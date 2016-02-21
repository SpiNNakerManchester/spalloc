import pytest

from mock import Mock

from spalloc.term import Terminal

from spalloc.scripts.machine import \
    main, generate_keys, list_machines, show_machine, \
    VERSION_RANGE_START, VERSION_RANGE_STOP


@pytest.fixture
def client(monkeypatch):
    client = Mock()
    client.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    import spalloc.scripts.machine
    monkeypatch.setattr(spalloc.scripts.machine,
                        "ProtocolClient",
                        Mock(return_value=client))
    return client


def test_generate_keys():
    actual = [v for v, i in zip(generate_keys("AB"), range(8))]
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

    assert list_machines(t, machines, jobs) == 0

    out, err = capsys.readouterr()
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
         "dead_boards": [[0, 0, 1]],
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

    assert show_machine(t, machines, jobs, "m1") == 0

    out, err = capsys.readouterr()
    assert out == (
        "Name: m1\n"
        "Tags: default\n"
        "\n"
        r" ___     ___" "\n"
        r"/ B \___/ . \___" "\n"
        r"\___/ B \___/ . " "\\\n"
        r"/ A \___/ . \___/" "\n"
        r"\___/   \___/" "\n"
        "\n"
        "Key  Job ID  Num boards  Owner\n"
        "A         0           1  me\n"
        "B         1           2  me\n"
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

    assert show_machine(t, machines, jobs, "missing") == 6


def test_no_hostname(no_config_files):
    with pytest.raises(SystemExit):
        main("".split())


@pytest.mark.parametrize("version", [(0, 0, 0),
                                     VERSION_RANGE_STOP])
def test_bad_version(basic_config_file, client, version):
    client.version.return_value = ".".join(map(str, version))
    assert main("".split()) == 2


def test_io_error(basic_config_file, client):
    client.version.side_effect = IOError()
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
    assert main("n".split()) == 6


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
    assert main("m -w".split()) == 6
    assert len(client.wait_for_notification.mock_calls) == 0
