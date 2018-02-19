# zipstream

Simple python library for streaming ZIP files which are created dynamically, without using any temporary files.

Files stored in ZIP file are not compressed. Its intended to serve easily structured content in convenient way in web applications

- No temporary files, data is streamed directly from files
- Small memory usage, straming is realised using yield statement
- Archive structure is created on the fly
- Zip32 compatible files
- Zip64 support is planned in future
- Independent from python's standard lib implementation


## Examples:

### Example of creating zip file

```python
def files_to_stream(dirname):
    for f in os.listdir(dirname):
        fp = os.path.join(dirname, f)
        if os.path.isfile(fp):
            yield {'file': fp}

zs = ZipStream(files_to_stream("/tmp/my_files_to_zip"))

# write result file
with open("example.zip", "wb") as fout:
    for data in zs.stream():
        fout.write(data)
```

### Example of using zipstream as Django view

```python
from django.http import StreamingHttpResponse

def stream_as_zip(request):
    streamed_data_filename = "my_streamed_zip_file.zip"
    files = []
    files.append({'file': '/tmp/some_grapth.jpg'})
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
```
