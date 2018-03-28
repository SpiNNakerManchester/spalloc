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
        print "Connect"
        client.connect(timeout)

        # Send the keepalive packet twice as often as required
        if keepalive is not None:
            keepalive /= 2.0
        print "Wait", keepalive
        while not self._stop.wait(keepalive):

            # Keep trying to send the keep-alive packet, if this fails,
            # keep trying to reconnect until it succeeds.
            print "Stop set", self._stop.is_set()
            while not self._stop.is_set():
                try:
                    print "Keepalive"
                    client.job_keepalive(job_id, timeout=timeout)
                    break
                except (ProtocolTimeoutError, IOError, OSError):
                    print "Error"
                    # Something went wrong, reconnect, after a delay which
                    # may be interrupted by the thread being stopped

                    # pylint: disable=protected-access
                    client._close()
                    print "Wait", reconnect_delay
                    if not self._stop.wait(reconnect_delay):
                        print "Reconnect"
                        try:
                            client.connect(timeout)
                            print "Reconnected"
                        except (IOError, OSError):
                            print "Reconnect Error"
                            client.close()
        print "Stopped"


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
