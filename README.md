# ZipStream

Simple python library for streaming ZIP files which are created dynamically, without using any temporary files.

- No temporary files, data is streamed directly
- Supported `deflate` compression method
- Small memory usage, straming is realised using yield statement
- Archive structure is created on the fly, and all data can be created during stream
- Files included into archive can be generated on the fly using Python generators
- Asynchronous AioZipStream and classic ZipStream are available
- Zip32 format compatible files
- Independent from python's standard ZipFile implementation
- Almost no dependencies: only `aiofiles` in some circumstances (see AioZipStream section for details)
- Zip64 support is also planned in future (far future, because I never hitted 4GB file size limit ;-) )

### Required Python version:

`ZipStream` is compatible with **Python 2.7**.

`AioZipStream` require **Python 3.6**. For earlier versions `AioZipStream` is not available for import.


## Usage:

List of files to archive is stored as list of dicts. Why dicts? Because there are possible additional parameters for each file, and more parameters are planned in future.

Sample list of files to archive:

```python
files = [
         # file /tmp/file.dat will be added to archive under `file.dat` name.
         {'file':'/tmp/file.dat'},

         # same file as previous under own name: `completly_different.foo`
         # and will be compressed using `deflate` compression method
         {'file':'/tmp/file.dat',
          'name':'completly_different.foo',
          'compression':'deflate'}
        ]
```

It's time to stream / archive:

```python
zs = ZipStream(files)
with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
```

Any iterable source of binary data can be used in place of regular files. Using generator as input for file must be represented by `stream` field instead of `file`, additional `name` parameter is also required.

```python

def source_of_bytes():
    yield b"123456789"
    yield b"abcdefgh"
    yield b"I am a binary data"

files = [....
         # file will be generated dynamically under name my_data.bin
         {'stream': source_of_bytes(), 'name': 'my_data.bin'},
        ]
```

Keep in mind, that data should be served in chunks of reasonable size, because in case of using stream, `ZipStream` class is not able to split data by self.

List of files to stream can be also generated on the fly, during streaming:

```python
import os
from zipstream import ZipStream

def files_to_stream_with_foo_in_name(dirname):
    # all files from selected firectory
    for f in os.listdir(dirname):
        fp = os.path.join(dirname, f)
        if os.path.isfile(fp):
            yield {'file': fp,
                   'name': "foo_" + os.path.basename(fp)}
    # and our generator too
    yield {'stream': source_of_bytes(),
           'name': 'my_data.bin',
           'compression': 'deflate'}

zs = ZipStream(files_to_stream_with_foo_in_name('\tmp\some-files'))
```

## Asynchronous AioZipStream

:warning: **To use asynchronous AioZipStream at least Python 3.6 version is required**. AioZipStream is using asynchronous generator syntax, wchich is avilable from 3.6 version.

To work with local files addtional `aiofiles` library is required. If You plan to stream only dynamically generated content, then `aiofiles` is not required.

See [aiofiles github repo](https://github.com/Tinche/aiofiles) for details about `aiofiles`.


### Sample of asynchronous zip streaming

Any generator used to create data on the fly, must be defined as `async`:

```python
async def content_generator():
    yield b'foo baz'
    asyncio.sleep(0.1) # we simulate little slow source of data
    data = await remote_data_source()
    yield bytes(data, 'utf-8') # always remember to yield binary data
    asyncio.sleep(0.5)
    yield b"the end"
```

Also zip streaming must be inside `async` function. Note usage `aiofiles.open` instead of `open`, which is asynchronous and will not block event loop during disk access.

```python
from zipstream import AioZipStream

async def zip_async(zipname, files):
    aiozip = AioZipStream(files, chunksize=32768)
    async with aiofiles.open(zipname, mode='wb') as z:
        async for chunk in aiozip.stream():
            await z.write(chunk)
```

Here is going list of files to send:

```python
files = [
    {'file': '/tmp/car.jpeg'},
    {'file': '/tmp/aaa.mp3', 'name': 'music.mp3'},
    {'stream': content_generator(),
     'name': 'random_stuff.txt'}
]
```

Start asyncio loop and stream result to file:

```python
loop = asyncio.get_event_loop()
loop.run_until_complete(zip_async('example.zip', files))
loop.stop()
```

The List of files may also be an async generator:
```python
async def  files():
    yield {
              'file': '/tmp/car.jpeg'
          },
    yield {
              'file': '/tmp/aaa.mp3', 
              'name': 'music.mp3'
          },
    yield {
        'stream': content_generator(),
        'name': 'random_stuff.txt'
           }
 
```

## Examples

See `examples` directory for complete code and working examples of ZipStream and AioZipStream.
