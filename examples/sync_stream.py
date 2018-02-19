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


zs = ZipStream(files_to_stream("/home/moozg/Pulpit/tmp/1/2/34"))

# write result file
with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
