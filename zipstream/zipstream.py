#
# ZIP File streaming
# based on official ZIP File Format Specification version 6.3.4
# https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
#
import os
import time
from zlib import crc32 as zip_crc32
from . import consts
try:
    import aiofiles
    aio_available = True
except ImportError:
    aio_available = False


__all__ = ("ZipStream", "AioZipStream")


class ZipStream(object):

    def __init__(self, files, chunksize=1024):
        """
        files - list of files, or generator returning files
                each file entry should be represented as dict with
                parameters:
                file - full path to file name
                name - (optional) name of file in zip archive
                       if not used, filename stripped from 'file' will be used

                not implemented yet:
                stream - (optional) can be used as replacement for 'file'
                         entry, will be treated as generator returnig
                         chunks of data that will be streamed in archive.
                         If used, then 'name' entry is required.
        chunksize - default size of data block streamed from files
        """
        self._source_of_files = files
        self.__files = []
        self.__version = consts.ZIP32_VERSION
        self.zip64 = False
        self.chunksize = chunksize
        # this flag tuns on signature for data descriptor record.
        # see section 4.3.9.3 of ZIP File Format Specification
        self.__use_ddmagic = True
        # central directory size and placement
        self.__cdir_size = 0
        self.__offset = 0

    def zip64_required(self):
        """
        Turn on zip64 mode for archive
        """
        raise NotImplementedError("Zip64 is not supported yet")

    def _create_file_struct(self, data):
        """
        extract info about streamed file and return all processed data
        required in zip archive
        """
        # date and time of file
        dt = time.localtime()
        dosdate = ((dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]) \
            & 0xffff
        dostime = (dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)) \
            & 0xffff

        # check zip32 limit
        # stats = os.stat(data['file'])
        #  if stats.st_size > consts.ZIP32_LIMIT:
        #     self.zip64_required()

        # file properties used in zip
        file_struct = {'src': data['file'],
                       'mod_time': dostime,
                       'mod_date': dosdate,
                       'crc': 0,  # will be calculated during data streaming
                       "offset": 0,  # file header offset in zip file
                       'flags': 0b00001000}  # flag about using data descriptor is always on

        # file name in archive
        if 'name' not in data:
            data['name'] = os.path.basename(data['file'])
        try:
            file_struct['fname'] = data['name'].encode("ascii")
        except UnicodeError:
            file_struct['fname'] = data['name'].encode("utf-8")
            file_struct['flags'] |= consts.UTF8_FLAG
        return file_struct

    def make_extra_field(self, signature, data):
        """
        Extra field for file
        """
        fields = {"signature": signature,
                  "size": len(data)}
        head = consts.EXTRA_TUPLE(**fields)
        head = consts.EXTRA_STRUCT.pack(*head)
        return head + data

    def make_local_file_header(self, file_struct):
        """
        Create file header
        """
        fields = {"signature": consts.LF_MAGIC,
                  "version": self.__version,
                  "flags": file_struct['flags'],
                  "compression": 0,
                  "mod_time": file_struct['mod_time'],
                  "mod_date": file_struct['mod_date'],
                  "crc": 0,
                  "uncomp_size": 0,
                  "comp_size": 0,
                  "fname_len": len(file_struct['fname']),
                  "extra_len": 0}
        head = consts.LF_TUPLE(**fields)
        head = consts.LF_STRUCT.pack(*head)
        head += file_struct['fname']
        #file_struct['header'] = head
        return head

    def make_data_descriptor(self, file_struct):
        """
        Create file descriptor.
        """
        fields = {"uncomp_size": file_struct['size'],
                  "comp_size": file_struct['size'],
                  "crc": file_struct['crc']}
        descriptor = consts.DD_TUPLE(**fields)
        descriptor = consts.DD_STRUCT.pack(*descriptor)
        if self.__use_ddmagic:
            descriptor = consts.DD_MAGIC + descriptor
        return descriptor

    def make_cdir_file_header(self, file_struct):
        """
        Create central directory file header
        """
        fields = {"signature": consts.CDFH_MAGIC,
                  "system": 0x03,  # 0x03 - unix
                  "version": self.__version,
                  "version_ndd": self.__version,
                  "flags": file_struct['flags'],
                  "compression": 0,  # no compression
                  "mod_time": file_struct['mod_time'],
                  "mod_date": file_struct['mod_date'],
                  "uncomp_size": file_struct['size'],
                  "comp_size": file_struct['size'],
                  "offset":  file_struct['offset'],  # < file header offset
                  "crc": file_struct['crc'],
                  "fname_len": len(file_struct['fname']),
                  "extra_len": 0,
                  "fcomm_len": 0,  # comment length
                  "disk_start": 0,
                  "attrs_int":  0,
                  "attrs_ext": 0}
        cdfh = consts.CDLF_TUPLE(**fields)
        cdfh = consts.CDLF_STRUCT.pack(*cdfh)
        cdfh += file_struct['fname']
        return cdfh

    def make_cdend(self):
        """
        make end of central directory record
        """
        fields = {"signature": consts.CD_END_MAGIC,
                  "disk_num": 0,
                  "disk_cdstart": 0,
                  "disk_entries": len(self.__files),
                  "total_entries": len(self.__files),
                  "cd_size": self.__cdir_size,
                  "cd_offset": self.__offset,
                  "comment_len": 0}
        cdend = consts.CD_END_TUPLE(**fields)
        cdend = consts.CD_END_STRUCT.pack(*cdend)
        return cdend

    def stream_single_file(self, file_struct):
        """
        stream single zip file with header and descriptor at the end
        """
        # file header
        yield self.make_local_file_header(file_struct)
        # file content
        crc = None
        size = 0
        with open(file_struct['src'], "rb") as fh:
            while True:
                part = fh.read(self.chunksize)
                if not part:
                    break
                yield part
                size += len(part)
                if crc:
                    crc = zip_crc32(part, crc)
                else:
                    crc = zip_crc32(part)
        file_struct['size'] = size
        if not crc:
            crc = 0
        # hack for making CRC unsigned long
        file_struct['crc'] = crc & 0xffffffff
        # file descriptor
        yield self.make_data_descriptor(file_struct)

    def stream(self):
        """
        Stream complete archive
        """
        # stream files
        for idx, source in enumerate(self._source_of_files):
            file_struct = self._create_file_struct(source)
            file_struct['offset'] = self.__offset  # file offset in archive
            self.__files.append(file_struct)
            # file data
            for chunk in self.stream_single_file(file_struct):
                self.__offset += len(chunk)
                yield chunk

        # stream central directory entries
        for idx, file_struct in enumerate(self.__files):
            chunk = self.make_cdir_file_header(file_struct)
            self.__cdir_size += len(chunk)
            yield chunk

        # stream end of central directory
        yield self.make_cdend()


class AioZipStream(ZipStream):
    """
    Asynchronous file of ZipStream
    """

    def __init__(self, *args, **kwargs):
        super(AioZipStream, self).__init__(*args, **kwargs)
        if not aio_available:
            raise Exception(
                "aiofiles module is required to stream ZIP files in asynchronous mode")
