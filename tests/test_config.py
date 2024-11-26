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

import tempfile
import shutil
import os.path
import pytest
from spalloc_client.spalloc_config import SpallocConfig, TIMEOUT


@pytest.yield_fixture
def tempdir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.fixture
def filename(tempdir):
    filename = os.path.join(tempdir, "f1")
    return filename


def test_priority(tempdir):
    f1 = os.path.join(tempdir, "f1")
    f2 = os.path.join(tempdir, "f2")

    with open(f1, "w") as f:
        f.write("[spalloc]\nport=123\nhostname=bar")
    with open(f2, "w") as f:
        f.write("[spalloc]\nport=321\ntags=qux")

    cfg = SpallocConfig([f1, f2])

    assert cfg.port == 321
    assert cfg.reconnect_delay == 5.0
    assert cfg.hostname == "bar"
    assert cfg.tags == ["qux"]
