import os
import sys
import pytest


def pytest_configure(config):
    p = os.path.abspath(os.path.join(__file__, "..", ".."))
    if p not in sys.path:
        sys.path.append(p)

 