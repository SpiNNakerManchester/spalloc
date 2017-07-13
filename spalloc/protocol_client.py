"""A simple blocking spalloc_server protocol implementation."""

import socket
import json
import time
from collections import deque


class ProtocolTimeoutError(Exception):
    """Thrown upon a protocol-level timeout."""


class ProtocolClient(object):
    """A simple (blocking) client implementation of the `spalloc-server
    <https://github.com/project-rig/spalloc_server>`_ protocol.

    This minimal implementation is intended to serve both simple applications
    and as an example implementation of the protocol for other applications.
    This implementation simply implements the protocol, presenting an RPC-like
    interface to the server. For a higher-level interface built on top of this
    client, see :py:class:`spalloc.Job`.

    Usage examples::

        # Connect to a spalloc_server
        c = ProtocolClient("hostname")
        c.connect()

        # Call commands by name
        print(c.call("version"))  # '0.1.0'

        # Call commands as if they were methods
        print(c.version())  # '0.1.0'

        # Wait an event to be received
        print(c.wait_for_notification())  # {"jobs_changed": [1, 3]}

        # Done!
        c.close()
    """

    def __init__(self, hostname, port=22244):
        """Define a new connection.

        .. note::

            Does not connect to the server until :py:meth:`.connect` is called.

        Parameters
        ----------
        hostname : str
            The hostname of the server.
        port : str
            The port to use (default: 22244).
        """
        self._hostname = hostname
        self._port = port

        # The socket connected to the server or None if disconnected.
        self._sock = None

        # A buffer for incoming, but incomplete, lines of data
        self._buf = b""

        # A queue of unprocessed notifications
        self._notifications = deque()

    def connect(self, timeout=None):
        """(Re)connect to the server.

        Raises
        ------
        OSError, IOError
            If a connection failure occurs.
        """
        # Close any existing connection
        if self._sock is not None:
            self.close()

        # Try to (re)connect to the server
        try:
            self._sock = socket.socket(socket.AF_INET,
                                       socket.SOCK_STREAM)
            self._sock.settimeout(timeout)
            self._sock.connect((self._hostname, self._port))
            # Success!
            return
        except (IOError, OSError):
            # Failiure, try again...
            self.close()

            # Pass on the exception
            raise

    def close(self):
        """Disconnect from the server."""
        if self._sock is not None:
            self._sock.close()
        self._sock = None
        self._buf = b""

    def _recv_json(self, timeout=None):
        """Recieve a line of JSON from the server.

        Parameters
        ----------
        timeout : float or None
            The number of seconds to wait before timing out or None if this
            function should try again forever.

        Returns
        -------
        object or None
            The unpacked JSON line received.

        Raises
        ------
        ProtocolTimeoutError
            If a timeout occurs.
        OSError
            If the socket is unusable or becomes disconnected.
        """
        if self._sock is None:
            raise OSError("Not connected!")

        # Wait for some data to arrive
        while b"\n" not in self._buf:
            try:
                self._sock.settimeout(timeout)
                data = self._sock.recv(1024)
            except socket.timeout:
                raise ProtocolTimeoutError("recv timed out.")

            # Has socket closed?
            if len(data) == 0:
                raise OSError("Connection closed.")

            self._buf += data

        # Unpack and return the JSON
        line, _, self._buf = self._buf.partition(b"\n")
        return json.loads(line.decode("utf-8"))

    def _send_json(self, obj, timeout=None):
        """Attempt to send a line of JSON to the server.

        Parameters
        ----------
        obj : object
            The object to serialise.
        timeout : float or None
            The number of seconds to wait before timing out or None if this
            function should try again forever.

        Raises
        ------
        ProtocolTimeoutError
            If a timeout occurs.
        OSError
            If the socket is unusable or becomes disconnected.
        """
        # Connect if not already connected
        if self._sock is None:
            raise OSError("Not connected!")

        # Send the line
        self._sock.settimeout(timeout)
        data = json.dumps(obj).encode("utf-8") + b"\n"
        try:
            if self._sock.send(data) != len(data):
                # XXX: If can't send whole command at once, just fail
                raise OSError("Could not send whole command.")
        except socket.timeout:
            raise ProtocolTimeoutError("send timed out.")

    def call(self, name, *args, **kwargs):
        """Send a command to the server and return the reply.

        Parameters
        ----------
        name : str
            The name of the command to send.
        timeout : float or None
            The number of seconds to wait before timing out or None if this
            function should wait forever. (Default: None)

        Returns
        -------
        object
            The object returned by the server.

        Raises
        ------
        ProtocolTimeoutError
            If a timeout occurs.
        IOError, OSError
            If the connection is unavailable or is closed.
        """
        timeout = kwargs.pop("timeout", None)

        finish_time = time.time() + timeout if timeout is not None else None

        # Construct the command message
        command = {"command": name,
                   "args": args,
                   "kwargs": kwargs}

        self._send_json(command, timeout=timeout)

        # Command sent! Attempt to receive the response...
        while finish_time is None or finish_time > time.time():
            if finish_time is None:
                time_left = None
            else:
                time_left = max(finish_time - time.time(), 0.0)

            obj = self._recv_json(timeout=time_left)
            if "return" in obj:
                # Success!
                return obj["return"]
            else:
                # Got a notification, keep trying...
                self._notifications.append(obj)

    def wait_for_notification(self, timeout=None):
        """Return the next notification to arrive.

        Parameters
        ----------
        name : str
            The name of the command to send.
        timeout : float or None
            The number of seconds to wait before timing out or None if this
            function should try again forever.

            If negative only responses already-received will be returned. If no
            responses are available, in this case the function does not raise a
            ProtocolTimeoutError but returns None instead.

        Returns
        -------
        object
            The notification sent by the server.

        Raises
        ------
        ProtocolTimeoutError
            If a timeout occurs.
        IOError, OSError
            If the socket is unusable or becomes disconnected.
        """
        # If we already have a notification, return it
        if self._notifications:
            return self._notifications.popleft()

        # Otherwise, wait for a notification to arrive
        if timeout is None or timeout >= 0.0:
            return self._recv_json(timeout)
        else:
            return None

    # The bindings of the Spalloc protocol methods themselves

    def version(self, timeout=None):
        return self.call("version", timeout=timeout)

    def create_job(self, *args, **kwargs):
        return self.call("create_job", *args, **kwargs)

    def job_keepalive(self, job_id, timeout=None):
        return self.call("job_keepalive", job_id, timeout=timeout)

    def get_job_state(self, job_id, timeout=None):
        return self.call("get_job_state", job_id, timeout=timeout)

    def get_job_machine_info(self, job_id, timeout=None):
        return self.call("get_job_machine_info", job_id, timeout=timeout)

    def power_on_job_boards(self, job_id, timeout=None):
        return self.call("power_on_job_boards", job_id, timeout=timeout)

    def power_off_job_boards(self, job_id, timeout=None):
        return self.call("power_off_job_boards", job_id, timeout=timeout)

    def destroy_job(self, job_id, reason=None, timeout=None):
        return self.call("destroy_job", job_id, reason, timeout=timeout)

    def notify_job(self, job_id=None, timeout=None):
        return self.call("notify_job", job_id, timeout=timeout)

    def no_notify_job(self, job_id=None, timeout=None):
        return self.call("no_notify_job", job_id, timeout=timeout)

    def notify_machine(self, machine_name=None, timeout=None):
        return self.call("notify_machine", machine_name, timeout=timeout)

    def no_notify_machine(self, machine_name=None, timeout=None):
        return self.call("no_notify_machine", machine_name, timeout=timeout)

    def list_jobs(self, timeout=None):
        return self.call("list_jobs", timeout=timeout)

    def list_machines(self, timeout=None):
        return self.call("list_machines", timeout=timeout)

    def get_board_position(self, machine_name, x, y, z, timeout=None):
        return self.call("get_board_position", machine_name, x, y, z,
                         timeout=timeout)

    def get_board_at_position(self, machine_name, x, y, z, timeout=None):
        return self.call("get_board_at_position", machine_name, x, y, z,
                         timeout=timeout)

    def where_is(self, **kwargs):
        return self.call("where_is", **kwargs)
