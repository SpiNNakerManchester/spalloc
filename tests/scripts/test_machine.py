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

import pytest
from mock import Mock, MagicMock
from spalloc.term import Terminal
from spalloc.scripts.machine import (
    main, generate_keys, list_machines, show_machine)
from spalloc.scripts.support import (
    VERSION_RANGE_START, VERSION_RANGE_STOP, Terminate)
from spalloc.protocol_client import ProtocolError


@pytest.fixture
def client(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    client.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    client.__exit__.return_value = False
    monkeypatch.setattr(main,
                        "client_factory",
                        Mock(return_value=client))
    return client


def test_generate_keys():
    actual = [v for v, _ in zip(generate_keys("AB"), range(8))]
    expected = ["A", "B", "AA", "AB", "BA", "BB", "AAA", "AAB"]
    assert actual == expected


def test_list_machines(capsys):
    t = Terminal(force=False)

    machines = [
        {"name": "m1", "tags": ["default"],
         "width": 2, "height": 1,
         "dead_boards": [[0, 0, 1]],
         "dead_links": []},
        {"name": "m2", "tags": ["pie", "chips"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
        {"name": "m3", "tags": ["default"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
    ]

    jobs = [
        # On m1
        {"job_id": 0, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m1", "boards": [[0, 0, 0]]},
        {"job_id": 1, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m1", "boards": [[0, 0, 1], [0, 0, 2]]},
        # On m2
        {"job_id": 2, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m2", "boards": [[0, 0, 0]]},
        # Queued
        {"job_id": 2, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 1, "power": None, "args": [], "kwargs": {},
         "allocated_machine_name": None, "boards": None},
    ]

    list_machines(t, machines, jobs)

    out, _ = capsys.readouterr()
    assert out == (
        "Name  Num boards  In-use  Jobs  Tags\n"
        "m1             5       3     2  default\n"
        "m2             3       1     1  pie, chips\n"
        "m3             3       0     0  default\n"
    )


def test_show_machine(capsys):
    t = Terminal(force=False)

    machines = [
        {"name": "m1", "tags": ["default"],
         "width": 2, "height": 1,
         "dead_boards": [[1, 0, 2]],
         "dead_links": []},
        {"name": "m2", "tags": ["pie", "chips"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
    ]

    jobs = [
        # On m1
        {"job_id": 0, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m1", "boards": [[0, 0, 0]]},
        {"job_id": 1, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m1", "boards": [[0, 0, 1], [0, 0, 2]]},
        # On m2
        {"job_id": 2, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m2", "boards": [[0, 0, 0]]},
        # Queued
        {"job_id": 2, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 1, "power": None, "args": [], "kwargs": {},
         "allocated_machine_name": None, "boards": None},
    ]

    show_machine(t, machines, jobs, "m1")

    out, _ = capsys.readouterr()
    assert out == (
        "  Name: m1\n"
        "  Tags: default\n"
        "In-use: 3 of 5\n"
        "  Jobs: 2\n"
        "\n"
        r" ___" "\n"
        r"/ B \___     ___" "\n"
        r"\___/ B \___/ . " "\\\n"
        r"/ A \___/ . \___/" "\n"
        r"\___/   \___/" "\n"
        "\n"
        "Key  Job ID  Num boards  Owner (Host)\n"
        "A         0           1  me\n"
        "B         1           2  me\n"
    )


def test_show_machine_compact(capsys):
    t = Terminal(force=False)

    machines = [
        {"name": "m1", "tags": ["default"],
         "width": 2, "height": 1,
         "dead_boards": [[1, 0, 2]],
         "dead_links": []},
        {"name": "m2", "tags": ["pie", "chips"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
    ]

    jobs = [
        # On m1
        {"job_id": 0, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m1", "boards": [[0, 0, 0]]},
        {"job_id": 1, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m1", "boards": [[0, 0, 1], [0, 0, 2]]},
        # On m2
        {"job_id": 2, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 2, "power": True, "args": [], "kwargs": {},
         "allocated_machine_name": "m2", "boards": [[0, 0, 0]]},
        # Queued
        {"job_id": 2, "owner": "me", "start_time": 0, "keepalive": 60.0,
         "machine": None, "state": 1, "power": None, "args": [], "kwargs": {},
         "allocated_machine_name": None, "boards": None},
    ]

    show_machine(t, machines, jobs, "m1", True)

    out, _ = capsys.readouterr()
    assert out == (
        "  Name: m1\n"
        "  Tags: default\n"
        "In-use: 3 of 5\n"
        "  Jobs: 2\n"
        "\n"
        r" ___" "\n"
        r"/ B \___     ___" "\n"
        r"\___/ B \___/ . " "\\\n"
        r"/ A \___/ . \___/" "\n"
        r"\___/   \___/" "\n"
        "\n"
        "A:0  B:1\n"
    )


def test_show_machine_fail():
    t = Terminal(force=False)

    machines = [
        {"name": "m1", "tags": ["default"],
         "width": 2, "height": 1,
         "dead_boards": [[0, 0, 1]],
         "dead_links": []},
    ]

    jobs = []

    with pytest.raises(Terminate) as exn:
        show_machine(t, machines, jobs, "missing")
    assert exn.value._code == 6


def test_no_hostname(no_config_files):
    with pytest.raises(SystemExit):
        main("".split())


def test_detailed_without_machine(basic_config_file):
    with pytest.raises(SystemExit):
        main("--detailed".split())


@pytest.mark.parametrize("version", [(0, 0, 0),
                                     VERSION_RANGE_STOP])
def test_bad_version(basic_config_file, client, version):
    client.version.return_value = ".".join(map(str, version))
    with pytest.raises(SystemExit) as exn:
        main("".split())
    assert exn.value.code == 2


def test_io_error(basic_config_file, client):
    client.version.side_effect = ProtocolError()
    assert main("".split()) == 1


def test_default_list(basic_config_file, client):
    client.list_machines.return_value = []
    client.list_jobs.return_value = []
    assert main("".split()) == 0


def test_specify_machine(basic_config_file, client):
    client.list_machines.return_value = [
        {"name": "m", "tags": ["default"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
    ]
    client.list_jobs.return_value = []
    assert main("m".split()) == 0


def test_specify_missing_machine(basic_config_file, client):
    client.list_machines.return_value = [
        {"name": "m", "tags": ["default"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
    ]
    client.list_jobs.return_value = []
    with pytest.raises(SystemExit) as exn:
        main("n".split())
    assert exn.value.code == 6


@pytest.mark.parametrize("args", ["-w", "m -w"])
def test_watch(basic_config_file, client, args):
    client.list_machines.return_value = [
        {"name": "m", "tags": ["default"],
         "width": 1, "height": 1,
         "dead_boards": [],
         "dead_links": []},
    ]
    client.list_jobs.return_value = []

    client.wait_for_notification.side_effect = [None, KeyboardInterrupt()]
    assert main(args.split()) == 0
    assert len(client.wait_for_notification.mock_calls) == 2


def test_watch_fail(basic_config_file, client):
    client.list_machines.return_value = []
    client.list_jobs.return_value = []

    client.wait_for_notification.side_effect = [None, KeyboardInterrupt()]
    with pytest.raises(SystemExit) as exn:
        main("m -w".split())
    assert exn.value.code == 6
    assert len(client.wait_for_notification.mock_calls) == 0
