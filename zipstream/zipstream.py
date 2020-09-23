#
# ZIP File streaming
# based on official ZIP File Format Specification version 6.3.4
# https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
#
import os
import time
import zlib
from . import consts


__all__ = ("ZipStream", )


class Processor:
    def __init__(self, file_struct):
        self.crc = 0
        self.o_size = self.c_size = 0
        if file_struct['cmethod'] is None:
            self.process = self._process_through
            self.tail = self._no_tail
        elif file_struct['cmethod'] == 'deflate':
            self.compr = zlib.compressobj(5, zlib.DEFLATED, -15)
            self.process = self._process_deflate
            self.tail = self._tail_deflate

    # no compression
    def _process_through(self, chunk):
        self.o_size += len(chunk)
        self.c_size = self.o_size
        self.crc = zlib.crc32(chunk, self.crc)
        return chunk

    def _no_tail(self):
        return b''

    # deflate compression
    def _process_deflate(self, chunk):
        self.o_size += len(chunk)
        self.crc = zlib.crc32(chunk, self.crc)
        chunk = self.compr.compress(chunk)
        self.c_size += len(chunk)
        return chunk

    def _tail_deflate(self):
        chunk = self.compr.flush(zlib.Z_FINISH)
        self.c_size += len(chunk)
        return chunk

    # after processing counters and crc
    def state(self):
        return self.crc, self.o_size, self.c_size


class ZipBase:

    def __init__(self, files=[], chunksize=1024):
        """
        files - list of files, or generator returning files
                each file entry should be represented as dict with
                parameters:
                file - full path to file name
                name - (optional) name of file in zip archive
                       if not used, filename stripped from 'file' will be used
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
        self.__cdir_size = self.__offset = 0

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
        file_struct = {'mod_time': dostime,
                       'mod_date': dosdate,
                       'crc': 0,  # will be calculated during data streaming
                       "offset": 0,  # file header offset in zip file
                       'flags': 0b00001000}  # flag about using data descriptor is always on

        if 'file' in data:
            file_struct['src'] = data['file']
            file_struct['stype'] = 'f'
        elif 'stream' in data:
            file_struct['src'] = data['stream']
            file_struct['stype'] = 's'
        else:
            raise Exception('No file or stream in sources')

        cmpr = data.get('compression', None)
        if cmpr not in (None, 'deflate'):
            raise Exception('Unknown compression method %r' % cmpr)
        file_struct['cmethod'] = cmpr
        file_struct['cmpr_id'] = {
            None: consts.COMPRESSION_STORE,
            'deflate': consts.COMPRESSION_DEFLATE}[cmpr]

        # file name in archive
        if 'name' not in data:
            data['name'] = os.path.basename(data['file'])
        try:
            file_struct['fname'] = data['name'].encode("ascii")
        except UnicodeError:
            file_struct['fname'] = data['name'].encode("utf-8")
            file_struct['flags'] |= consts.UTF8_FLAG
        return file_struct

    # zip structures creation

    def _make_extra_field(self, signature, data):
        """
        Extra field for file
        """
        fields = {"signature": signature,
                  "size": len(data)}
        head = consts.EXTRA_TUPLE(**fields)
        head = consts.EXTRA_STRUCT.pack(*head)
        return head + data

    def _make_local_file_header(self, file_struct):
        """
        Create file header
        """
        fields = {"signature": consts.LF_MAGIC,
                  "version": self.__version,
                  "flags": file_struct['flags'],
                  "compression": file_struct['cmpr_id'],
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
        return head

    def _make_data_descriptor(self, file_struct, crc, org_size, compr_size):
        """
        Create file descriptor.
        This function also updates size and crc fields of file_struct
        """
        # hack for making CRC unsigned long
        file_struct['crc'] = crc & 0xffffffff
        file_struct['size'] = org_size
        file_struct['csize'] = compr_size
        fields = {"uncomp_size": file_struct['size'],
                  "comp_size": file_struct['csize'],
                  "crc": file_struct['crc']}
        descriptor = consts.DD_TUPLE(**fields)
        descriptor = consts.DD_STRUCT.pack(*descriptor)
        if self.__use_ddmagic:
            descriptor = consts.DD_MAGIC + descriptor
        return descriptor

    def _make_cdir_file_header(self, file_struct):
        """
        Create central directory file header
        """
        fields = {"signature": consts.CDFH_MAGIC,
                  "system": 0x03,  # 0x03 - unix
                  "version": self.__version,
                  "version_ndd": self.__version,
                  "flags": file_struct['flags'],
                  "compression": file_struct['cmpr_id'],
                  "mod_time": file_struct['mod_time'],
                  "mod_date": file_struct['mod_date'],
                  "uncomp_size": file_struct['size'],
                  "comp_size": file_struct['csize'],
                  "offset": file_struct['offset'],  # < file header offset
                  "crc": file_struct['crc'],
                  "fname_len": len(file_struct['fname']),
                  "extra_len": 0,
                  "fcomm_len": 0,  # comment length
                  "disk_start": 0,
                  "attrs_int": 0,
                  "attrs_ext": 0}
        cdfh = consts.CDLF_TUPLE(**fields)
        cdfh = consts.CDLF_STRUCT.pack(*cdfh)
        cdfh += file_struct['fname']
        return cdfh

    def _make_cdend(self):
        """
        make end of central directory record
        """
        fields = {"signature": consts.CD_END_MAGIC,
                  "disk_num": 0,
                  "disk_cdstart": 0,
                  "disk_entries": len(self.__files),
                  "total_entries": len(self.__files),
                  "cd_size": self.__cdir_size,
                  "cd_offset": self._offset_get(),
                  "comment_len": 0}
        cdend = consts.CD_END_TUPLE(**fields)
        cdend = consts.CD_END_STRUCT.pack(*cdend)
        return cdend

    def _make_end_structures(self):
        """
        cdir and cdend structures are saved at the end of zip file
        """
        # stream central directory entries
        for idx, file_struct in enumerate(self.__files):
            chunk = self._make_cdir_file_header(file_struct)
            self.__cdir_size += len(chunk)
            yield chunk
        # stream end of central directory
        yield self._make_cdend()

    def _offset_add(self, value):
        self.__offset += value

    def _offset_get(self):
        return self.__offset

    def _add_file_to_cdir(self, file_struct):
        self.__files.append(file_struct)

    def _cleanup(self):
        """
        Clean all structs after streaming
        """
        self.__files = []
        self.__cdir_size = self.__offset = 0


class ZipStream(ZipBase):

    def data_generator(self, src, src_type):
        if src_type == 's':
            for chunk in src:
                yield chunk
            return
        if src_type == 'f':
            with open(src, "rb") as fh:
                while True:
                    part = fh.read(self.chunksize)
                    if not part:
                        break
                    yield part
            return

    def _stream_single_file(self, file_struct):
        """
        stream single zip file with header and descriptor at the end
        """
        yield self._make_local_file_header(file_struct)
        pcs = Processor(file_struct)
        for chunk in self.data_generator(file_struct['src'], file_struct['stype']):
            chunk = pcs.process(chunk)
            if len(chunk) > 0:
                yield chunk
        chunk = pcs.tail()
        if len(chunk) > 0:
            yield chunk
        yield self._make_data_descriptor(file_struct, *pcs.state())

    def stream(self):
        """
        Stream complete archive
        """
        # stream files
        for idx, source in enumerate(self._source_of_files):
            file_struct = self._create_file_struct(source)
            # file offset in archive
            file_struct['offset'] = self._offset_get()
            self._add_file_to_cdir(file_struct)
            # file data
            for chunk in self._stream_single_file(file_struct):
                self._offset_add(len(chunk))
                yield chunk
        # stream zip structures
        for chunk in self._make_end_structures():
            yield chunk
        self._cleanup()
