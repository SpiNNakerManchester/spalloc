from spalloc.protocol_client import ProtocolClient, ProtocolTimeoutError
import sys
import threading

stop = threading.Event()


def wait_for_exit():
    global stop
    for line in sys.stdin:
        if line.strip() == "exit":
            stop.set()


if __name__ == "__main__":
    hostname = sys.argv[1]
    port = int(sys.argv[2])
    job_id = int(sys.argv[3])
    keepalive = float(sys.argv[4])
    timeout = float(sys.argv[5])
    reconnect_delay = float(sys.argv[6])
    exit_thread = threading.Thread(target=wait_for_exit)
    exit_thread.daemon = True
    exit_thread.start()

    """Background keep-alive thread."""
    client = ProtocolClient(hostname, port)
    client.connect(timeout)

    # Send the keepalive packet twice as often as required
    if keepalive is not None:
        keepalive /= 2.0
    while not stop.wait(keepalive):

        # Keep trying to send the keep-alive packet, if this fails,
        # keep trying to reconnect until it succeeds.
        while not stop.is_set():
            try:
                client.job_keepalive(job_id, timeout=timeout)
                break
            except (ProtocolTimeoutError, IOError, OSError):
                # Something went wrong, reconnect, after a delay which
                # may be interrupted by the thread being stopped

                # pylint: disable=protected-access
                client._close()
                if not stop.wait(reconnect_delay):
                    client.connect(timeout)
