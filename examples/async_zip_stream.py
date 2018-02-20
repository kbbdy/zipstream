#!/usr/bin/env python3
import asyncio
import aiofiles
import random
from zipstream import AioZipStream


async def generated_content(size):
    """
    asynchronous source of random data of unknown length,
    which we stream inside zip
    """
    chars = '0123456789 abcdefghijklmnopqrstuvwxyz \n'
    for m in range(size):
        t = ""
        for n in range(random.randint(20, 200)):
            t += random.choice(chars)
        yield bytes(t, 'ascii')
        asyncio.sleep(0)


async def zip_async(zipname, files):
    # larger chunk size will increase performance
    aiozip = AioZipStream(files, chunksize=32768)
    async with aiofiles.open(zipname, mode='wb') as z:
        async for chunk in aiozip.stream():
            await z.write(chunk)

files = [
    {'file': '/tmp/car.jpeg'},
    {'file': '/tmp/aaa.mp3', 'name': 'music.mp3'},
    {'stream': generated_content(50),
     'name': 'random_stuff.txt'}
]

loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async('example.zip', files))
loop.stop()
