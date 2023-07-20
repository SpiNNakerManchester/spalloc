Spalloc: SpiNNaker machine allocation client
============================================

.. image:: https://img.shields.io/pypi/v/spalloc.svg?style=flat
   :alt: PyPi version
   :target: https://pypi.python.org/pypi/spalloc/
.. image:: https://readthedocs.org/projects/spalloc/badge/?version=stable
   :alt: Documentation
   :target: https://spalloc.readthedocs.org/
.. image:: https://github.com/SpiNNakerManchester/spalloc/workflows/Python%20Build/badge.svg?branch=master
   :alt: Build Status
   :target: https://github.com/SpiNNakerManchester/spalloc/actions?query=workflow%3A%22Python+Build%22+branch%3Amaster
.. image:: https://coveralls.io/repos/SpiNNakerManchester/spalloc/badge.svg?branch=master
   :alt: Coverage Status
   :target: https://coveralls.io/r/SpiNNakerManchester/spalloc?branch=master

Spalloc is a Python library and set of command-line programs for requesting
SpiNNaker_ machines from a spalloc `server`_.

.. _SpiNNaker: https://apt.cs.manchester.ac.uk/projects/SpiNNaker/
.. _server: https://github.com/SpiNNakerManchester/spalloc_server

To get started, see the quick-start below or refer to the documentation_.

.. _documentation: https://spalloc.readthedocs.org/


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

    >>> from spalloc_client import Job
    >>> with Job(3) as j:
    ...     my_boot(j.hostname, j.width, j.height)
    ...     my_application(j.hostname)


Pip Freeze
----------
This code was tested with all (SpiNNakerManchester)[https://github.com/SpiNNakerManchester] on tag 7.0.0

Pip Freeze showed the dependencies as:

appdirs==1.4.4

astroid==2.15.6

attrs==23.1.0

certifi==2023.5.7

charset-normalizer==3.2.0

contourpy==1.1.0

coverage==7.2.7

csa==0.1.12

cycler==0.11.0

dill==0.3.6

ebrains-drive==0.5.1

exceptiongroup==1.1.2

execnet==2.0.2

fonttools==4.41.0

graphviz==0.20.1

httpretty==1.1.4

idna==3.4

importlib-resources==6.0.0

iniconfig==2.0.0

isort==5.12.0

jsonschema==4.18.4

jsonschema-specifications==2023.7.1

kiwisolver==1.4.4

lazy-object-proxy==1.9.0

lazyarray==0.5.2

matplotlib==3.7.2

mccabe==0.7.0

mock==5.1.0

multiprocess==0.70.14

neo==0.12.0

numpy==1.24.4

opencv-python==4.8.0.74

packaging==23.1

pathos==0.3.0

Pillow==10.0.0

pkgutil_resolve_name==1.3.10

platformdirs==3.9.1

pluggy==1.2.0

pox==0.3.2

ppft==1.7.6.6

py==1.11.0

pylint==2.17.4

PyNN==0.11.0

pyparsing==2.4.7

pytest==7.4.0

pytest-cov==4.1.0

pytest-forked==1.6.0

pytest-instafail==0.5.0

pytest-progress==1.2.5

pytest-timeout==2.1.0

pytest-xdist==3.3.1

python-coveralls==2.9.3

python-dateutil==2.8.2

PyYAML==6.0.1

quantities==0.14.1

referencing==0.30.0

requests==2.31.0

rpds-py==0.9.2

scipy==1.10.1

six==1.16.0

tomli==2.0.1

tomlkit==0.11.8

typing_extensions==4.7.1

urllib3==2.0.4

websocket-client==1.6.1

wrapt==1.15.0

zipp==3.16.2

