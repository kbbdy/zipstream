from django.http import StreamingHttpResponse
from zipstream import ZipStream


def stream_as_zip(request):
    streamed_data_filename = "my_streamed_zip_file.zip"
    files = []
    files.append({'file': '/tmp/some_image.jpg'})
    files.append({'file': '/tmp/foo'})
    # this file will have different name than original
    files.append({'file': '/tmp/my_mp3_file.mp3', 'name': 'my.mp3'})
    # large chunk size will improve speed, but increase memory usage
    stream = ZipStream(files, chunksize=32768)
    # streamed response
    response = StreamingHttpResponse(
        stream.stream(),
        content_type="application/zip")
    response['Content-Disposition'] = 'attachment; filename="%s"' % streamed_data_filename
    return response
