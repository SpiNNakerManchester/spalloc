import pytest

from mock import Mock

import datetime

from spalloc.scripts.ps import \
    main, render_job_list, VERSION_RANGE_START, VERSION_RANGE_STOP
from spalloc.term import Terminal
from spalloc import JobState


@pytest.mark.parametrize("machine", [None, "a"])
@pytest.mark.parametrize("owner", [None, "you"])
def test_render_job_list(machine, owner):
    t = Terminal(force=False)

    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0).timestamp()

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

    assert render_job_list(t, jobs, machine, owner) == (
        "ID  State  Power  Boards  Machine  Created at           Keepalive  Owner\n" +  # noqa
        (" 1  ready  on          1  a        01/01/1970 00:00:00  60.0       me\n"      # noqa
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


def test_args_from_file(basic_config_file, basic_job_kwargs, monkeypatch):
    # Mock out the ProtocolClient
    import spalloc.scripts.ps
    pc = Mock()
    PC = Mock(return_value=pc)
    pc.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    pc.list_jobs.return_value = []
    monkeypatch.setattr(spalloc.scripts.ps, "ProtocolClient", PC)
    render_job_list = Mock()
    monkeypatch.setattr(spalloc.scripts.ps, "render_job_list", render_job_list)

    assert main("".split()) == 0

    PC.assert_called_once_with(basic_job_kwargs["hostname"],
                               basic_job_kwargs["port"])
    assert render_job_list.mock_calls[0][1][1] == []
    assert render_job_list.mock_calls[0][1][2] is None
    assert render_job_list.mock_calls[0][1][3] is None


def test_args(basic_config_file, basic_job_kwargs, monkeypatch):
    # Mock out the ProtocolClient
    import spalloc.scripts.ps
    pc = Mock()
    PC = Mock(return_value=pc)
    pc.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    pc.list_jobs.return_value = []
    pc.wait_for_notification.side_effect = KeyboardInterrupt()
    monkeypatch.setattr(spalloc.scripts.ps, "ProtocolClient", PC)
    render_job_list = Mock()
    monkeypatch.setattr(spalloc.scripts.ps, "render_job_list", render_job_list)

    assert main("--hostname pstastic --port 10 --timeout 9.0 "
                "--machine foo --owner bar --watch".split()) == 0

    PC.assert_called_once_with("pstastic", 10)
    pc.wait_for_notification.assert_called_once_with()
    assert render_job_list.mock_calls[0][1][1] == []
    assert render_job_list.mock_calls[0][1][2] == "foo"
    assert render_job_list.mock_calls[0][1][3] == "bar"


def test_connection_error(basic_config_file, monkeypatch):
    # Mock out the ProtocolClient
    import spalloc.scripts.ps
    pc = Mock()
    PC = Mock(return_value=pc)
    pc.connect.side_effect = IOError()
    monkeypatch.setattr(spalloc.scripts.ps, "ProtocolClient", PC)

    assert main("".split()) == 1


@pytest.mark.parametrize("version", [(0, 0, 0), VERSION_RANGE_STOP])
def test_version_error(basic_config_file, version, monkeypatch):
    # Mock out the ProtocolClient
    import spalloc.scripts.ps
    pc = Mock()
    PC = Mock(return_value=pc)
    pc.version.return_value = ".".join(map(str, version))
    monkeypatch.setattr(spalloc.scripts.ps, "ProtocolClient", PC)

    assert main("".split()) == 2


def test_watch(basic_config_file, basic_job_kwargs, monkeypatch):
    # Mock out the ProtocolClient
    import spalloc.scripts.ps
    pc = Mock()
    PC = Mock(return_value=pc)
    pc.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    pc.list_jobs.return_value = []
    pc.wait_for_notification.side_effect = [None, KeyboardInterrupt]
    monkeypatch.setattr(spalloc.scripts.ps, "ProtocolClient", PC)

    assert main("--watch".split()) == 0

    assert len(pc.list_jobs.mock_calls) == 2
