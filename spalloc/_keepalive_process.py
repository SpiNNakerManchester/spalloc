""" A script for keeping Spalloc jobs alive, intended to only ever be run\
    from the Spalloc client itself.
"""


from spalloc.protocol_client import ProtocolClient, ProtocolTimeoutError
import sys
import threading


def wait_for_exit(stop_event):
    """ Listens to stdin for a line equal to 'exit' or end-of-file and then\
        notifies the given event (that it is time to stop keeping the Spalloc\
        job alive). 

    :param stop_event: Used to notify another thread that is time to stop.
    :type stop_event: threading.Event
    """
    for line in sys.stdin:
        if line.strip() == "exit":
            break
    stop_event.set()


def keep_job_alive(hostname, port, job_id, keepalive_period, timeout,
               reconnect_delay, stop_event):
    """ Keeps a Spalloc job alive. Run as a separate process to the main\
        Spalloc client.

    :param hostname: The address of the Spalloc server.
    :param port: The port of the Spalloc server.
    :param job_id: The ID of the Spalloc job to keep alive.
    :param keepalive_period: \
        How long will the job live without a keep-alive message being sent.
    :param timeout: The communication timeout.
    :param reconnect_delay: \
        The delay before reconnecting on communication failure.
    :param stop_event: Used to notify this function that it is time to stop \
        keeping the job alive.
    :type stop_event: threading.Event
    """
    client = ProtocolClient(hostname, port)
    client.connect(timeout)

    # Send the keepalive packet twice as often as required
    if keepalive_period is not None:
        keepalive_period /= 2.0
    while not stop_event.wait(keepalive_period):

        # Keep trying to send the keep-alive packet, if this fails,
        # keep trying to reconnect until it succeeds.
        while not stop_event.is_set():
            try:
                client.job_keepalive(job_id, timeout=timeout)
                break
            except (ProtocolTimeoutError, IOError, OSError):
                # Something went wrong, reconnect, after a delay which
                # may be interrupted by the thread being stopped

                # pylint: disable=protected-access
                client._close()
                if not stop_event.wait(reconnect_delay):
                    try:
                        client.connect(timeout)
                    except (IOError, OSError):
                        client.close()


if __name__ == "__main__":
    if len(sys.argv) != 7:
        sys.stderr.write(
            "wrong # args: should be '" + sys.argv[0] + " hostname port "
            "job_id keepalive_delay comms_timeout reconnect_delay'\n")
        sys.exit(1)
    hostname = sys.argv[1]
    port = int(sys.argv[2])
    job_id = int(sys.argv[3])
    keepalive = float(sys.argv[4])
    timeout = float(sys.argv[5])
    reconnect_delay = float(sys.argv[6])

    # Set things up so that we can detect when to stop
    stop_event = threading.Event()
    stdin_watcher_thread = threading.Thread(
        target=wait_for_exit, args=(stop_event,), daemon=True)
    stdin_watcher_thread.start()

    # Start keeping the job alive
    keep_job_alive(hostname, port, job_id, keepalive, timeout,
                   reconnect_delay, stop_event)
