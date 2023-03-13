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
from spalloc.scripts.where_is import main
from spalloc.scripts.support import VERSION_RANGE_START, VERSION_RANGE_STOP
from spalloc.protocol_client import ProtocolError


@pytest.fixture
def client(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    client.version.return_value = ".".join(map(str, VERSION_RANGE_START))
    client.__exit__.return_value = False
    client.where_is.return_value = {
        "machine": "m",
        "logical": [3, 2, 1],
        "physical": [6, 5, 4],
        "chip": [8, 7],
        "board_chip": [10, 9],
        "job_id": 11,
        "job_chip": [13, 12],
    }
    monkeypatch.setattr(main, "client_factory", Mock(return_value=client))
    return client


def test_no_hostname(no_config_files):
    with pytest.raises(SystemExit):
        main("-b m 1 2 3".split())


@pytest.mark.parametrize("version", [VERSION_RANGE_STOP, (0, 0, 0)])
def test_bad_version(basic_config_file, client, version):
    client.version.return_value = ".".join(map(str, version))
    with pytest.raises(SystemExit) as exn:
        main("-b m 1 2 3".split())
    assert exn.value.code == 2


@pytest.mark.parametrize("args",
                         ["--board name x y z",
                          "--physical name x y z",
                          "--chip name x y",
                          "--job_chip job x y"])
def test_bad_args(basic_config_file, client, args):
    with pytest.raises(SystemExit):
        main(args.split())


def test_server_error(basic_config_file, client):
    client.where_is.side_effect = ProtocolError()
    assert main("--board name 3 2 1".split()) == 1


def test_board(basic_config_file, client):
    assert main("--board name 3 2 1".split()) == 0
    client.where_is.assert_called_once_with(
        machine="name", x=3, y=2, z=1)


def test_physical(basic_config_file, client):
    assert main("--physical name 3 2 1".split()) == 0
    client.where_is.assert_called_once_with(
        machine="name", cabinet=3, frame=2, board=1)


def test_chip(basic_config_file, client):
    assert main("--chip name 7 8".split()) == 0
    client.where_is.assert_called_once_with(
        machine="name", chip_x=7, chip_y=8)


def test_job_chip(basic_config_file, client):
    assert main("--job-chip 123 7 8".split()) == 0
    client.where_is.assert_called_once_with(
        job_id=123, chip_x=7, chip_y=8)


def test_formatting_full(basic_config_file, client, capsys):
    assert main("--job-chip 123 7 8".split()) == 0
    out, _ = capsys.readouterr()
    assert out == ("                 Machine: m\n"
                   "       Physical location: Cabinet 6, Frame 5, Board 4\n"
                   "        Board coordinate: (3, 2, 1)\n"
                   "Machine chip coordinates: (8, 7)\n"
                   "Coordinates within board: (10, 9)\n"
                   "         Job using board: 11\n"
                   "  Coordinates within job: (13, 12)\n")


def test_formatting_no_board_chip(basic_config_file, client, capsys):
    assert main("--board m 3 2 1".split()) == 0
    out, _ = capsys.readouterr()
    assert out == ("                 Machine: m\n"
                   "       Physical location: Cabinet 6, Frame 5, Board 4\n"
                   "        Board coordinate: (3, 2, 1)\n"
                   "Machine chip coordinates: (8, 7)\n"
                   "         Job using board: 11\n"
                   "  Coordinates within job: (13, 12)\n")


def test_formatting_no_job(basic_config_file, client, capsys):
    client.where_is.return_value["job_id"] = None
    client.where_is.return_value["job_chip"] = None
    assert main("--board m 3 2 1".split()) == 0
    out, _ = capsys.readouterr()
    assert out == ("                 Machine: m\n"
                   "       Physical location: Cabinet 6, Frame 5, Board 4\n"
                   "        Board coordinate: (3, 2, 1)\n"
                   "Machine chip coordinates: (8, 7)\n"
                   "         Job using board: None\n")


def test_no_boards(basic_config_file, client, capsys):
    client.where_is.return_value = None
    with pytest.raises(SystemExit) as exn:
        main("--board m 3 2 1".split())
    assert exn.value.code == 4
