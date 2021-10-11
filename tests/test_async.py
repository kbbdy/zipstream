import io
import pytest
import zipstream
import zipfile
import aiofiles
pytestmark = pytest.mark.asyncio

async def asyncfileslist():
    with open("/tmp/_tempik_1.txt", "w") as f:
        f.write("foo baz bar")
    with open("/tmp/_tempik_2.txt", "w") as f:
        f.write("baz trololo something")
    yield {"file": "/tmp/_tempik_1.txt"}
    yield {"file": "/tmp/_tempik_2.txt"}


def  syncfileslist():
    with open("/tmp/_tempik_1.txt", "w") as f:
        f.write("foo baz bar")
    with open("/tmp/_tempik_2.txt", "w") as f:
        f.write("baz trololo something")
    yield {"file": "/tmp/_tempik_1.txt"}
    yield {"file": "/tmp/_tempik_2.txt"}

async def asyncfileslist_streams():
    with open("/tmp/_tempik_1.txt", "w") as f:
        f.write("foo baz bar")
    with open("/tmp/_tempik_2.txt", "w") as f:
        f.write("baz trololo something")
    async with aiofiles.open("/tmp/_tempik_1.txt","rb") as f:
        yield {"stream":f ,
                         "name": "_tempik_1.txt"
               }
    async with aiofiles.open("/tmp/_tempik_2.txt","rb") as f:
        yield {"stream": f,
               "name": "_tempik_2.txt"
               }


async def asyncfileslist_stream_iter ():
    with open("/tmp/_tempik_1.txt", "w") as f:
        f.write("foo baz bar")
    with open("/tmp/_tempik_2.txt", "w") as f:
        f.write("baz trololo something")
    with open("/tmp/_tempik_1.txt","rb") as f:
        yield {"stream":f ,
                         "name": "_tempik_1.txt"
               }
    with open("/tmp/_tempik_2.txt","rb") as f:
        yield {"stream": f,
               "name": "_tempik_2.txt"
               }


async def test_async_generator_for_files():
    gen=asyncfileslist()
    await zip_gen_and_check(gen)

async  def   test_sync_generator_for_files():
    gen=syncfileslist()
    await zip_gen_and_check(gen)

async  def   test_sync_list_for_files():
    gen=list(syncfileslist())
    await zip_gen_and_check(gen)

async  def  test_async_list_for_async_get():
    gen=asyncfileslist_streams()
    await zip_gen_and_check(gen)

async  def  test_async_list_for_iter():
    gen=asyncfileslist_stream_iter()
    await zip_gen_and_check(gen)


async def zip_gen_and_check(gen):
    FILENAMES = set(fd["file"].split("/")[-1] for fd in syncfileslist())
    zs = zipstream.AioZipStream(gen)
    res = b""

    async for f in zs.stream():
        res += f
    zf=zipfile.ZipFile(io.BytesIO(res))
    filenames=set(zipinfo.filename for zipinfo  in zf.filelist)
    assert not  filenames.difference(FILENAMES)



