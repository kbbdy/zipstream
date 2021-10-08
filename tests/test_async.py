import pytest

pytestmark = pytest.mark.asyncio
import zipstream
from tests.test_zipstream import ZipStreamTestCase


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



async def test_async_generator_for_files():
    gen=asyncfileslist()
    await zipgen(gen)

async  def   test_sync_generator_for_files():
    gen=syncfileslist()
    await zipgen(gen)

async  def   test_sync_list_for_files():
    gen=list(syncfileslist())
    await zipgen(gen)

async def zipgen(gen):
    zs = zipstream.AioZipStream(gen)
    res = b""

    async for f in zs.stream():
        res += f
