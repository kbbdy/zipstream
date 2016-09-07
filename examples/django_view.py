#coding: utf-8
from django.http import StreamingHttpResponse
from zipstream import ZipStream

def stream_as_zip(request):
    streamed_data_filename = "my_streamed_zip_file.zip"
    # large chunk size will improve speed, but increase memory usage
    stream = ZipStream(chunksize=32768)
    # filename of first file in ZIP archive will be different than original
    stream.add_file("/tmp/my_mp3_file.mp3", "my.mp3")
    stream.add_file("/tmp/some_grapth.jpg")
    stream.add_file("/tmp/foo")
    # streamed response
    response = StreamingHttpResponse(
        stream.stream(),
        content_type="application/zip")
    response['Content-Disposition'] =
        'attachment; filename="%s"' % streamed_data_filename
    return response
