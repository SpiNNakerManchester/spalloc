from spalloc.version import __version__

# Alias useful objects
from spalloc.protocol_client import ProtocolClient
from spalloc.job import Job, JobDestroyedError
from spalloc.states import JobState
