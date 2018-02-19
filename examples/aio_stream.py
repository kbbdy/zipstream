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


async def zip_async(zipname, dirname, p):
    aioz = AioZipStream(files_to_stream(dn), chunksize=32768)
    async with aiofiles.open(zipname, mode='wb') as z:
        async for chunk in aioz.stream():
            print(p, end='', flush=True)
            await z.write(chunk)


dn = "/home/moozg/Pulpit/tmp/1/2/34"
loop = asyncio.get_event_loop()
loop.run_until_complete(
    asyncio.gather(zip_async('azip1.zip', dn, '1'),
                   zip_async('azip2.zip', dn, '2'),
                   zip_async('azip2.zip', dn, '3'))
)
loop.stop()
print()
