#!/usr/bin/env python3
import asyncio
import aiofiles
from zipstream import AioZipStream


async def zip_async(zipname, files):
    aiozip = AioZipStream(files, chunksize=32768)
    async with aiofiles.open(zipname, mode='wb') as z:
        async for chunk in aiozip.stream():
            await z.write(chunk)

files = [
    {'file': '/tmp/files/to/stream/car.jpeg'},
    {'file': '/tmp/files/to/stream/aaa.mp3',
     'name': 'music.mp3'},
]

loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async('example.zip', files))
loop.stop()
