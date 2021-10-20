import asyncio
import random
import io
import zipstream
import aiofiles
async def generate_task(doc):
    delay=random.randrange(0,5)
    await asyncio.sleep(delay)
    data= {"stream":   doc["data"],
                "name":  doc["name"],
                "compression": "deflate"}
    print(f"finshed {data['name']} in {delay}s"  )
    return data



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


files = [
    {'name': '/tmp/z/1.txt' ,"data": generated_content(50)},
    {'name': '/tmp/z/2.txt',"data": generated_content(50)},
    {'name': '/tmp/z/3.txt', "data":  generated_content(50)},
    {'name': '/tmp/z/4.txt', "data":  generated_content(50)},
    {'name': '/tmp/z/5.txt', "data":  generated_content(50)},

]

async def fileslistgen(docs):
    """
    This allows concurrency while files get streamed as completed
    """
    futures = []
    for doc in docs:
        futures.append((generate_task(doc)))

    for coroutine in asyncio.as_completed(futures):
        yield await coroutine


async def zip_async(zipname, files):
    # larger chunk size will increase performance
    aiozip = zipstream.AioZipStream(
    fileslistgen(files)
)
    async with aiofiles.open(zipname, mode='wb') as z:
        async for chunk in aiozip.stream():
            await z.write(chunk)

loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async('example.zip', files))
loop.stop()
