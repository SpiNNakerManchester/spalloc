import pytest

import threading

from spalloc import ProtocolClient
from spalloc.config import SEARCH_PATH

from common import MockServer

@pytest.yield_fixture
def no_config_files(monkeypatch):
    # Prevent discovery of config files during test
    before = SEARCH_PATH[:]
    SEARCH_PATH.clear()
    yield
    SEARCH_PATH.extend(before)


@pytest.yield_fixture
def s():
    # A mock server
    s = MockServer()
    yield s
    s.close()

@pytest.yield_fixture
def c():
    c = ProtocolClient("localhost")
    yield c
    c.close()

@pytest.yield_fixture
def bg_accept(s):
    # Accept the first conncetion in the background
    started = threading.Event()
    def accept_and_listen():
        s.listen()
        started.set()
        s.connect()
    t = threading.Thread(target=accept_and_listen)
    t.start()
    started.wait()
    yield t
    s.close()
    t.join()

