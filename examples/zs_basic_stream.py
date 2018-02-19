#!/usr/bin/env python3
#
#  Example usage of ZipStream with generator as source of files
#
from zipstream import ZipStream
import os


def files_to_stream(dirname):
    for f in os.listdir(dirname):
        fp = os.path.join(dirname, f)
        if os.path.isfile(fp):
            name = "foo_" + os.path.basename(fp)
            yield {'file': fp, 'name': name}


zs = ZipStream(files_to_stream("/tmp/files/to/stream"))

with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
