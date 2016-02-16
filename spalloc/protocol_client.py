"""A simple blocking spalloc_server protocol implementation."""

import socket
import json
import time

from functools import partial

from collections import deque

import logging


logger = logging.getLogger(__name__)


class ProtocolClient(object):
    """A simple `spalloc-server
    <https://github.com/project-rig/spalloc_server>`_ protocol client
    implementation.
    
    This minimal blocking implementation is not intended to be truly general
    purpose but rather serve as an example of a simple client implementation
    and form the basis of the basic 'spalloc' command-line tools.
    
    Usage examples::
    
        # Connect to a spalloc_server
        c = ProtocolClient("hostname")
        
        # Call commands by name
        print(c.call("version"))  # '0.0.2'
        
        # Call commands as if they were methods
        c.notify_job([1, 2, 3])
        
        # Wait an event to be received
        print(c.wait_for_notification())  # {"jobs_changed": [1, 3]}
        
        # Done!
        c.close()
    """
    
    def __init__(self, hostname, port=22244, reconnect_delay=5.0):
        """
        Parameters
        ----------
        hostname : str
            The hostname of the server.
        port : str
            The port to use (default: 22244).
        reconnect_delay : float
            The number of seconds to wait between attempts to (re)connect to
            the server when the socket is closed.
        """
        self._hostname = hostname
        self._port = port
        self._reconnect_delay = reconnect_delay
        
        # The socket connected to the server or None if disconnected.
        self._sock = None
        
        # A buffer for incoming, but incomplete, lines of data
        self._buf = b""
        
        # A queue of unprocessed notifications
        self._notifications = deque()
    
    def connect(self, timeout=None, no_retry=False):
        """(Re)connect to the server.
        
        Parameters
        ----------
        timeout : float or None
            The number of seconds to wait before timing out. None if this
            function should try again forever.
        no_retry : bool
            If True, will only attempt to connect to the server once.
        
        Raises
        ------
        TimeoutError
            If a timeout occurs.
        """
        finish_time = time.time() + timeout if timeout is not None else None
        
        # Close any existing connection (and wait the reconnect delay before
        # connecting again)
        if self._sock is not None:
            self.close()
            delay = self._reconnect_delay
            if finish_time is not None:
                delay = min(finish_time - time.time(), delay)
            time.sleep(delay)
        
        # Keep trying to reconnect to the server (until a timeout is reached)
        first_try = True
        while finish_time is None or finish_time > time.time():
            try:
                self._sock = socket.socket(socket.AF_INET,
                                           socket.SOCK_STREAM)
                self._sock.connect((self._hostname, self._port))
                logger.debug("Connected to server.")
                # Success!
                return True
            except OSError as e:
                # Failiure, try again...
                logger.info("Could not connect to server: %s.", e)
                
                self.close()
                
                # Should we give up after this first failure?
                if first_try and no_retry:
                    first_try = False
                    raise
                else:
                    first_try = False
                
                # Wait before next attempt. If the timeout will expire before
                # then, just wait for the timeout.
                delay = self._reconnect_delay
                if finish_time is not None:
                    delay = min(finish_time - time.time(), delay)
                if delay > 0.0:
                    logger.info("Retrying in %0.1f seconds...",
                                self._reconnect_delay)
                    time.sleep(delay)
        
        # Timeout
        logger.debug("Connection attempt timed out.")
        raise TimeoutError()
    
    def close(self):
        """Disconnect from the server."""
        if self._sock is not None:
            logger.debug("Disconnecting from server.")
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
        TimeoutError
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
                raise TimeoutError("recv timed out.")
            
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
        TimeoutError
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
            raise TimeoutError("send timed out.")
    
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
        TimeoutError
            If a timeout occurs.
        OSError
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
            TimeoutError but returns None instead.
        
        Returns
        -------
        object
            The notification sent by the server.
        
        Raises
        ------
        TimeoutError
            If a timeout occurs.
        OSError
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
    
    def __getattr__(self, name):
        """:py:meth:`.call` commands by calling 'methods' of this object.
        
        For example, the following lines are equivilent::
        
            c.call("foo", 1, bar=2, on_return=f)
            c.foo(1, bar=2, on_return=f)
        """
        if name.startswith("_"):
            raise AttributeError(name)
        else:
            return partial(self.call, name)

