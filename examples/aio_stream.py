#!/usr/bin/env python3
import os
import asyncio
from zipstream import AioZipStream


def files_to_stream(dirname):
    """
    This simple generator is used to feed
    zip streamer by files to stream inside
    of the file
    """
    for f in os.listdir(dirname):
        fp = os.path.join(dirname, f)
        if os.path.isfile(fp):
            yield fp


async def zip_async(dirname):
    for a, b in files_to_stream(dn):
        print(b)


dn = "/home/moozg/Pulpit/tmp/1/2/34"
loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async(dn))
loop.stop()
