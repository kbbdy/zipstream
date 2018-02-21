from .zipstream import ZipStream
import sys

# AioZipStream is avilable from Python 3.6 version
if (sys.version_info.major >= 3) and (sys.version_info.minor >= 6):
    from .aiozipstream import AioZipStream
del sys

version = "0.4"
