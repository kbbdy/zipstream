#!/usr/bin/env python3
import os
import random
from zipstream import ZipStream


def bin_generator(lines):
    blah = ['foo', 'baz', 'bar', 'xyz', 'aaa', 'bbb']
    for a in range(lines):
        ln = []
        for b in range(random.randint(5, 20)):
            ln.append(random.choice(blah))
        yield bytes(' '.join(ln), 'ascii')
        yield b'\n'


def files_to_stream(dirname):
    for f in os.listdir(dirname):
        fp = os.path.join(dirname, f)
        if os.path.isfile(fp):
            name = "foo_" + os.path.basename(fp)
            yield {'file': fp, 'name': name}
    yield {'stream': bin_generator(10), 'name': 'foo.txt'}


zs = ZipStream(files_to_stream("/tmp/files/to/stream"))

with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
