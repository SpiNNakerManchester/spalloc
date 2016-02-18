import os
import sys
import argparse
import tempfile
import logging
import subprocess
import colorama

from collections import OrderedDict

from six import iteritems
from six.moves import input

from spalloc import config
from spalloc import Job, JobState, __version__
from spalloc.term import Terminal


try:
    from rig.machine_control import MachineController
except ImportError:  # pragma: no cover
    MachineController = None



def write_ips_to_csv(connections, ip_file_filename):
    """Write the supplied IP addresses to a CSV file.
    
    The produced CSV has three columns: x, y and hostname where x and y give
    chip coordinates of Ethernet-connected chips and hostname gives the IP
    address for that chip.
    
    Parameters
    ----------
    connections : {(x, y): hostname, ...}
    ip_file_filename : str
    """
    with open(ip_file_filename, "w") as f:
        f.write("x,y,hostname\n")
        f.write("".join("{},{},{}\n".format(x, y, hostname)
                        for (x, y), hostname
                        in sorted(iteritems(connections))))

def print_info(machine_info, ip_file_filename):
    """Print the current machine info in a human-readable form and wait for the
    user to press enter.
    
    Parameters
    ----------
    machine_info : :py:class:`.JobMachineInfoTuple`
    ip_file_filename : str
    """
    t = Terminal()
    
    to_print = OrderedDict()
    
    to_print["Hostname"] = t.bright(machine_info.connections[(0, 0)])
    to_print["Width"] = machine_info.width
    to_print["Height"] = machine_info.height
    
    if len(machine_info.connections) > 1:
        to_print["Num boards"] = len(machine_info.connections)
        to_print["All hostnames"] = ip_file_filename
    
    to_print["Running on"] = machine_info.machine_name
    
    col_width = max(map(len, to_print))
    for name, value in iteritems(to_print):
        print("{:>{}s}: {}".format(name, col_width, value))
    
    try:
        input(t.dim("<Press enter to destroy job>"))
    except KeyboardInterrupt:
        print()


def run_command(command, machine_info, ip_file_filename):
    """Run a user-specified command, substituting arguments for values taken
    from the allocated board.
    
    Parameters
    ----------
    logger : :py:class:`logging.Logger`
    command : [command, arg, ...]
    machine_info : :py:class:`.JobMachineInfoTuple`
    ip_file_filename : str
    
    Returns
    -------
    int
        The return code of the supplied command.
    """
    
    root_hostname = machine_info.connections[(0, 0)]
    
    # Print essential info in log
    logging.info("Allocated %d x %d chip machine in '%s'",
                 machine_info.width, machine_info.height,
                 machine_info.machine_name)
    logging.info("Chip (0, 0) IP: %s", root_hostname)
    logging.info("All board IPs listed in: %s", ip_file_filename)
    
    # Make substitutions in command arguments
    command = [arg.format(root_hostname,
                          hostname=root_hostname,
                          w=machine_info.width,
                          width=machine_info.width,
                          h=machine_info.height,
                          height=machine_info.height,
                          ethernet_ips=ip_file_filename)
               for arg in command]
    
    p = subprocess.Popen(command, shell=True)
    
    # Pass through keyboard interrupts
    while True:
        try:
            return p.wait()
        except KeyboardInterrupt:
            p.terminate()


def main(argv=None):
    # Colour support for Windows
    colorama.init()
    t = Terminal(stream=sys.stderr)
    
    cfg = config.read_config()
    
    parser = argparse.ArgumentParser(
        description="Request (and allocate) a SpiNNaker machine.")
    
    parser.add_argument("--version", "-V", action="version",
                        version=__version__)
    
    parser.add_argument("--quiet", "-q", action="store_true",
                        default=False,
                        help="suppress informational messages")
    parser.add_argument("--debug", action="store_true",
                        default=False,
                        help="enable additional diagnostic information")
    
    if MachineController is not None:
        parser.add_argument("--boot", "-B", action="store_true",
                            default=False,
                            help="boot the machine once powered on")
    
    allocation_args = parser.add_argument_group(
        "allocation requirement arguments")
    allocation_args.add_argument("what", nargs="*", default=[], type=int,
                                 metavar="WHAT",
                                 help="what to allocate: nothing or 1 "
                                      "requests 1 SpiNN-5 board, NUM requests "
                                      "at least NUM SpiNN-5 boards, WIDTH "
                                      "HEIGHT means WIDTHxHEIGHT triads of "
                                      "SpiNN-5 boards and X Y Z requests a "
                                      "board the specified logical board "
                                      "coordinate.")
    allocation_args.add_argument("--machine", "-m", nargs="?",
                                 default=cfg["machine"],
                                 help="only allocate boards which are part "
                                      "of a specific machine, or any machine "
                                      "if no machine is given "
                                      "(default: %(default)s)")
    allocation_args.add_argument("--tags", "-t", nargs="*", metavar="TAG",
                                 default=cfg["tags"] or ["default"],
                                 help="only allocate boards which have (at "
                                      "least) the specified flags "
                                      "(default: {})".format(
                                          " ".join(cfg["tags"] or [])))
    allocation_args.add_argument("--min-ratio", type=float, metavar="RATIO",
                                 default=cfg["min_ratio"],
                                 help="when allocating by number of boards, "
                                      "require that the allocation be at "
                                      "least as square as this ratio "
                                      "(default: %(default)s)")
    allocation_args.add_argument("--max-dead-boards", type=int, metavar="NUM",
                                 default=(-1 if cfg["max_dead_boards"] is None
                                          else cfg["max_dead_boards"]),
                                 help="boards allowed to be "
                                      "dead in the allocation, or -1 to allow "
                                      "any number of dead boards "
                                      "(default: %(default)s)")
    allocation_args.add_argument("--max-dead-links", type=int, metavar="NUM",
                                 default=(-1 if cfg["max_dead_links"] is None
                                          else cfg["max_dead_links"]),
                                 help="inter-board links allowed to be "
                                      "dead in the allocation, or -1 to allow "
                                      "any number of dead links "
                                      "(default: %(default)s)")
    allocation_args.add_argument("--require-torus", "-w", action="store_true",
                                 default=cfg["require_torus"],
                                 help="require that the allocation contain "
                                      "torus (a.k.a. wrap-around) "
                                      "links {}".format(
                                          "(default)" if cfg["require_torus"]
                                          else ""
                                      ))
    allocation_args.add_argument("--no-require-torus", "-W",
                                 action="store_false", dest="require_torus",
                                 help="do not require that the allocation "
                                      "contain torus (a.k.a. wrap-around) "
                                      "links {}".format(
                                          "" if cfg["require_torus"]
                                          else "(default)"
                                      ))
    
    command_args = parser.add_argument_group("command wrapping arguments")
    command_args.add_argument("--command", "-c", nargs=argparse.REMAINDER,
                              help="execute the specified command once boards "
                                   "have been allocated and deallocate the boards "
                                   "when the application exits ({} and {hostname} "
                                   "are substituted for the hostname of the "
                                   "SpiNNaker chip at (0, 0), {w} and {h} give "
                                   "the dimensions of the SpiNNaker machine in "
                                   "chips, {ethernet_ips} is a temporary file "
                                   "containing a CSV with three columns: x, y and "
                                   "hostname giving the hostname of each Ethernet "
                                   "connected SpiNNaker chip)")
    
    server_args = parser.add_argument_group("spalloc server arguments")
    
    server_args.add_argument("--owner", default=cfg["owner"],
                             help="by convention, the email address of the "
                                  "owner of the job (default: %(default)s)")
    server_args.add_argument("--hostname", "-H", default=cfg["hostname"],
                             help="hostname or IP of the spalloc server "
                                  "(default: %(default)s)")
    server_args.add_argument("--port", "-P", default=cfg["port"],
                             type=int,
                             help="port number of the spalloc server "
                                  "(default: %(default)s)")
    server_args.add_argument("--keepalive", type=int, metavar="SECONDS",
                             default=(-1 if cfg["keepalive"] is None
                                      else cfg["keepalive"]),
                             help="the interval at which to require "
                                  "keepalive messages to be sent to "
                                  "prevent the server cancelling the "
                                  "job, or -1 to not require keepalive "
                                  "messages (default: %(default)s)")
    server_args.add_argument("--reconnect-delay",
                             default=cfg["reconnect_delay"],
                             type=float, metavar="SECONDS",
                             help="seconds to wait before "
                                  "reconnecting to the server if the "
                                  "connection is lost (default: %(default)s)")
    server_args.add_argument("--timeout", default=cfg["timeout"],
                             type=float, metavar="SECONDS",
                             help="seconds to wait for a response "
                                  "from the server (default: %(default)s)")
    
    args = parser.parse_args(argv)
    
    # Fail if no owner is defined
    if not args.owner:
        parser.error(
            "--owner must be specified (typically your email address)")
    
    # Fail if server not specified
    if args.hostname is None:
        parser.error("--hostname of spalloc server must be specified")
    
    # Make sure 'what' takes the right form
    if len(args.what) not in (0, 1, 2, 3):
        parser.error("expected either no arguments, one argument, NUM, "
                     "two arguments, WIDTH HEIGHT, or three arguments X Y Z")
    
    # Unpack arguments for the job and server
    job_args = args.what
    job_kwargs = {
        "hostname": args.hostname,
        "port": args.port,
        "reconnect_delay":
            args.reconnect_delay if args.reconnect_delay >= 0.0 else None,
        "timeout": args.timeout if args.timeout >= 0.0 else None,
        "owner": args.owner,
        "keepalive": args.keepalive if args.keepalive >= 0.0 else None,
        "machine": args.machine,
        "tags": args.tags if args.machine is None else None,
        "min_ratio": args.min_ratio,
        "max_dead_boards":
            args.max_dead_boards if args.max_dead_boards >= 0.0 else None,
        "max_dead_links":
            args.max_dead_links if args.max_dead_links >= 0.0 else None,
        "require_torus": args.require_torus,
    }
    
    # Set debug level
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Create temporary file in which to write CSV of all board IPs
    _, ip_file_filename = tempfile.mkstemp(".csv", "spinnaker_ips_")
    
    def info(msg):
        if not args.quiet:
            t.stream.write("{}\n".format(msg))
    
    try:
        # Create the job
        try:
            job = Job(*job_args, **job_kwargs)
            job.create()
        except (OSError, IOError) as e:
            info(t.red("Could not connect to server: {}".format(e)))
            return 6
        try:
            # Wait for it to become ready, keeping the user informed along the way
            old_state = None
            cur_state = job.get_state().state
            while True:
                # Show debug info on state-change
                if old_state != cur_state:
                    if cur_state == JobState.queued:
                        info(t.update(t.yellow(
                            "Job {}: Waiting in queue...".format(job.id))))
                    elif cur_state == JobState.power:
                        info(t.update(t.yellow(
                            "Job {}: Waiting for power on...".format(job.id))))
                    elif cur_state == JobState.ready:
                        # Here we go!
                        break
                    elif cur_state == JobState.destroyed:
                        # Exit with error state
                        try:
                            reason = job.get_state().reason
                        except (IOError, OSError):
                            reason = None
                        
                        if reason is not None:
                            info(t.update(t.red(
                                "Job {}: Destroyed: {}".format(
                                    job.id, reason))))
                        else:
                            info(t.red("Job {}: Destroyed.".format(job.id)))
                        return 1
                    elif cur_state == JobState.unknown:
                        info(t.update(t.red(
                            "Job {}: Job not recognised by server.".format(
                                job.id))))
                        return 2
                    else:
                        info(t.update(t.red(
                            "Job {}: Entered an unrecognised state {}.".format(
                                job.id, cur_state))))
                        return 3
                
                try:
                    old_state = cur_state
                    cur_state = job.wait_for_state_change(cur_state)
                except KeyboardInterrupt:
                    # Gracefully terminate from keyboard interrupt
                    info(t.update(t.red(
                        "Job {}: Destroyed by keyboard interrupt.".format(
                            job.id))))
                    return 4
            
            # Machine is now ready
            machine_info = job.get_machine_info()
            write_ips_to_csv(machine_info.connections, ip_file_filename)
            
            # Boot the machine if required
            if MachineController is not None and args.boot:
                info(t.update(t.yellow(
                    "Job {}: Booting...".format(job.id))))
                mc = MachineController(machine_info.connections[(0, 0)])
                mc.boot(machine_info.width, machine_info.height)
            
            info(t.update(t.green("Job {}: Ready!".format(job.id))))
            
            # Either run the user's application or just print the details.
            if args.command:
                return run_command(args.command, machine_info,
                                   ip_file_filename)
            else:
                print_info(machine_info, ip_file_filename)
                return 0
        finally:
            # Destroy job and disconnect client
            job.destroy()
    finally:
        # Delete IP address list file
        os.remove(ip_file_filename)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
