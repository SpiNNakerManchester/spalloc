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

import collections
import datetime
from mock import Mock, MagicMock  # type: ignore[import]
import pytest
from spalloc_client.scripts.ps import main, render_job_list
from spalloc_client.scripts.support import (
    VERSION_RANGE_START, VERSION_RANGE_STOP)
from spalloc_client.term import Terminal
from spalloc_client import JobState


@pytest.fixture
def client_factory(monkeypatch):
    mock = Mock()
    monkeypatch.setattr(main, "client_factory", mock)
    return mock


@pytest.fixture
def client(client_factory):
    client = MagicMock()
    client.__enter__.return_value = client
    client.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    client.__exit__.return_value = False
    client_factory.return_value = client
    return client


@pytest.fixture
def faux_render(monkeypatch):
    import spalloc_client.scripts.ps
    render_job_list = Mock()
    monkeypatch.setattr(
        spalloc_client.scripts.ps, "render_job_list", render_job_list)
    return render_job_list


@pytest.mark.parametrize("machine", [None, "a"])
@pytest.mark.parametrize("owner", [None, "you"])
def test_render_job_list(machine, owner):
    t = Terminal(force=False)

    epoch = int(datetime.datetime(1970, 1, 1, 0, 0, 0).strftime("%s"))

    jobs = [
        # A ready, powered-on job
        {
            "job_id": 1,
            "owner": "me",
            "start_time": epoch,
            "keepalive": 60.0,
            "machine": None,
            "state": int(JobState.ready),
            "power": True,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": "a",
            "boards": [[[0, 0], "m00"]],
        },
        # A ready, powered-on job with a keepalive host
        {
            "job_id": 1,
            "owner": "me",
            "start_time": epoch,
            "keepalive": 60.0,
            "machine": None,
            "state": int(JobState.ready),
            "power": True,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": "a",
            "boards": [[[0, 0], "m00"]],
            "keepalivehost": "1.2.3.4",
        },
        # A ready, powered-off job
        {
            "job_id": 2,
            "owner": "me",
            "start_time": epoch,
            "keepalive": 60.0,
            "machine": None,
            "state": int(JobState.ready),
            "power": False,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": "b",
            "boards": [[[0, 0], "m00"]],
        },
        # A powering-on job
        {
            "job_id": 3,
            "owner": "you",
            "start_time": epoch,
            "keepalive": 60.0,
            "machine": None,
            "state": int(JobState.power),
            "power": True,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": "a",
            "boards": [[[0, 0], "m00"]],
        },
        # A powering-off job
        {
            "job_id": 4,
            "owner": "you",
            "start_time": epoch,
            "keepalive": 60.0,
            "machine": None,
            "state": int(JobState.power),
            "power": False,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": "b",
            "boards": [[[0, 0], "m00"]],
        },
        # A queued job
        {
            "job_id": 5,
            "owner": "me",
            "start_time": epoch,
            "keepalive": 60.0,
            "machine": None,
            "state": int(JobState.queued),
            "power": None,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": None,
            "boards": None,
        },
        # A non-keepalive job with an unknown state
        {
            "job_id": 6,
            "owner": "you",
            "start_time": epoch,
            "keepalive": None,
            "machine": None,
            "state": -1,
            "power": None,
            "args": [],
            "kwargs": {},
            "allocated_machine_name": None,
            "boards": None,
        },
    ]

    nt = collections.namedtuple("args", "machine,owner")
    assert render_job_list(t, jobs, nt(machine, owner)) == (
        "ID  State  Power  Boards  Machine  Created at           Keepalive  Owner (Host)\n" +  # noqa
        (" 1  ready  on          1  a        01/01/1970 00:00:00  60.0       me\n"      # noqa
         if not owner else "") +
        (" 1  ready  on          1  a        01/01/1970 00:00:00  60.0       me (1.2.3.4)\n"  # noqa
         if not owner else "") +
        (" 2  ready  off         1  b        01/01/1970 00:00:00  60.0       me\n"      # noqa
         if not owner and not machine else "") +
        " 3  power  on          1  a        01/01/1970 00:00:00  60.0       you\n" +    # noqa
        (" 4  power  off         1  b        01/01/1970 00:00:00  60.0       you\n"     # noqa
         if not machine else "") +
        (" 5  queue                          01/01/1970 00:00:00  60.0       me\n"      # noqa
         if not owner and not machine else "") +
        (" 6  -1                             01/01/1970 00:00:00  None       you"       # noqa
         if not machine else "")
    ).rstrip()


def test_args_no_hostname(no_config_files):
    with pytest.raises(SystemExit):
        main("".split())


def test_args_from_file(basic_config_file, basic_job_kwargs, client_factory,
                        client, faux_render):
    client.list_jobs.return_value = []
    assert main("".split()) == 0
    client_factory.assert_called_once_with(basic_job_kwargs["hostname"],
                                           basic_job_kwargs["port"])
    assert faux_render.mock_calls[0][1][1] == []
    assert faux_render.mock_calls[0][1][2].machine is None
    assert faux_render.mock_calls[0][1][2].owner is None


def test_args(basic_config_file, basic_job_kwargs, client_factory, client,
              faux_render):
    client.list_jobs.return_value = []
    client.wait_for_notification.side_effect = KeyboardInterrupt()
    assert main("--hostname pstastic --port 10 --timeout 9.0 "
                "--machine foo --owner bar --watch".split()) == 0
    client_factory.assert_called_once_with("pstastic", 10)
    client.wait_for_notification.assert_called_once_with()
    assert faux_render.mock_calls[0][1][1] == []
    assert faux_render.mock_calls[0][1][2].machine == "foo"
    assert faux_render.mock_calls[0][1][2].owner == "bar"


def test_connection_error(basic_config_file, client):
    client.list_jobs.side_effect = IOError

    assert main("".split()) == 1


@pytest.mark.parametrize("version", [(0, 0, 0), VERSION_RANGE_STOP])
def test_version_error(basic_config_file, version, client):
    client.version.return_value = ".".join(map(str, version))
    with pytest.raises(SystemExit) as exn:
        main("".split())
    assert exn.value.code == 2


def test_watch(basic_config_file, basic_job_kwargs, client):
    client.list_jobs.return_value = []
    client.wait_for_notification.side_effect = [None, KeyboardInterrupt]

    assert main("--watch".split()) == 0

    assert len(client.list_jobs.mock_calls) == 2
