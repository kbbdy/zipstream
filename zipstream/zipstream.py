import os
import time
from zlib import crc32 as zip_crc32
from . import consts

__all__ = ("ZipStream", "AioZipStream")


class ZipStream(object):

    def __init__(self, source, chunksize=1024):
        self._source_of_files = source
        self.__files = []
        self.__version = consts.ZIP32_VERSION
        self.zip64 = False
        self.chunksize = chunksize
        self.__use_ddmagic = True
        # central directory size and placement
        self.__cdir_size = 0
        self.__offset = 0

    def zip64_required(self):
        """
        Turn on zip64 mode for archive
        """
        raise NotImplementedError("Zip64 is not supported yet")

#    def source_files(self):
#        """
#        Source of files that wille be streamed
#        result is dict with fields:
#        file - full path to source file
#        name - name of file in zip (if omitted, file field will be uses)
#        """
#        for f in self.__files:
#            yield {'file': f,
#                   'name': os.path.basename(f)}

    def _prepare_source(self, data):
        """
        extract info about streamed file and return all processed data
        required in zip archive
        """
        # date and time of file
        # TODO: Fix broken date / time
        dt = time.localtime()
        dosdate = (dt.tm_year - 1980) << 9 | dt.tm_mon << 5 | dt.tm_mday
        dostime = dt.tm_hour << 11 | dt.tm_min << 5 | (dt.tm_min // 2)
        # check zip32 limit
        stats = os.stat(data['file'])
        if stats.st_size > consts.ZIP32_LIMIT:
            self.zip64_required()
        # file properties used in zip
        rec = {'src': data['file'],
               'size': stats.st_size,  # <- this should't be statted here
               'mod_time': dosdate,
               'mod_date': dostime,
               'crc': 0,  # will be calculated during data streaming
               "offset": 0,  # file header offset in zip file
               'flags': 0b00001000,  # flag about using data descriptor is always on
               }

        # file name in archive
        if 'name' not in data:
            data['name'] = os.path.basename(data['file'])
        try:
            rec['fname'] = data['name'].encode("ascii")
        except UnicodeError:
            rec['fname'] = data['name'].encode("utf-8")
            rec['flags'] |= consts.UTF8_FLAG
        return rec

    def make_extra_field(self, signature, data):
        """
        Extra field for file
        """
        fields = {"signature": signature,
                  "size": len(data)}
        head = consts.EXTRA_TUPLE(**fields)
        head = consts.EXTRA_STRUCT.pack(*head)
        return head + data

    def make_local_file_header(self, idx):
        """
        Create file header
        """
        fileinfo = self.__files[idx]
        fields = {"signature": consts.LF_MAGIC,
                  "version": self.__version,
                  "flags": fileinfo['flags'],
                  "compression": 0,
                  "mod_time": fileinfo['mod_time'],
                  "mod_date": fileinfo['mod_date'],
                  "crc": 0,
                  "uncomp_size": 0,
                  "comp_size": 0,
                  "fname_len": len(fileinfo['fname']),
                  "extra_len": 0,
                  }
        head = consts.LF_TUPLE(**fields)
        head = consts.LF_STRUCT.pack(*head)
        head += fileinfo['fname']
        self.__files[idx]['header'] = head
        return head

    def make_data_descriptor(self, idx):
        """
        Create file descriptor.
        """
        fileinfo = self.__files[idx]
        fields = {"uncomp_size": fileinfo['size'],
                  "comp_size": fileinfo['size'],
                  "crc": fileinfo['crc']}
        descriptor = consts.DD_TUPLE(**fields)
        descriptor = consts.DD_STRUCT.pack(*descriptor)
        if self.__use_ddmagic:
            descriptor = consts.DD_MAGIC + descriptor
        return descriptor

    def make_cdir_file_header(self, idx):
        """
        Create central directory file header
        """
        fileinfo = self.__files[idx]
        fields = {"signature": consts.CDFH_MAGIC,
                  "system": 0x03,  # 0x03 - unix
                  "version": self.__version,
                  "version_ndd": self.__version,
                  "flags": fileinfo['flags'],
                  "compression": 0,  # no compression
                  "mod_time": fileinfo['mod_time'],
                  "mod_date": fileinfo['mod_date'],
                  "uncomp_size": fileinfo['size'],
                  "comp_size": fileinfo['size'],
                  "offset":  fileinfo['offset'],  # < file header offset
                  "crc": fileinfo['crc'],
                  "fname_len": len(fileinfo['fname']),
                  "extra_len": 0,
                  "fcomm_len": 0,  # comment length
                  "disk_start": 0,
                  "attrs_int":  0,
                  "attrs_ext": 0,
                  }
        cdfh = consts.CDLF_TUPLE(**fields)
        cdfh = consts.CDLF_STRUCT.pack(*cdfh)
        cdfh += fileinfo['fname']
        print(cdfh)
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
                  "comment_len": 0,
                  }
        cdend = consts.CD_END_TUPLE(**fields)
        cdend = consts.CD_END_STRUCT.pack(*cdend)
        return cdend

    # stream single zip file with header and descriptor
    def stream_single_file(self, idx):
        # file header
        yield self.make_local_file_header(idx)
        # file content
        crc = None
        with open(self.__files[idx]['src'], "rb") as fh:
            while True:
                part = fh.read(self.chunksize)
                if not part:
                    break
                yield part
                if crc:
                    crc = zip_crc32(part, crc)
                else:
                    crc = zip_crc32(part)
        if not crc:
            crc = 0
        # hack for making CRC unsigned long
        self.__files[idx]['crc'] = crc & 0xffffffff
        # file descriptor
        yield self.make_data_descriptor(idx)

    def stream(self):
        """
        Stream archive
        """
        # stream files
        for idx, source in enumerate(self._source_of_files):
            file_struct = self._prepare_source(source)
            file_struct['offset'] = self.__offset  # file offset in zip
            self.__files.append(file_struct)
            # file data
            for chunk in self.stream_single_file(idx):
                self.__offset += len(chunk)
                yield chunk

        # stream central directory entries
        for idx, file_struct in enumerate(self.__files):
            chunk = self.make_cdir_file_header(idx)
            self.__cdir_size += len(chunk)
            yield(chunk)

        # stream end of central directory
        yield(self.make_cdend())


# class AioZipStream(ZipStream):
#     """
#     Asynchronous file of ZipStream
#     """
#     pass
