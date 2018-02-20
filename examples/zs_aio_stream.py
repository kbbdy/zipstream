#!/usr/bin/env python3
import asyncio
import aiofiles
import random
from zipstream import AioZipStream


async def some_content_generated_on_fly():
    """
    asynchronous source of some random data of known length,
    which we stream inside zip
    """
    chars = '0123456789 abcdefghijklmnopqrstuvwxyz \n'
    for m in range(50):
        t = ""
        for n in range(random.randint(20, 200)):
            t += random.choice(chars)
        yield bytes(t, 'ascii')
        asyncio.sleep(0)


async def zip_async(zipname, files):
    aiozip = AioZipStream(files, chunksize=32768)
    async with aiofiles.open(zipname, mode='wb') as z:
        async for chunk in aiozip.stream():
            await z.write(chunk)

files = [
    {'file': '/home/moozg/Pulpit/tmp/1/2/34/car.jpeg'},
    {'file': '/home/moozg/Pulpit/tmp/1/2/34/aaa.mp3',
     'name': 'music.mp3'},
    {'stream': some_content_generated_on_fly(),
     'name': 'random_stuff.txt'}
]

loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async('example.zip', files))
loop.stop()
