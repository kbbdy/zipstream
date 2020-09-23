#!/usr/bin/env python3
from __future__ import unicode_literals, absolute_import
from unittest import TestCase, main, skip
import os
import zipfile
import zipstream
import zlib, struct

class FileUsingTestBase(object):

    def setUp(self):
        self.__temps = []

    def tearDown(self):
        while len(self.__temps)>0:
            t = self.__temps.pop()
            os.unlink(t)

    def _add_temp_file(self, length=None):
        import tempfile, random
        tf = tempfile.mkstemp(prefix="_zipstream_test_", suffix=".txt")[1]
        if length is None:
            length = random.randint(10,50)
        temptxt = b"This is temporary file.\n"
        idx,pos = 0,0
        with open(tf, "w") as f:
            while idx<length:
                idx+=1
                f.write( temptxt[pos] )
                pos+=1
                if pos>=len(temptxt):
                    pos = 0
        self.__temps.append(tf)
        return tf

class ZipStreamTestCase(FileUsingTestBase, TestCase):

    def test_structs(self):
        # base structures are match?
        self.assertEqual( zipfile.sizeEndCentDir, zipstream.consts.CD_END_STRUCT.size )
        self.assertEqual( zipfile.sizeCentralDir, zipstream.consts.CDLF_STRUCT.size )
        self.assertEqual( zipfile.sizeFileHeader, zipstream.consts.LF_STRUCT.size )
        # magic numbers
        self.assertEqual( zipstream.consts.LF_MAGIC, zipfile.stringFileHeader )
        self.assertEqual( zipstream.consts.CDFH_MAGIC, zipfile.stringCentralDir )
        self.assertEqual( zipstream.consts.CD_END_MAGIC, zipfile.stringEndArchive )

    def test_empty_zip(self):
        # compare empty zip files
        with zipfile.ZipFile('/tmp/empty.zip', 'w') as myzip:
            pass
        zs = zipstream.ZipStream()
        with open("/tmp/empty_out.zip","wb") as fo:
            for f in zs.stream():
                fo.write(f)
        bin1 = open("/tmp/empty.zip","r").read()
        bin2 = open("/tmp/empty_out.zip","r").read()
        self.assertEqual(bin1, bin2)

    def test_one_file_add(self):
        with open("/tmp/_tempik_1.txt","w") as f:
            f.write("foo baz bar")
        with open("/tmp/_tempik_2.txt","w") as f:
            f.write("baz trololo something")

        zs = zipstream.ZipStream([
            {"file": "/tmp/_tempik_1.txt"},
            {"file": "/tmp/_tempik_2.txt"}
        ])

        res = b""
        with open("/tmp/empty_out.zip","wb") as f:
            for f in zs.stream():
                res+=f

        # check header
        self.assertEqual( res[:4], zipfile.stringFileHeader )
        self.assertEqual( res[4:6], b"\x14\x00" )    # version
        self.assertEqual( res[6:8], b"\x08\x00" )    # flags
        self.assertEqual( res[8:10], b"\x00\x00" )   # compression method
        self.assertEqual( res[14:18], b"\x00\x00\x00\x00" ) # crc is set to 0
        self.assertEqual( res[18:22], b"\x00\x00\x00\x00" ) # compressed size is 0
        self.assertEqual( res[22:26], b"\x00\x00\x00\x00" ) # uncompressed size is 0

        pos = res.find( zipstream.consts.LF_MAGIC ,10)

        # data descriptor has 16 bytes
        dd = res[pos-16:pos]
        self.assertEqual(dd[:4], zipstream.consts.DD_MAGIC)

        # check CRC
        crc = dd[4:8]
        crc2 = zlib.crc32(b"foo baz bar") & 0xffffffff
        crc2 = struct.pack(b"<L", crc2 )
        self.assertEqual( crc, crc2 )
        # check file len compressed and uncompressed
        self.assertEqual( dd[8:12], b"\x0b\x00\x00\x00" )
        self.assertEqual( dd[12:16], b"\x0b\x00\x00\x00" )

        # check end file descriptor
        endstruct  = res[ -zipstream.consts.CD_END_STRUCT.size: ]
        self.assertEqual( endstruct[:4], zipstream.consts.CD_END_MAGIC )
        self.assertEqual( endstruct[8:10], b"\x02\x00" ) # two files in disc
        self.assertEqual( endstruct[10:12], b"\x02\x00" ) # two files total

        zdsize = len(res) - zipstream.consts.CD_END_STRUCT.size
        cdsize = struct.unpack("<L", endstruct[12:16])[0]
        cdpos = struct.unpack("<L", endstruct[16:20])[0]

        # position of ender is equal of cd + cd size
        self.assertEqual( cdpos+cdsize, len(res)-zipstream.consts.CD_END_STRUCT.size )
        self.assertEqual( res[cdpos:cdpos+4], zipstream.consts.CDFH_MAGIC )

        cdentry = res[ cdpos: cdpos+cdsize ]


if __name__ == '__main__':
    main()

