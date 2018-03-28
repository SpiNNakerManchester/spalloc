from spalloc.protocol_client import ProtocolClient, ProtocolTimeoutError
import sys
import threading


def _wait_for_exit(keepalive):
    for line in sys.stdin:
        if line.strip() == "exit":
            keepalive.stop()


class KeepAliveProcess(object):

    def __init__(self):
        self._stop = threading.Event()
        self._running = threading.Event()

    def stop(self):
        self._stop.set()

    def wait_for_start(self):
        self._running.wait()

    def run(self, hostname, port, job_id, keepalive, timeout, reconnect_delay):
        """Background keep-alive thread."""
        self._running.set()
        client = ProtocolClient(hostname, port)
        client.connect(timeout)

        # Send the keepalive packet twice as often as required
        if keepalive is not None:
            keepalive /= 2.0
        while not self._stop.wait(keepalive):

            # Keep trying to send the keep-alive packet, if this fails,
            # keep trying to reconnect until it succeeds.
            while not self._stop.is_set():
                try:
                    client.job_keepalive(job_id, timeout=timeout)
                    break
                except (ProtocolTimeoutError, IOError, OSError):
                    # Something went wrong, reconnect, after a delay which
                    # may be interrupted by the thread being stopped

                    # pylint: disable=protected-access
                    client._close()
                    if not self._stop.wait(reconnect_delay):
                        try:
                            client.connect(timeout)
                        except (IOError, OSError):
                            client.close()


if __name__ == "__main__":
    hostname = sys.argv[1]
    port = int(sys.argv[2])
    job_id = int(sys.argv[3])
    keepalive = float(sys.argv[4])
    timeout = float(sys.argv[5])
    reconnect_delay = float(sys.argv[6])
    keep_alive = KeepAliveProcess()
    exit_thread = threading.Thread(target=_wait_for_exit, args=(keep_alive,))
    exit_thread.daemon = True
    exit_thread.start()
    keep_alive.run(hostname, port, job_id, keepalive, timeout, reconnect_delay)
