#!/usr/bin/env python3
import os
import asyncio
from zipstream import AioZipStream
import aiofiles


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


async def zip_async(dirname):
    aioz = AioZipStream(files_to_stream(dn), chunksize=32768)
    async with aiofiles.open('aio_example.zip', mode='wb') as z:
        async for chunk in aioz.stream():
            await z.write(chunk)


dn = "/home/moozg/Pulpit/tmp/1/2/34"
loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async(dn))
loop.stop()
