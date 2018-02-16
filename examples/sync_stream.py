#!/usr/bin/env python3
#
#  Example usage of ZipStream with generator
#  as source of files to stream.
#
from zipstream import ZipStream
import os


def files_to_stream(dirname):
    """
    This simple generator is used to feed
    zip streamer by files to stream inside
    of the file
    """
    for f in os.listdir(dirname):
        fp = os.path.join(dirname, f)
        if os.path.isfile(fp):
            yield {'file': fp}


dn = "/tmp/my_files_to_stream"
zs = ZipStream(files_to_stream(dn))

# write result file
with open("example.zip", "wb") as fout:
    for f in zs.stream():
        fout.write(f)
