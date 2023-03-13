Spalloc: SpiNNaker machine allocation client
============================================

Spalloc is a Python library and set of command-line programs for requesting
SpiNNaker_ machines from a spalloc `server`_.

.. _SpiNNaker: https://apt.cs.manchester.ac.uk/projects/SpiNNaker/
.. _server: https://github.com/SpiNNakerManchester/spalloc_server


Quick-start
-----------

**Step 1: Install spalloc**::

    $ pip install spalloc

**Step 2: Write a configuration file** indicating your email address and the spalloc
server's address (run ``python -m spalloc.config`` to discover what to call
your config file on your machine)::

    [spalloc]
    hostname = my_server
    owner = jdh@cs.man.ac.uk

**Step 3: Request a system** using the command-line interface, e.g. a
three-board machine::

    $ spalloc 3

.. image:: _static/spalloc.gif
    :alt: Animated GIF showing the typical execution of a spalloc call.

...or request one from :py:class:`Python <spalloc.Job>`...

::

    >>> from spalloc import Job
    >>> with Job(3) as j:
    ...     my_boot(j.hostname, j.width, j.height)
    ...     my_application(j.hostname)

.. note::

    When a machine is allocated it is powered on but not booted: that is up to
    you. If Rig_ is installed on your system the ``spalloc`` commandline tool
    provides a ``--boot`` option which will boot the allocated machine for you.

.. note::

    The dimensions of a machine may not be what you're used to and may change
    from allocation to allocation, even for the same number of boards.

.. note::

    When you're finished with the boards you were allocated, pressing enter (or
    exiting the ``with`` block in the Python version) will automatically shut
    them down and allow them to be used by others.

.. _Rig: https://github.com/SpiNNakerManchester/rig

Configuration file format and defaults
--------------------------------------

.. automodule:: spalloc.config


``spalloc``: Allocate SpiNNaker machines
----------------------------------------
.. automodule:: spalloc.scripts.alloc

``spalloc-job``: Manage and reset existing jobs and their boards
----------------------------------------------------------------
.. automodule:: spalloc.scripts.job

``spalloc-ps``: List all running jobs
-------------------------------------
.. automodule:: spalloc.scripts.ps

``spalloc-machine``: List available machines and their running jobs
-------------------------------------------------------------------
.. automodule:: spalloc.scripts.machine

``spalloc-where-is``: Query the server for the physical/logical locations of boards/chips
-----------------------------------------------------------------------------------------
.. automodule:: spalloc.scripts.where_is


Python library
--------------

Spalloc provides a pair of Python libraries which enable basic high- and
low-level interaction with a spalloc server. The high-level
:py:class:`~spalloc.Job` interface makes the task of creating jobs (and keeping
them alive) straight-forward but only facilitates basic job management
functions such as resetting boards and getting their IP addresses.  The
low-level :py:class:`~spalloc.ProtocolClient` provides an RPC-like interface to
the spalloc server enabling any spalloc server command to be sent.

.. note::

    These libraries are intentionally simplistic and may be unsuitable for very
    advanced applications. In such instances, users are encouraged to implement
    the spalloc server protocol_ in a manner better suited to their specific
    use-case.

.. _protocol: https://spalloc-server.readthedocs.org/en/stable/protocol.html

High level interface (:py:class:`spalloc.Job`)
``````````````````````````````````````````````

.. autoclass:: spalloc.Job
    :members:
    :special-members:

.. autoclass:: spalloc.JobState
    :members:

.. autoexception:: spalloc.JobDestroyedError

.. autoexception:: spalloc.StateChangeTimeoutError

Lower level interface (:py:class:`spalloc.ProtocolClient`)
``````````````````````````````````````````````````````````

.. autoclass:: spalloc.ProtocolClient
    :members:
    :special-members:

.. autoexception:: spalloc.ProtocolTimeoutError


Indicies and Tables
-------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

