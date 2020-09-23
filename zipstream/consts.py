from collections import namedtuple
import struct


# zip constants
ZIP32_VERSION = 20
ZIP64_VERSION = 45
ZIP32_LIMIT = (1 << 31) - 1
UTF8_FLAG = 0x800   # utf-8 filename encoding flag

# zip compression methods
COMPRESSION_STORE = 0
COMPRESSION_DEFLATE = 8
COMPRESSION_BZIP2 = 12
COMPRESSION_LZMA = 14

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
EXTRA_64_TUPLE = namedtuple("extra64local", ("uncomp_size", "comp_size"))
CD_EXTRA_64_STRUCT = struct.Struct(b"<HHH")
CD_EXTRA_64_TUPLE = namedtuple(
    "extra64cdir", ("uncomp_size", "comp_size", "offset"))

# file descriptor
DD_STRUCT = struct.Struct(b"<LLL")
DD_STRUCT64 = struct.Struct(b"<LQQ")
DD_TUPLE = namedtuple("filecrc",
                      ("crc", "comp_size", "uncomp_size"))
DD_MAGIC = b'\x50\x4b\x07\x08'

# central directory file header
CDLF_STRUCT = struct.Struct(b"<4sBBHHHHHLLLHHHHHLL")
CDLF_TUPLE = namedtuple("cdfileheader",
                        ("signature", "system", "version", "version_ndd", "flags",
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
