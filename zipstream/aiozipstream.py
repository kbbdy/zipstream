#
# ZIP File streaming
# based on official ZIP File Format Specification version 6.3.4
# https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
#
import asyncio
from .zipstream import ZipBase, Processor
from concurrent import futures
try:
    import aiofiles
    aio_available = True
except ImportError:
    aio_available = False


__all__ = ("AioZipStream",)


class AioZipStream(ZipBase):
    """
    Asynchronous version of ZipStream
    """

    def __init__(self, *args, **kwargs):
        super(AioZipStream, self).__init__(*args, **kwargs)

    def __get_executor(self):
        # get thread pool executor
        try:
            return self.__tpex
        except AttributeError:
            self.__tpex = futures.ThreadPoolExecutor(max_workers=1)
            return self.__tpex

    async def _execute_aio_task(self, task, *args, **kwargs):
        # run synchronous task in separate thread and await for result
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.__get_executor(),
                                          task, *args, **kwargs)

    def _create_file_struct(self, data):
        if 'file' in data:
            if not aio_available:
                raise Exception(
                    "aiofiles module is required to stream files asynchronously")
        return super(AioZipStream, self)._create_file_struct(data)

    async def data_generator(self, src, src_type):
        if src_type == 's':
            async for chunk in src:
                yield chunk
            return
        if src_type == 'f':
            async with aiofiles.open(src, "rb") as fh:
                while True:
                    part = await fh.read(self.chunksize)
                    if not part:
                        break
                    yield part
            return

    async def _stream_single_file(self, file_struct):
        """
        stream single zip file with header and descriptor at the end
        """
        yield self._make_local_file_header(file_struct)
        pcs = Processor(file_struct)
        async for chunk in self.data_generator(file_struct['src'], file_struct['stype']):
            yield await self._execute_aio_task(pcs.process, chunk)
        chunk = await self._execute_aio_task(pcs.tail)
        # chunk = await pcs.aio_tail()
        if len(chunk) > 0:
            yield chunk
        yield self._make_data_descriptor(file_struct, *pcs.state())

    async def stream(self):
        # stream files
        for idx, source in enumerate(self._source_of_files):
            file_struct = self._create_file_struct(source)
            # file offset in archive
            file_struct['offset'] = self._offset_get()
            self._add_file_to_cdir(file_struct)
            # file data
            async for chunk in self._stream_single_file(file_struct):
                self._offset_add(len(chunk))
                yield chunk
        # stream zip structures
        for chunk in self._make_end_structures():
            yield chunk
        self._cleanup()
