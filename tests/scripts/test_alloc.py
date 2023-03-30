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

import os
import tempfile
import pytest
from mock import Mock, PropertyMock
from spalloc_client import JobState, JobDestroyedError
from spalloc_client.scripts.alloc import (
    write_ips_to_csv, print_info, run_command, main)
# pylint: disable=redefined-outer-name, unused-argument


@pytest.yield_fixture
def filename():
    _, filename = tempfile.mkstemp()
    yield filename
    os.remove(filename)


@pytest.fixture
def mock_input(monkeypatch):
    m = Mock()
    import spalloc.scripts.alloc
    monkeypatch.setattr(spalloc.scripts.alloc, "_input", m)
    return m


@pytest.fixture
def mock_popen(monkeypatch):
    popen_behaviour = Mock(wait=Mock(return_value=123))
    popen_func = Mock(return_value=popen_behaviour)
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", popen_func)
    return popen_func


@pytest.fixture
def mock_job(monkeypatch):
    # A fake job which immediately exits with a connection error.
    job_returner = Mock(side_effect=OSError())
    import spalloc.scripts.alloc
    monkeypatch.setattr(spalloc.scripts.alloc, "Job", job_returner)
    return job_returner


@pytest.fixture
def mock_working_job(monkeypatch):
    job = Mock()
    job_returner = Mock(return_value=job)
    import spalloc.scripts.alloc
    monkeypatch.setattr(spalloc.scripts.alloc, "Job", job_returner)

    job.id = 123
    job.state = JobState.queued
    job.wait_for_state_change.side_effect = [JobState.power,
                                             JobState.power,
                                             JobState.ready]

    job.width = 8
    job.height = 8
    job.connections = {(0, 0): "foobar"}
    job.hostname = "foobar"
    job.machine_name = "m"

    return job


@pytest.fixture
def mock_mc(monkeypatch):
    mc = Mock(return_value=Mock())
    import spalloc.scripts.alloc
    monkeypatch.setattr(spalloc.scripts.alloc, "MachineController", mc)
    return mc


@pytest.fixture
def no_rig(monkeypatch):
    import spalloc.scripts.alloc
    monkeypatch.setattr(spalloc.scripts.alloc, "MachineController", None)


def test_write_ips_to_file_empty(filename):
    write_ips_to_csv({}, filename)

    with open(filename, "r") as f:
        assert f.read() == "x,y,hostname\n"


def test_write_ips_to_file(filename):
    write_ips_to_csv({
        (0, 0): "board-0-0",
        (4, 8): "board-4-8",
        (8, 4): "board-8-4",
    }, filename)

    with open(filename, "r") as f:
        assert f.read() == ("x,y,hostname\n"
                            "0,0,board-0-0\n"
                            "4,8,board-4-8\n"
                            "8,4,board-8-4\n")


def test_print_info_one_board(capsys, mock_input, no_colour):
    print_info("m", {(0, 0): "foobar"}, 1, 2, "/some/file")

    out, err = capsys.readouterr()

    assert out == ("  Hostname: foobar\n"
                   "     Width: 1\n"
                   "    Height: 2\n"
                   "Running on: m\n")
    assert err == ""

    mock_input.assert_called_once_with("<Press enter when done>")


def test_print_info_many_boards(capsys, mock_input, no_colour):
    print_info("m", {(0, 0): "foobar", (4, 8): "bazqux"}, 1, 2, "/some/file")

    out, err = capsys.readouterr()

    assert out == ("     Hostname: foobar\n"
                   "        Width: 1\n"
                   "       Height: 2\n"
                   "   Num boards: 2\n"
                   "All hostnames: /some/file\n"
                   "   Running on: m\n")
    assert err == ""
    mock_input.assert_called_once_with("<Press enter when done>")


def test_print_info_keyboard_interrupt(capsys, mock_input):
    # Make sure keyboard interrpt during input is handled gracefully
    mock_input.side_effect = KeyboardInterrupt()
    print_info("m", {(0, 0): "foobar"}, 1, 2, "/some/file")


@pytest.mark.parametrize("args,expected",
                         [([], ""),
                          (["foo", "bar"], "foo bar"),
                          (["foo", "oh look a 'quote"],
                           "foo 'oh look a '\"'\"'quote'"),
                          (["<{}>"], "'<foobar>'"),
                          (["<{hostname}>"], "'<foobar>'"),
                          (["<{w}>"], "'<1>'"),
                          (["<{width}>"], "'<1>'"),
                          (["<{h}>"], "'<2>'"),
                          (["<{height}>"], "'<2>'"),
                          (["<{ethernet_ips}>"], "'</some/file>'"),
                          (["<{id}>"], "'<12>'"),
                          ])
def test_run_command(mock_popen, args, expected):
    run_command(args, 12, "m", {(0, 0): "foobar", (4, 8): "bazqux"}, 1, 2,
                "/some/file")
    mock_popen.assert_called_once_with(expected, shell=True)


def test_run_command_kill_and_return(mock_popen):
    mock_popen.return_value = Mock()
    mock_popen.return_value.wait.side_effect = [KeyboardInterrupt(), 2]
    assert run_command([], 12, "m", {(0, 0): "foobar", (4, 8): "bazqux"}, 1, 2,
                       "/some/file") == 2
    mock_popen.return_value.terminate.assert_called_once_with()


def test_no_owner(no_config_files):
    with pytest.raises(SystemExit):
        main("--hostname foobar".split())


def test_no_hostname(no_config_files):
    with pytest.raises(SystemExit):
        main("--owner me".split())


def test_too_many_arguments(basic_config_file):
    with pytest.raises(SystemExit):
        main("1 2 3 4".split())


def test_wrong_argument_type(basic_config_file):
    with pytest.raises(SystemExit):
        main("fail".split())


def test_from_config_file(basic_config_file, mock_job, basic_job_kwargs):
    assert main("".split()) == 6
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args", [tuple(),
                                  (0, ),
                                  (1, 2, ),
                                  (3, 4, 5)])
def test_what(basic_config_file, mock_job, args, basic_job_kwargs):
    assert main(list(map(str, args))) == 6
    mock_job.assert_called_once_with(*args,
                                     **basic_job_kwargs)


@pytest.mark.parametrize("args,machine",
                         [("-m", None),
                          ("-m foo", "foo")])
def test_machine_arg(basic_config_file, mock_job, args, machine,
                     basic_job_kwargs):
    assert main(args.split()) == 6
    basic_job_kwargs["machine"] = machine
    basic_job_kwargs["tags"] = None if machine else ["foo", "bar"]
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args,tags",
                         [("-m --tags", []),
                          ("-m --tags baz qux", ["baz", "qux"])])
def test_tags_arg(basic_config_file, mock_job, args, tags,
                  basic_job_kwargs):
    assert main(args.split()) == 6
    basic_job_kwargs["machine"] = None
    basic_job_kwargs["tags"] = tags
    mock_job.assert_called_once_with(**basic_job_kwargs)


def test_min_ratio_arg(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--min-ratio 0.5".split()) == 6
    basic_job_kwargs["min_ratio"] = 0.5
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args,max_dead_boards",
                         [("--max-dead-boards -1", None),
                          ("--max-dead-boards 123", 123)])
def test_max_dead_boards_arg(basic_config_file, mock_job, args,
                             max_dead_boards, basic_job_kwargs):
    assert main(args.split()) == 6
    basic_job_kwargs["max_dead_boards"] = max_dead_boards
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args,max_dead_links",
                         [("--max-dead-links -1", None),
                          ("--max-dead-links 123", 123)])
def test_max_dead_links_args(basic_config_file, mock_job, args,
                             max_dead_links, basic_job_kwargs):
    assert main(args.split()) == 6
    basic_job_kwargs["max_dead_links"] = max_dead_links
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args,require_torus",
                         [("--require-torus", True),
                          ("--no-require-torus", False)])
def test_require_torus_args(basic_config_file, mock_job, args,
                            require_torus, basic_job_kwargs):
    assert main(args.split()) == 6
    basic_job_kwargs["require_torus"] = require_torus
    mock_job.assert_called_once_with(**basic_job_kwargs)


def test_require_owner_args(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--owner theboss".split()) == 6
    basic_job_kwargs["owner"] = "theboss"
    mock_job.assert_called_once_with(**basic_job_kwargs)


def test_require_hostname_args(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--hostname altserve".split()) == 6
    basic_job_kwargs["hostname"] = "altserve"
    mock_job.assert_called_once_with(**basic_job_kwargs)


def test_require_port_args(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--port 1000".split()) == 6
    basic_job_kwargs["port"] = 1000
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args,keepalive",
                         [("--keepalive -1", None),
                          ("--keepalive 123", 123)])
def test_keepalive_args(basic_config_file, mock_job, args,
                        keepalive, basic_job_kwargs):
    assert main(args.split()) == 6
    basic_job_kwargs["keepalive"] = keepalive
    mock_job.assert_called_once_with(**basic_job_kwargs)


def test_reconnect_delay_args(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--reconnect-delay 0.5".split()) == 6
    basic_job_kwargs["reconnect_delay"] = 0.5
    mock_job.assert_called_once_with(**basic_job_kwargs)


def test_timeout_args(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--timeout 0.5".split()) == 6
    basic_job_kwargs["timeout"] = 0.5
    mock_job.assert_called_once_with(**basic_job_kwargs)


@pytest.mark.parametrize("args,boot", [("--boot", True), ("", False)])
def test_boot_args(basic_config_file, mock_working_job, mock_input,
                   args, boot, mock_mc):
    assert main(args.split()) == 0

    if boot:
        mock_mc.assert_called_once_with("foobar")
        mock_mc().boot.assert_called_once_with(8, 8)
    else:
        assert len(mock_mc.mock_calls) == 0


def test_no_boot_arg_when_no_rig(basic_config_file, mock_job, no_rig):
    with pytest.raises(SystemExit):
        main("--boot".split())


@pytest.mark.parametrize("args,boot", [("--boot", True), ("", False)])
def test_default_info(capsys, basic_config_file, mock_working_job, mock_input,
                      args, boot, mock_mc, no_colour):
    assert main(args.split()) == 0

    out, err = capsys.readouterr()

    # Should have printed the connection info
    assert "foobar" in out

    # Should have printed no debug output
    expected = ("Job 123: Waiting in queue...\n"
                "Job 123: Waiting for power on...\n")
    if boot:
        expected += "Job 123: Booting...\n"
    expected += "Job 123: Ready!\n"

    assert err == expected


def test_quiet_args(capsys, basic_config_file, mock_working_job, mock_input):
    assert main("--quiet".split()) == 0

    out, err = capsys.readouterr()

    # Should have printed the connection info
    assert "foobar" in out

    # Should have printed no debug output
    assert err == ""


@pytest.mark.parametrize("args,enable", [("--debug", True), ("", False)])
def test_debug_args(basic_config_file, mock_job, monkeypatch, args, enable):
    import spalloc.scripts.alloc
    logging = Mock()
    monkeypatch.setattr(spalloc.scripts.alloc, "logging", logging)

    assert main(args.split()) == 6

    if enable:
        assert len(logging.mock_calls) == 1
    else:
        assert len(logging.mock_calls) == 0


def test_command_args(basic_config_file, mock_working_job, mock_popen):
    assert main("--command foo {} bar{w}x{h}".split()) == 123
    mock_popen.assert_called_once_with("foo foobar bar8x8", shell=True)


@pytest.mark.parametrize("state,reason,retcode",
                         [(JobState.destroyed, None, 1),
                          (JobState.destroyed, "Dunno.", 1),
                          (JobState.unknown, None, 2),
                          (-1, None, 3)])
def test_failiure_modes(basic_config_file, mock_working_job,
                        state, reason, retcode):
    mock_working_job.state = state
    mock_working_job.reason = reason
    mock_working_job.wait_for_state_change.side_effect = JobDestroyedError()
    assert main("".split()) == retcode


def test_get_reason_fails(basic_config_file, mock_working_job):
    mock_working_job.state = JobState.destroyed
    type(mock_working_job).reason = PropertyMock(side_effect=IOError())
    assert main("".split()) == 1


def test_keyboard_interrupt(basic_config_file, mock_working_job):
    mock_working_job.state = JobState.queued
    mock_working_job.wait_for_state_change.side_effect = KeyboardInterrupt()
    assert main("".split()) == 4
    mock_working_job.destroy.assert_called_once_with("Keyboard interrupt.")


def test_no_destroy(basic_config_file, mock_working_job):
    assert main("--no-destroy -c true".split()) == 0
    assert len(mock_working_job.destroy.mock_calls) == 0
    mock_working_job.close.assert_called_once_with()


def test_resume(basic_config_file, mock_job, basic_job_kwargs):
    assert main("--resume 123 -c true".split()) == 6
    mock_job.assert_called_once_with(**{
        "resume_job_id": 123,
        "hostname": basic_job_kwargs["hostname"],
        "port": basic_job_kwargs["port"],
        "timeout": basic_job_kwargs["timeout"],
        "reconnect_delay": basic_job_kwargs["reconnect_delay"],
    })
