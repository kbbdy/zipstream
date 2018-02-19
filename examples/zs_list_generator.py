#!/usr/bin/env python3
from zipstream import ZipStream

files = [
    {'file': '/home/moozg/Pulpit/tmp/1/2/34/car.jpeg'},
    {'file': '/home/moozg/Pulpit/tmp/1/2/34/aaa.mp3',
     'name': 'music.mp3'},
]

zs = ZipStream(files)

with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
