#!/bin/bash
rm -r ./dist
./setup.py bdist_wheel --universal
rm -r ./build
rm -r ./zipstream.egg-info
echo "Result files:"
ls -lx1 ./dist
