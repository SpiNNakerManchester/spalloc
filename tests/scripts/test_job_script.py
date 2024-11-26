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

from datetime import datetime
import pytest
from mock import Mock, MagicMock  # type: ignore[import]
from spalloc_client import JobState, ProtocolError
from spalloc_client.spalloc_config import TIMEOUT
from spalloc_client.term import Terminal
from spalloc_client.scripts.job import (
    show_job_info, watch_job, power_job, list_ips, destroy_job, main)
from spalloc_client.scripts.support import (
    VERSION_RANGE_START, VERSION_RANGE_STOP, Terminate)


@pytest.fixture
def mock_protocol_client(monkeypatch):
    mock_protocol_client = Mock()
    monkeypatch.setattr(main,
                        "client_factory",
                        mock_protocol_client)
    return mock_protocol_client


@pytest.fixture
def client(mock_protocol_client):
    # A mock protocol client which returns a sensible version number.
    client = MagicMock()
    mock_protocol_client.return_value = client
    client.__enter__.return_value = client
    client.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    client.__exit__.return_value = False

    return client


class TestShowJobInfo(object):

    def test_unknown(self, capsys):
        t = Terminal(force=False)
        client = Mock()
        client.list_jobs.return_value = []
        client.get_job_state.return_value = {
            "state": int(JobState.unknown),
            "power": None,
            "keepalive": None,
            "reason": None,
            "start_time": None,
        }

        show_job_info(t, client, 1.0, 123)

        out, _ = capsys.readouterr()
        assert out == ("Job ID: 123\n"
                       " State: unknown\n")

    def test_queued(self, capsys):
        t = Terminal(force=False)
        naive = datetime(2000, 1, 1, 0, 0, 0)
        aware = naive.astimezone()
        epoch = int(aware.timestamp())

        client = Mock()
        client.list_jobs.return_value = [
            {
                "job_id": 123,
                "owner": "me",
                "start_time": epoch,
                "keepalive": 60.0,
                "state": int(JobState.queued),
                "power": None,
                "args": [3, 2, 1],
                "kwargs": {"tags": ["bar"]},
                "allocated_machine_name": None,
                "boards": None,
            },
        ]
        client.get_job_machine_info.return_value = {
            "width": None, "height": None,
            "connections": None, "machine_name": None,
        }

        show_job_info(t, client, 1.0, 123)

        out, _ = capsys.readouterr()
        assert out == ("    Job ID: 123\n"
                       "     Owner: me\n"
                       "     State: queued\n"
                       "Start time: 01/01/2000 00:00:00\n"
                       " Keepalive: 60.0\n"
                       "   Request: Job(3, 2, 1,\n"
                       "                tags=['bar'])\n")

    @pytest.mark.parametrize("state", [JobState.power, JobState.ready])
    def test_power_ready(self, capsys, state):
        t = Terminal(force=False)
        naive = datetime(2000, 1, 1, 0, 0, 0)
        aware = naive.astimezone()
        epoch = int(aware.timestamp())

        client = Mock()
        client.list_jobs.return_value = [
            {
                "job_id": 123,
                "owner": "me",
                "start_time": epoch,
                "keepalive": 60.0,
                "state": int(state),
                "power": True,
                "args": [3, 2, 1],
                "kwargs": {"tags": ["bar"]},
                "allocated_machine_name": "machine",
                "boards": [[0, 0, z] for z in range(3)],
            },
        ]
        client.get_job_machine_info.return_value = {
            "width": 10,
            "height": 20,
            "connections": [[[4, 8], "board48"],
                            [[8, 4], "board84"],
                            [[0, 0], "board00"]],
            "machine_name": "machine",
        }

        show_job_info(t, client, 1.0, 123)

        out, _ = capsys.readouterr()
        assert out == ("     Job ID: 123\n"
                       "      Owner: me\n"
                       "      State: " + state.name + "\n"
                       " Start time: 01/01/2000 00:00:00\n"
                       "  Keepalive: 60.0\n"
                       "    Request: Job(3, 2, 1,\n"
                       "                 tags=['bar'])\n"
                       r" Allocation:  ___" "\n"
                       r"             / . \___" "\n"
                       r"             \___/ . " "\\\n"
                       r"             / . \___/" "\n"
                       r"             \___/" "\n"
                       "   Hostname: board00\n"
                       "      Width: 10\n"
                       "     Height: 20\n"
                       " Num boards: 3\n"
                       "Board power: on\n"
                       " Running on: machine\n")

    def test_destroyed(self, capsys):
        t = Terminal(force=False)

        client = Mock()
        client.list_jobs.return_value = []
        client.get_job_state.return_value = {
            "state": int(JobState.destroyed),
            "power": None,
            "keepalive": None,
            "reason": "foobar",
            "start_time": None,
        }

        show_job_info(t, client, 1.0, 123)

        out, _ = capsys.readouterr()
        assert out == ("Job ID: 123\n"
                       " State: destroyed\n"
                       "Reason: foobar\n")


def test_watch_job():
    t = Terminal(force=False)
    client = Mock()
    client.list_jobs.return_value = []
    client.get_job_state.return_value = {
        "state": int(JobState.unknown),
        "power": None, "keepalive": None,
        "reason": None, "start_time": None,
    }

    # Loop once and then get interrupted
    client.wait_for_notification.side_effect = [None, KeyboardInterrupt()]

    assert watch_job(t, client, 1.0, 123) == 0


class TestPowerJob(object):

    @pytest.mark.parametrize("state", [JobState.unknown, JobState.destroyed])
    @pytest.mark.parametrize("power", [True, False])
    def test_bad_state(self, state, power):
        client = Mock()
        client.get_job_state.return_value = {
            "state": int(state),
            "power": None, "keepalive": None,
            "reason": None, "start_time": None,
        }

        with pytest.raises(Terminate) as exn:
            power_job(client, 1.0, 123, power)
        assert exn.value._code == 8

    @pytest.mark.parametrize("states", [[JobState.power, JobState.ready],
                                        [JobState.ready]])
    @pytest.mark.parametrize("power", [True, False])
    def test_success(self, states, power):
        client = Mock()
        client.get_job_state.side_effect = [
            {
                "state": int(state),
                "power": power, "keepalive": 60.0,
                "reason": None, "start_time": 0,
            }
            for state in states
        ]

        power_job(client, 1.0, 123, power)

        if power:
            client.power_on_job_boards.assert_called_once_with(
                123, timeout=1.0)
        else:
            client.power_off_job_boards.assert_called_once_with(
                123, timeout=1.0)

    @pytest.mark.parametrize("power", [True, False])
    def test_interrupt(self, power):
        client = Mock()
        client.get_job_state.return_value = {
            "state": int(JobState.power),
            "power": power, "keepalive": 60.0,
            "reason": None, "start_time": 0,
        }

        client.wait_for_notification.side_effect = [None, KeyboardInterrupt()]

        with pytest.raises(Terminate) as exn:
            power_job(client, 1.0, 123, power)
        assert exn.value._code == 7

        if power:
            client.power_on_job_boards.assert_called_once_with(
                123, timeout=1.0)
        else:
            client.power_off_job_boards.assert_called_once_with(
                123, timeout=1.0)


class TestListIPs(object):

    def test_no_connections(self):
        client = Mock()
        client.get_job_machine_info.return_value = {
            "width": None, "height": None,
            "connections": None, "machine_name": None,
        }
        with pytest.raises(Terminate) as exn:
            list_ips(client, 1.0, 123)
        assert exn.value._code == 9

    def test_some_connections(self, capsys):
        client = Mock()
        client.get_job_machine_info.return_value = {
            "width": 10,
            "height": 20,
            "connections": [[[4, 8], "board48"],
                            [[8, 4], "board84"],
                            [[0, 0], "board00"]],
            "machine_name": "machine",
        }

        list_ips(client, 1.0, 123)

        out, _ = capsys.readouterr()

        assert out == ("x,y,hostname\n"
                       "0,0,board00\n"
                       "4,8,board48\n"
                       "8,4,board84\n")


def test_destroy_job():
    client = Mock()
    destroy_job(client, 1.0, 123, "foo")
    client.destroy_job.assert_called_once_with(123, "foo", timeout=1.0)


class TestMain(object):

    def test_no_hostname(self, no_config_files):
        with pytest.raises(SystemExit):
            main("".split())

    def test_no_job_id_or_owner(self, no_config_files):
        with pytest.raises(SystemExit):
            main("--hostname foo".split())

    @pytest.mark.parametrize("version",
                             [".".join(map(str, VERSION_RANGE_STOP)),
                              "0.0.0"])
    def test_bad_version(self, no_config_files, client, version):
        client.version.return_value = version
        with pytest.raises(SystemExit) as exn:
            main("--hostname foo 123".split())
        assert exn.value.code == 2

    def test_bad_connection(self, no_config_files, client):
        client.version.side_effect = ProtocolError()
        assert main("--hostname foo 123".split()) == 1

    def test_no_job_owner_has_no_jobs(self, no_config_files, client):
        client.list_jobs.return_value = [
            {"job_id": 1, "owner": "someone-else"}
        ]
        with pytest.raises(SystemExit) as exn:
            main("--hostname foo --owner bar".split())
        assert exn.value.code == 3

    def test_no_job_owner_has_many_jobs(self, no_config_files, client):
        client.list_jobs.return_value = [
            {"job_id": 1, "owner": "bar"},
            {"job_id": 2, "owner": "bar"},
        ]
        with pytest.raises(SystemExit) as exn:
            main("--hostname foo --owner bar".split())
        assert exn.value.code == 3

    def test_automatic_job_id(self, no_config_files, client):
        client.list_jobs.return_value = [
            {
                "job_id": 123,
                "owner": "bar",
                "start_time": 0,
                "keepalive": 60.0,
                "state": int(JobState.queued),
                "power": None,
                "args": [3, 2, 1],
                "kwargs": {"tags": ["bar"]},
                "allocated_machine_name": None,
                "boards": None,
            },
        ]
        client.get_job_machine_info.return_value = {
            "width": None, "height": None,
            "connections": None, "machine_name": None,
        }
        client.get_job_state.return_value = {
            "state": int(JobState.queued),
            "power": None,
            "keepalive": 60.0,
            "reason": None,
            "start_time": 0,
        }
        assert main("--hostname foo --owner bar".split()) == 0
        client.get_job_machine_info.assert_called_once_with(
            123, timeout=TIMEOUT)

    def test_manual(self, no_config_files, client):
        client.list_jobs.return_value = [
            {"job_id": 123},
            {
                "job_id": 321,
                "owner": "bar",
                "start_time": 0,
                "keepalive": 60.0,
                "state": int(JobState.queued),
                "power": None,
                "args": [3, 2, 1],
                "kwargs": {"tags": ["bar"]},
                "allocated_machine_name": None,
                "boards": None,
            },
        ]
        client.get_job_machine_info.return_value = {
            "width": None, "height": None,
            "connections": None, "machine_name": None,
        }
        client.get_job_state.return_value = {
            "state": int(JobState.queued),
            "power": None,
            "keepalive": 60.0,
            "reason": None,
            "start_time": 0,
        }
        assert main("321 --hostname foo --owner bar".split()) == 0
        client.get_job_machine_info.assert_called_once_with(
            321, timeout=TIMEOUT)

    @pytest.mark.parametrize("args", ["", "-i", "--info"])
    def test_info(self, no_config_files, client, args):
        client.list_jobs.return_value = []
        client.get_job_state.return_value = {
            "state": int(JobState.unknown),
            "power": None,
            "keepalive": None,
            "reason": None,
            "start_time": None,
        }
        assert main(("321 --hostname foo --owner bar " + args).split()) == 0
        client.get_job_state.assert_called_once_with(321, timeout=TIMEOUT)

    @pytest.mark.parametrize("args", ["-w", "--watch"])
    def test_watch(self, no_config_files, client, args):
        client.wait_for_notification.side_effect = [None, KeyboardInterrupt()]
        client.list_jobs.return_value = []
        client.get_job_state.return_value = {
            "state": int(JobState.unknown),
            "power": None,
            "keepalive": None,
            "reason": None,
            "start_time": None,
        }
        assert main(("321 --hostname foo --owner bar " + args).split()) == 0

    @pytest.mark.parametrize("args,power",
                             [("-p", True),
                              ("--power-on", True),
                              ("-r", True),
                              ("--reset", True),
                              ("--power-off", False)])
    def test_power_and_reset(self, no_config_files, client, args, power):
        client.get_job_state.return_value = {
            "state": int(JobState.ready),
            "power": power,
            "keepalive": 60.0,
            "reason": None,
            "start_time": 0,
        }
        assert main(("321 --hostname foo --owner bar " + args).split()) == 0
        if power:
            client.power_on_job_boards.assert_called_once_with(
                321, timeout=TIMEOUT)
        else:
            client.power_off_job_boards.assert_called_once_with(
                321, timeout=TIMEOUT)

    @pytest.mark.parametrize("args", ["-e", "--ethernet-ips"])
    def test_ethernet_ips(self, no_config_files, client, args):
        client.get_job_machine_info.return_value = {
            "width": 10, "height": 20,
            "connections": [[[0, 0], "board00"]],
            "machine_name": "machine",
        }
        assert main(("321 --hostname foo --owner bar " + args).split()) == 0
        client.get_job_machine_info.assert_called_once_with(
            321, timeout=TIMEOUT)

    @pytest.mark.parametrize("args,reason", [("-D", ""),
                                             ("--destroy", ""),
                                             ("-D foobar", "foobar"),
                                             ("--destroy foobar", "foobar")])
    @pytest.mark.parametrize("owner_args, owner", [("--owner me", "me"),
                                                   ("", None)])
    def test_destroy(self, no_config_files, client, args, reason,
                     owner_args, owner):
        assert main(
            ("321 --hostname foo " + owner_args + " " + args).split()) == 0

        if not reason and owner is not None:
            reason = "Destroyed by {}".format(owner)

        client.destroy_job.assert_called_once_with(
            321, reason, timeout=TIMEOUT)
