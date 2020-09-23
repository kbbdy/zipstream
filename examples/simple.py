#!/usr/bin/env python3
from zipstream import ZipStream

files = [
    {'stream': [b'this\n', b'is\n', b'stream\n', b'of\n',b'data\n'],
     'name': 'a.txt',
     'compression':'deflate'},
    {'file': '/tmp/z/car.jpeg'},
    {'file': '/tmp/z/aaa.mp3',
     'name': 'music.mp3'},
]

zs = ZipStream(files)

with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
