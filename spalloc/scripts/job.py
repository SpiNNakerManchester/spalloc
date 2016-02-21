import sys
import argparse
import datetime

from collections import OrderedDict

from spalloc import config
from spalloc import \
    __version__, ProtocolClient, ProtocolTimeoutError, JobState
from spalloc.term import Terminal, render_definitions


VERSION_RANGE_START = (0, 1, 0)
VERSION_RANGE_STOP = (2, 0, 0)


def show_job_info(client, timeout, job_id):
    info = OrderedDict()

    job_state = client.get_job_state(job_id, timeout=timeout)

    state = JobState(job_state["state"])

    info["Job ID"] = job_id
    if job_state["start_time"] is not None:
        info["Start time"] = datetime.datetime.fromtimestamp(
            job_state["start_time"]).strftime('%d/%m/%Y %H:%M:%S')
    info["State"] = state.name
    if (state == JobState.queued or state == JobState.power or
            state == JobState.ready):
        info["Keepalive"] = job_state["keepalive"]

        if state == JobState.power or state == JobState.ready:
            info["Board power"] = "on" if job_state["power"] else "off"

            machine_info = client.get_job_machine_info(job_id, timeout=timeout)

            if machine_info["connections"] is not None:
                connections = sorted(machine_info["connections"])
                info["Hostname"] = connections[0][1]
                info["Num boards"] = len(connections)
            if machine_info["width"] is not None:
                info["Width"] = machine_info["width"]
            if machine_info["height"] is not None:
                info["Height"] = machine_info["height"]
            if machine_info["machine_name"] is not None:
                info["Running on"] = machine_info["machine_name"]
    elif state == JobState.destroyed:
        info["Reason"] = job_state["reason"]

    print(render_definitions(info))

    return 0


def watch_job(client, timeout, job_id):
    t = Terminal()

    client.notify_job(job_id, timeout=timeout)
    while True:
        t.stream.write(t.clear_screen())
        show_job_info(client, timeout, job_id)

        try:
            client.wait_for_notification()
            print()
        except KeyboardInterrupt:
            # Gracefully exit
            print()
            break

    return 0


def power_job(client, timeout, job_id, power):
    if power:
        client.power_on_job_boards(job_id, timeout=timeout)
    else:
        client.power_off_job_boards(job_id, timeout=timeout)

    # Wait for power command to complete...
    while True:
        client.notify_job(job_id, timeout=timeout)
        state = client.get_job_state(job_id, timeout=timeout)

        if state["state"] == JobState.ready:
            # Power command completed
            return 0
        elif state["state"] == JobState.power:
            # Wait for change...
            try:
                client.wait_for_notification()
            except KeyboardInterrupt:
                # If interrupted, quietly return an error state
                return 7
        else:
            # In an unknown state, perhaps the job was queued etc.
            sys.stderr.write(
                "Error: Cannot power {} job {} in state {}.\n".format(
                    "on" if power else "off",
                    job_id,
                    JobState(state["state"]).name))
            return 8


def list_ips(client, timeout, job_id):
    info = client.get_job_machine_info(job_id, timeout=timeout)
    connections = info["connections"]
    if connections is not None:
        print("x,y,hostname")
        for ((x, y), hostname) in sorted(connections):
            print("{},{},{}".format(x, y, hostname))
        return 0
    else:
        sys.stderr.write(
            "Job {} does not exist or is still queued.\n".format(
                job_id))
        return 9


def destroy_job(client, timeout, job_id, reason=None):
    client.destroy_job(job_id, reason, timeout=timeout)
    return 0


def main(argv=None):
    cfg = config.read_config()

    parser = argparse.ArgumentParser(
        description="Manage running jobs.")

    parser.add_argument("--version", "-V", action="version",
                        version=__version__)

    parser.add_argument("job_id", type=int, nargs="?",
                        help="the job ID of interest, optional if the current "
                             "owner only has one job")

    parser.add_argument("--owner", "-o", default=cfg["owner"],
                        help="if no job ID is provided and this owner has "
                             "only one job, this job is assumed "
                             "(default: %(default)s)")

    control_args = parser.add_mutually_exclusive_group()

    control_args.add_argument("--info", "-i", action="store_true",
                              help="Show basic job information (the default)")
    control_args.add_argument("--watch", "-w", action="store_true",
                              help="Watch this job for state changes.")
    control_args.add_argument("--power-on", "--reset", "-p", "-r",
                              action="store_true",
                              help="power-on or reset the job's boards")
    control_args.add_argument("--power-off", action="store_true",
                              help="power-off the job's boards")
    control_args.add_argument("--ethernet-ips", "-e", action="store_true",
                              help="output the IPs of all Ethernet connected "
                                   "chips as a CSV")
    control_args.add_argument("--destroy", "-D", nargs="?", metavar="REASON",
                              const="",
                              help="destroy a queued or running job")

    server_args = parser.add_argument_group("spalloc server arguments")

    server_args.add_argument("--hostname", "-H", default=cfg["hostname"],
                             help="hostname or IP of the spalloc server "
                                  "(default: %(default)s)")
    server_args.add_argument("--port", "-P", default=cfg["port"],
                             type=int,
                             help="port number of the spalloc server "
                                  "(default: %(default)s)")
    server_args.add_argument("--timeout", default=cfg["timeout"],
                             type=float, metavar="SECONDS",
                             help="seconds to wait for a response "
                                  "from the server (default: %(default)s)")

    args = parser.parse_args(argv)

    # Fail if server not specified
    if args.hostname is None:
        parser.error("--hostname of spalloc server must be specified")

    # Fail if job *and* owner not specified
    if args.job_id is None and args.owner is None:
        parser.error("job ID (or --owner) not specified")

    client = ProtocolClient(args.hostname, args.port)
    try:
        # Connect to server and ensure compatible version
        client.connect()
        version = tuple(
            map(int, client.version(timeout=args.timeout).split(".")))
        if not (VERSION_RANGE_START <= version < VERSION_RANGE_STOP):
            sys.stderr.write("Incompatible server version ({}).\n".format(
                ".".join(map(str, version))))
            return 2

        # If no Job ID specified, attempt to discover one
        if args.job_id is None:
            jobs = client.list_jobs(timeout=args.timeout)
            job_ids = [job["job_id"] for job in jobs
                       if job["owner"] == args.owner]
            if len(job_ids) == 0:
                sys.stderr.write(
                    "Owner {} has no live jobs.\n".format(args.owner))
                return 3
            elif len(job_ids) > 1:
                sys.stderr.write("Ambiguous: {} has {} live jobs: {}\n".format(
                    args.owner, len(job_ids), ", ".join(map(str, job_ids))))
                return 3
            else:
                args.job_id = job_ids[0]

        # Do as the user asked
        if args.watch:
            return watch_job(client, args.timeout, args.job_id)
        elif args.power_on:
            return power_job(client, args.timeout, args.job_id, True)
        elif args.power_off:
            return power_job(client, args.timeout, args.job_id, False)
        elif args.ethernet_ips:
            return list_ips(client, args.timeout, args.job_id)
        elif args.destroy is not None:
            # Set default destruction message
            if args.destroy == "" and args.owner:
                args.destroy = "Destroyed by {}".format(args.owner)
            return destroy_job(client, args.timeout, args.job_id, args.destroy)
        else:
            return show_job_info(client, args.timeout, args.job_id)

    except (IOError, OSError, ProtocolTimeoutError) as e:
        sys.stderr.write("Error communicating with server: {}\n".format(e))
        return 1
    finally:
        client.close()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
