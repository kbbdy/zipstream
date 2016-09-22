#!/usr/bin/env python
#coding: utf-8
from zipstream import ZipStream

zs = ZipStream()
# add files to zip before streaming
zs.add_file("example_file_1.txt")
zs.add_file("example_file_2.txt")
zs.add_file("example_file_3.jpg","foo.jpeg")
# write result file
with file("zipout.zip","wb") as fout:
    for f in zs.stream():
        fout.write(f)
