# Copyright (c) 2016-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
