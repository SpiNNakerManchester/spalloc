# Copyright (c) 2016 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import threading
import time
import logging
import pytest
from mock import Mock
from spalloc_client import (
    ProtocolClient, SpallocServerException, ProtocolTimeoutError,
    ProtocolError)
from .common import MockServer

logging.basicConfig(level=logging.DEBUG)


class TestConnect(object):

    @pytest.mark.timeout(1.0)
    def test_first_time(self, s, c, bg_accept):  # @UnusedVariable
        # If server already available, should just connect straight away
        c.connect()
        bg_accept.join()

    @pytest.mark.timeout(1.0)
    def test_no_server(self):
        # Should just fail if there is no server
        c = ProtocolClient("localhost")
        with pytest.raises((IOError, OSError)):
            c.connect()

    @pytest.mark.timeout(1.0)
    def test_reconnect(self):
        # If previously connected, connecting should close the existing
        # connection and attempt to start a new one
        c = ProtocolClient("localhost")

        started = threading.Event()

        def accept_and_listen():
            s = MockServer()
            s.listen()
            started.set()
            s.connect()

        # Attempt several reconnects
        for _ in range(3):
            t = threading.Thread(target=accept_and_listen)
            t.start()
            started.wait()
            started.clear()
            c.connect()
            t.join()


@pytest.mark.timeout(1.0)
def test_close(c, s, bg_accept):
    # If already connected, should be able to close
    assert not c._has_open_socket()
    c.connect()
    assert c._has_open_socket()
    c.close()
    assert not c._has_open_socket()
    bg_accept.join()
    s.close()

    # Should be able to close again
    c.close()
    assert not c._has_open_socket()

    # And should be able to close a newly created connection
    c = ProtocolClient("localhost")
    assert not c._has_open_socket()
    c.close()
    assert not c._has_open_socket()


@pytest.mark.timeout(1.0)
def test_recv_json(c, s, bg_accept):

    # Should fail before connecting
    with pytest.raises((IOError, OSError)):
        c._recv_json()

    c.connect()
    bg_accept.join()

    # Make sure timeout works once connected
    before = time.time()
    with pytest.raises(ProtocolTimeoutError):
        c._recv_json(timeout=0.1)
    after = time.time()
    assert 0.1 < after - before < 0.2

    # Make sure we can actually receieve JSON
    s.send({"foo": 1, "bar": 2})
    assert c._recv_json() == {"foo": 1, "bar": 2}

    # Make sure we can receieve large blobs of JSON
    s.send({"foo": list(range(1000))})
    assert c._recv_json() == {"foo": list(range(1000))}

    # Make sure we can receive multiple blobs of JSON before returning each
    # sequentially
    s.send({"first": True, "second": False})
    s.send({"first": False, "second": True})
    assert c._recv_json() == {"first": True, "second": False}
    assert c._recv_json() == {"first": False, "second": True}

    # When socket becomes closed should fail
    s.close()
    with pytest.raises((IOError, OSError)):
        c._recv_json()


@pytest.mark.timeout(1.0)
def test_send_json(c, s, bg_accept):
    # Should fail before connecting
    with pytest.raises((IOError, OSError)):
        c._send_json(123)

    c.connect()
    bg_accept.join()

    # Make sure we can send JSON
    c._send_json({"foo": 1, "bar": 2})
    assert s.recv() == {"foo": 1, "bar": 2}


@pytest.mark.timeout(1.0)
def test_send_json_fails(c):
    sock = Mock()
    sock.send.side_effect = [1, socket.timeout()]
    c._socks[threading.current_thread()] = sock
    c._dead = False

    # If full amount is not sent, should fail
    with pytest.raises((IOError, OSError)):
        c._send_json(123)

    # If timeout, should fail
    with pytest.raises(ProtocolTimeoutError):
        c._send_json(123)


@pytest.mark.timeout(1.0)
def test_call(c, s, bg_accept):
    c.connect()
    bg_accept.join()

    # Basic calls should work
    s.send({"return": "Woo"})
    assert c.call("foo", 1, bar=2) == "Woo"
    assert s.recv() == {"command": "foo", "args": [1], "kwargs": {"bar": 2}}

    # Should be able to cope with notifications arriving before return value
    s.send({"notification": 1})
    s.send({"notification": 2})
    s.send({"return": "Woo"})
    assert c.call("foo", 1, bar=2) == "Woo"
    assert s.recv() == {"command": "foo", "args": [1], "kwargs": {"bar": 2}}
    assert list(c._notifications) == [{"notification": 1}, {"notification": 2}]
    c._notifications.clear()

    # Should be able to timeout immediately
    before = time.time()
    with pytest.raises(ProtocolTimeoutError):
        c.call("foo", 1, bar=2, timeout=0.1)
    after = time.time()
    assert s.recv() == {"command": "foo", "args": [1], "kwargs": {"bar": 2}}
    assert 0.1 < after - before < 0.2

    # Should be able to timeout after getting a notification
    s.send({"notification": 3})
    before = time.time()
    with pytest.raises(ProtocolTimeoutError):
        c.call("foo", 1, bar=2, timeout=0.1)
    after = time.time()
    assert s.recv() == {"command": "foo", "args": [1], "kwargs": {"bar": 2}}
    assert 0.1 < after - before < 0.2
    assert list(c._notifications) == [{"notification": 3}]

    # Exceptions should transfer
    s.send({"exception": "something informative"})
    with pytest.raises(SpallocServerException) as e:
        c.call("foo")
    assert "something informative" in str(e.value)


def test_wait_for_notification(c, s, bg_accept):
    c.connect()
    bg_accept.join()

    # Should be able to timeout
    with pytest.raises(ProtocolTimeoutError):
        c.wait_for_notification(timeout=0.1)

    # Should return None on negative timeout when no notifications arrived
    assert c.wait_for_notification(timeout=-1) is None

    # If notifications queued during call, should just return those
    s.send({"notification": 1})
    s.send({"notification": 2})
    s.send({"return": "Woo"})
    assert c.call("foo", 1, bar=2) == "Woo"
    assert s.recv() == {"command": "foo", "args": [1], "kwargs": {"bar": 2}}
    assert c.wait_for_notification() == {"notification": 1}
    assert c.wait_for_notification() == {"notification": 2}

    # If no notifications queued, should listen for them
    s.send({"notification": 3})
    assert c.wait_for_notification() == {"notification": 3}


def test_commands_as_methods(c, s, bg_accept):
    c.connect()
    bg_accept.join()

    s.send({"return": "Woo"})
    assert c.create_job(1, bar=2, owner="dummy") == "Woo"
    assert s.recv() == {
        "command": "create_job", "args": [1], "kwargs": {
            "bar": 2, "owner": "dummy"}}

    # Should fail for arbitrary internal method names
    with pytest.raises(AttributeError):
        c._bar()
    # Should fail for arbitrary external method names
    with pytest.raises(AttributeError):
        c.bar()


def test_where_is_sanity(c):
    with pytest.raises(SpallocServerException):
        c.where_is(foo=1, bar=2)
    with pytest.raises(SpallocServerException):
        c.where_is(machine=1, x=2, y=3, z=4, foo=5)
    with pytest.raises(ProtocolError):
        c.where_is(machine=1, x=2, y=3, z=4)
    with pytest.raises(ProtocolError):
        c.where_is(machine=1, x=2, y=3, z=4, timeout=5)
    with pytest.raises(ProtocolError):
        c.where_is(machine=1, x=2, y=3, z=4, timeout=None)
