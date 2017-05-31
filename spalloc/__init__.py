from spalloc.version import __version__  # noqa

# Alias useful objects
from spalloc.protocol_client import ProtocolClient  # noqa
from spalloc.protocol_client import ProtocolTimeoutError  # noqa
from spalloc.job import Job, JobDestroyedError, StateChangeTimeoutError  # noqa
from spalloc.states import JobState  # noqa
