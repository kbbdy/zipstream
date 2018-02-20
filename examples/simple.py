#!/usr/bin/env python3
from zipstream import ZipStream

files = [
    {'stream': [b'qwoeui youasd\n', b'yfoasudyf oiausdy foiuasdy\n', b'foiuasdy foiuasdy foa\n'],
     'name': 'a.txt',
     'compression':'deflate'},
    {'file': '/tmp/car.jpeg'},
    {'file': '/tmp/aaa.mp3',
     'name': 'music.mp3'},
]

zs = ZipStream(files)

with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
