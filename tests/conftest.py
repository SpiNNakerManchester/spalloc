import pytest

from mock import Mock

import os
import sys
import threading
import tempfile

from spalloc import ProtocolClient
from spalloc.config import SEARCH_PATH

from common import MockServer

@pytest.yield_fixture
def no_config_files(monkeypatch):
    # Prevent discovery of config files during test
    before = SEARCH_PATH[:]
    del SEARCH_PATH[:]
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


@pytest.yield_fixture
def basic_config_file(monkeypatch):
    # Sets up a basic config file with known and non-default values for all
    # fields
    fd, filename = tempfile.mkstemp()
    with open(filename, "w") as f:
        f.write("[spalloc]\n"
                "hostname=servername\n"
                "port=1234\n"
                "owner=me\n"
                "keepalive=1.0\n"
                "reconnect_delay=2.0\n"
                "timeout=3.0\n"
                "machine=m\n"
                "tags=foo, bar\n"
                "min_ratio=4.0\n"
                "max_dead_boards=5\n"
                "max_dead_links=6\n"
                "require_torus=True\n")
    before = SEARCH_PATH[:]
    del SEARCH_PATH[:]
    SEARCH_PATH.append(filename)
    yield
    del SEARCH_PATH[:]
    SEARCH_PATH.extend(before)
    os.remove(filename)


@pytest.fixture
def basic_job_kwargs():
    # The kwargs set by the basic_config_file fixture
    return dict(hostname="servername",
                port=1234,
                reconnect_delay=2.0,
                timeout=3.0,
                owner="me",
                keepalive=1.0,
                machine="m",
                tags=None,  # As machine is not None
                min_ratio=4.0,
                max_dead_boards=5,
                max_dead_links=6,
                require_torus=True)

@pytest.fixture
def no_colour(monkeypatch):
    isatty = Mock(return_value=False)
    monkeypatch.setattr(sys, "stdout",
                        Mock(write=sys.stdout.write, isatty=isatty))
    monkeypatch.setattr(sys, "stderr",
                        Mock(write=sys.stdout.write, isatty=isatty))
