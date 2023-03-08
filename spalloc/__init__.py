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

from spalloc._version import __version__  # noqa: F401

# Alias useful objects
from spalloc.protocol_client import ProtocolClient, ProtocolError
from spalloc.protocol_client import ProtocolTimeoutError
from spalloc.protocol_client import SpallocServerException
from spalloc.job import Job, JobDestroyedError, StateChangeTimeoutError
from spalloc.states import JobState

__all__ = [
    "Job", "JobDestroyedError", "JobState", "ProtocolClient",
    "ProtocolError", "ProtocolTimeoutError", "SpallocServerException",
    "StateChangeTimeoutError"]
