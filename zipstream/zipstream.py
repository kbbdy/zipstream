#!/usr/bin/env python
#coding: utf-8
from __future__ import unicode_literals, absolute_import
from collections import namedtuple
#import zipfile
import os, zlib
import struct, time


__all__ = ("ZipStream",)

# zip constants
ZIP32_VERSION = 20
ZIP64_VERSION = 45
ZIP32_LIMIT = (1 << 31) - 1
UTF8_FLAG = 0x800   # utf-8 filename encoding flag

# file header
LF_STRUCT = struct.Struct(b"<4sHHHHHLLLHH")
LF_TUPLE = namedtuple("fileheader",
    ("signature", "version", "flags",
     "compression", "mod_time", "mod_date",
     "crc", "comp_size", "uncomp_size",
     "fname_len", "extra_len"))
LF_MAGIC = b'\x50\x4b\x03\x04'

# extra fields
EXTRA_STRUCT = struct.Struct(b"<HH")
EXTRA_TUPLE = namedtuple("extra", ("signature", "size"))
EXTRA_64_STRUCT = struct.Struct(b"<HH")
EXTRA_64_TUPLE = namedtuple("extra64local", ("uncomp_size", "comp_size") )
CD_EXTRA_64_STRUCT = struct.Struct(b"<HHH")
CD_EXTRA_64_TUPLE = namedtuple("extra64cdir", ("uncomp_size", "comp_size", "offset") )

# file descriptor
DD_STRUCT = struct.Struct(b"<LLL")
DD_STRUCT64 = struct.Struct(b"<LQQ")
DD_TUPLE = namedtuple("filecrc",
    ("crc", "comp_size", "uncomp_size") )
DD_MAGIC = b'\x08\x07\x4b\x50'


# central directory file header
CDLF_STRUCT = struct.Struct(b"<4sBBHHHHHLLLHHHHHLL")
CDLF_TUPLE = namedtuple("cdfileheader",
    ("signature", "system", "version", "version_ndd","flags",
     "compression", "mod_time", "mod_date", "crc",
     "comp_size", "uncomp_size", "fname_len", "extra_len",
     "fcomm_len", "disk_start", "attrs_int", "attrs_ext", "offset"))
CDFH_MAGIC = b'\x50\x4b\x01\x02'

# end of central directory record
CD_END_STRUCT = struct.Struct(b"<4sHHHHLLH")
CD_END_TUPLE = namedtuple("cdend",
    ("signature", "disk_num", "disk_cdstart", "disk_entries",
     "total_entries", "cd_size", "cd_offset", "comment_len"))
CD_END_MAGIC = b'\x50\x4b\x05\x06'

# zip64 end of central directory record
CD_END_STRUCT64 = struct.Struct(b"<4sQHHIIQQQQ")
CD_END_TUPLE64 = namedtuple("cdend64",
    ("signature", "zip64_eocd_size", "version", "version_ndd",
        "disk_num", "disk_cdstart", "disk_entries", "total_entries",
        "cd_size", "cd_offset"))
CD_END_MAGIC64 = b'\x06\x06\x4b\x50'

# zip64 end of central directory locator
CD_LOC64_STRUCT = struct.Struct(b"<4sLQL")
CD_LOC64_TUPLE =  namedtuple("cdfileheader64",
    ("signature", "disk_cdstart", "offset", "disk_count"))
CD_LOC64_MAGIC = b'\x07\x06\x4b\x50'



class ZipStream(object):

    def __init__(self, zip64=False, chunksize=1024):
        """
        zip64
           False - 32bit
           True - 64bit
           None - auto (regardless of files size)
        """
        self.__files = []
        self.__zip64headers = False
        self.__version = ZIP32_VERSION
        if zip64==True:
            self.zip64 = None
            self.zip64_required()
        else:
            self.zip64 = zip64
        self.chunksize = chunksize
        self.__use_ddmagic = True
        # central directory size and placement
        self.__cdir_size = 0
        self.__offset = 0

    def zip64_required(self):
        """
        Turn on zip64 mode for archive
        """
        if self.zip64:
            return
        if self.zip64==False:
            raise Exception("Zip 64 mode is required to stream files larger than %i bytes" % ZIP32_LIMIT)
        self.zip64 = True
        self.__zip64headers = True
        self.__version = ZIP64_VERSION

    def add_file(self, fname, newname=None):
        # date and time of file
        dt = time.localtime()
        dosdate = (dt.tm_year-1980) << 9 | dt.tm_mon << 5 | dt.tm_mday
        dostime = dt.tm_hour << 11 | dt.tm_min << 5 | (dt.tm_min // 2)
        # check zip32 limit
        stats = os.stat(fname)
        if stats.st_size>ZIP32_LIMIT:
            self.zip64_required()
        # file properties
        rec = { 'src' : fname,
                'size': stats.st_size,
                'mod_time': dosdate,
                'mod_date': dostime,
                'crc' : 0, # will be calculated during data streaming
                "offset" : 0, # file header offset in zip file
                'flags' : 0b00001000, # flag about using data descriptor is always on
              }
        # file name in archive
        if newname:
            fname = newname
        else:
            fname = os.path.split(fname)[1]
        try:
            rec['fname'] = fname.encode("ascii")
        except UnicodeError:
            rec['fname'] = fname.encode("utf-8")
            rec['flags'] |= UTF8_FLAG
        self.__files.append(rec)

    def make_extra_field(self, signature, data):
        """
        Extra field for file
        """
        fields = { "signature" : signature,
                   "size" : len(data) }
        head = EXTRA_TUPLE( **fields )
        head = EXTRA_STRUCT.pack( *head )
        return head + data

    def make_zip64_cdir_extra(self, fsize, compsize, offset):
        """
        make zip64 extra field
        """
        fields = {"comp_size" : compsize,
                  "uncomp_size" : fsize,
                  "offset" : offset }
        data = CD_EXTRA_64_TUPLE( **fields )
        data = CD_EXTRA_64_STRUCT.pack( *data )
        return self.make_extra_field(0x0001, data)

    def make_zip64_local_extra(self, fsize, compsize):
        """
        make zip64 extra field
        """
        fields = {"comp_size" : compsize,
                  "uncomp_size" : fsize }
        data = EXTRA_64_TUPLE( **fields )
        data = EXTRA_64_STRUCT.pack( *data )
        return self.make_extra_field(0x0001, data)

    def make_local_file_header(self, idx):
        """
        Create file header
        """
        fileinfo = self.__files[idx]
        fields = { "signature" : LF_MAGIC,
                   "version" : self.__version,
                   "flags" : fileinfo['flags'],
                   "compression" : 0,
                   "mod_time" : fileinfo['mod_time'],
                   "mod_date" : fileinfo['mod_date'],
                   "crc" : 0,
                   "uncomp_size" : 0,
                   "comp_size" : 0,
                   "fname_len" : len(fileinfo['fname']),
                   "extra_len":0,
                   }
        if self.__zip64headers:
            # in zip64 file size headers are set to 0xffffffff
            fields['uncomp_size'] = 0xffffffff
            fields['comp_size'] = 0xffffffff
            # additional extra field is added
            z64extra = self.make_zip64_local_extra(0,0)
            fields['extra_len'] = len(z64extra)
        head = LF_TUPLE( **fields )
        head = LF_STRUCT.pack( *head )
        head += fileinfo['fname']
        if self.__zip64headers:
            head += z64extra
        self.__files[idx]['header'] = head
        return head

    def make_data_descriptor(self, idx):
        """
        Create file descriptor.
        """
        fileinfo = self.__files[idx]
        fields = { "uncomp_size" : fileinfo['size'],
                   "comp_size" : fileinfo['size'],
                   "crc": fileinfo['crc'] }
        descriptor = DD_TUPLE( **fields )
        if self.__zip64headers:
            descriptor = DD_STRUCT64.pack( *descriptor )
        else:
            descriptor = DD_STRUCT.pack( *descriptor )
        if self.__use_ddmagic:
            descriptor = DD_MAGIC + descriptor
        return descriptor

    def make_cdir_file_header(self, idx):
        """
        Create central directory file header
        """
        fileinfo = self.__files[idx]
        fields = {"signature" : CDFH_MAGIC,
                  "system" : 0x03, # 0x03 - unix
                  "version" : self.__version,
                  "version_ndd" : self.__version,
                  "flags" : fileinfo['flags'],
                  "compression" : 0, # no compression
                  "mod_time" : fileinfo['mod_time'],
                  "mod_date" : fileinfo['mod_date'],
                  "uncomp_size" : fileinfo['size'],
                  "comp_size" : fileinfo['size'],
                  "offset" :  fileinfo['offset'], # < file header offset
                  "crc" : fileinfo['crc'],
                  "fname_len" : len(fileinfo['fname']),
                  "extra_len" : 0,
                  "fcomm_len" : 0, # comment length
                  "disk_start" : 0,
                  "attrs_int" :  0,
                  "attrs_ext" : 0,
        }
        if self.__zip64headers:
            # in zip64 file size headers and offset are set to 0xffffffff
            fields['uncomp_size'] = 0xffffffff
            fields['comp_size'] = 0xffffffff
            fields['offset'] = 0xffffffff
            # additional extra field is added
            z64extra = self.make_zip64_cdir_extra(
                fileinfo['size'],
                fileinfo['size'],
                fileinfo['offset'])
            fields['extra_len'] = len(z64extra)
        cdfh = CDLF_TUPLE( **fields )
        cdfh = CDLF_STRUCT.pack( *cdfh )
        cdfh += fileinfo['fname']
        # extra headers
        if self.__zip64headers:
            cdfh += z64extra
        return cdfh

    def make_cdend(self):
        """
        make end of central directory record
        """
        fields = {"signature" : CD_END_MAGIC,
                  "disk_num" : 0,
                  "disk_cdstart" : 0,
                  "disk_entries" : len(self.__files),
                  "total_entries" : len(self.__files),
                  "cd_size" : self.__cdir_size,
                  "cd_offset" : self.__offset,
                  "comment_len" : 0,
                 }
        if self.__zip64headers:
            fields['cd_size'] = 0xffff
            fields['cd_offset'] = 0xffff
        cdend = CD_END_TUPLE( **fields )
        cdend = CD_END_STRUCT.pack( *cdend )
        return cdend

    def make_cdend64(self):
        """
        make zip64 end of central directory record
        """
        fields = {"signature" : CD_END_MAGIC64,
                  "zip64_eocd_size" : CD_END_STRUCT64.size - 12, # self size
                  "version" : self.__version,
                  "version_ndd" : self.__version,
                  "disk_num" : 0,
                  "disk_cdstart" : 0,
                  "disk_entries" : len(self.__files),
                  "total_entries" : len(self.__files),
                  "cd_size" : self.__cdir_size,
                  "cd_offset" : self.__offset,
                 }
        cdend = CD_END_TUPLE64( **fields )
        cdend = CD_END_STRUCT64.pack( *cdend )
        return cdend

    def make_eocd64_locator(self, offset):
        """
        Zip64 end of central directory locator
        """
        fields = {"signature" : CD_LOC64_MAGIC,
                  "disk_cdstart" : 0,
                  "offset" : offset,
                  "disk_count" : 0,
                 }
        cdend = CD_LOC64_TUPLE( **fields )
        cdend = CD_LOC64_STRUCT.pack( *cdend )
        return cdend


    # stream single zip file with header and descriptor
    def stream_single_file(self, idx):
        # file header
        yield self.make_local_file_header(idx)
        # file content
        crc = None
        with file( self.__files[idx]['src'], "rb" ) as fh:
            while True:
                part = fh.read( self.chunksize )
                if not part: break
                yield part
                if crc:
                    crc = zlib.crc32(part, crc)
                else:
                    crc = zlib.crc32(part)
        if not crc:
            crc = 0
        self.__files[idx]['crc'] = crc & 0xffffffff # hack for making CRC unsigned long
        # file descriptor
        yield self.make_data_descriptor(idx)

    # stream archive
    def stream(self):
        # stream files
        idx = 0
        while idx<len(self.__files):
            # file offset in zip
            self.__files[idx]['offset'] = self.__offset
            # file data
            for chunk in self.stream_single_file(idx):
                self.__offset += len(chunk)
                yield chunk
            idx += 1
        # stream central directory entries
        idx = 0
        while idx<len(self.__files):
            for chunk in self.make_cdir_file_header(idx):
                self.__cdir_size += len(chunk)
                yield(chunk)
            idx += 1
        # stream zip64 records
        if self.__zip64headers:
            eocd64position = self.__offset + self.__cdir_size
            yield( self.make_cdend64() )
            yield( self.make_eocd64_locator(eocd64position) )
        # stream end of central directory
        yield( self.make_cdend() )


if __name__ == '__main__':
    zs = ZipStream(zip64=True, chunksize=48)
    zs.add_file("temp_file_1.txt")
    zs.add_file("temp_file_2.jpg")
    #zs.add_file("temp_file_3.txt")
    with file("zipout.zip","wb") as fo:
        for f in zs.stream():
            fo.write(f)
