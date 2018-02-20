#
# ZIP File streaming
# based on official ZIP File Format Specification version 6.3.4
# https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
#
from zlib import crc32 as zip_crc32
from .zipstream import ZipBase
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
        # file header
        yield self._make_local_file_header(file_struct)
        # file content
        crc, size = 0, 0
        async for chunk in self.data_generator(file_struct['src'], file_struct['stype']):
            yield chunk
            size += len(chunk)
            crc = zip_crc32(chunk, crc)
        # file descriptor
        yield self._make_data_descriptor(file_struct, size, crc)

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
