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
import time


def time_left(timestamp):
    """ Convert a timestamp into how long to wait for it.
    """
    if timestamp is None:
        return None
    return max(0.0, timestamp - time.time())


def timed_out(timestamp):
    """ Check if a timestamp has been reached.
    """
    if timestamp is None:
        return False
    return timestamp < time.time()


def make_timeout(delay_seconds):
    """ Convert a delay (in seconds) into a timestamp.
    """
    if delay_seconds is None:
        return None
    return time.time() + delay_seconds


def render_timestamp(timestamp):
    """ Convert a timestamp (Unix seconds) into a local human-readable\
        timestamp string.
    """
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")
