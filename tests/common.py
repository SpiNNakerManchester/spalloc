# Copyright (c) 2016 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import json
import threading


class MockServer(object):
    """A mock JSON line sender/receiver server."""

    def __init__(self):
        self._server_socket = socket.socket(socket.AF_INET,
                                            socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET,
                                       socket.SO_REUSEADDR, 1)

        self._sock = None
        self._buf = b""
        self._started = threading.Event()

    def listen(self):
        """Start listening to the server port."""
        self._server_socket.bind(("", 22244))
        self._server_socket.listen(1)

    def connect(self):
        """Wait for a client to connect."""
        self._started.set()
        self._sock, _addr = self._server_socket.accept()

    def close(self):
        if self._sock is not None:
            self._sock.close()
        self._sock = None
        self._buf = b""
        self._server_socket.close()

    def send(self, obj):
        """Send a JSON object to the client."""
        self._sock.send(json.dumps(obj).encode("utf-8") + b"\n")

    def recv(self):
        """Recieve a JSON object."""
        while b"\n" not in self._buf:
            data = self._sock.recv(1024)
            if len(data) == 0:  # pragma: no cover
                raise OSError("Socket closed!")
            self._buf += data

        line, _, self._buf = self._buf.partition(b"\n")
        return json.loads(line.decode("utf-8"))
