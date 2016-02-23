Spalloc: SpiNNaker machine allocation client
============================================

.. image:: https://img.shields.io/pypi/v/spalloc.svg?style=flat
   :alt: PyPi version
   :target: https://pypi.python.org/pypi/spalloc/
.. image:: https://readthedocs.org/projects/spalloc/badge/?version=stable
   :alt: Documentation
   :target: http://spalloc.readthedocs.org/
.. image:: https://travis-ci.org/project-rig/spalloc.svg?branch=master
   :alt: Build Status
   :target: https://travis-ci.org/project-rig/spalloc
.. image:: https://coveralls.io/repos/project-rig/spalloc/badge.svg?branch=master
   :alt: Coverage Status
   :target: https://coveralls.io/r/project-rig/spalloc?branch=master

Spalloc is a Python library and set of command-line programs for requesting
SpiNNaker_ machines from a spalloc `server`_.

.. _SpiNNaker: http://apt.cs.manchester.ac.uk/projects/SpiNNaker/
.. _server: https://github.com/project-rig/spalloc_server

To get started, see the quick-start below or refer to the documentation_.

.. _documentation: http://spalloc.readthedocs.org/


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

.. image:: docs/source/_static/spalloc.gif
    :alt: Animated GIF showing the typical execution of a spalloc call.

...or request one from Python...

::

    >>> from spalloc import Job
    >>> with Job(3) as j:
    ...     my_boot(j.hostname, j.width, j.height)
    ...     my_application(j.hostname)
