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

from setuptools import setup, find_packages

__version__ = None
exec(open("spalloc/_version.py").read())
assert __version__

setup(
    name="spalloc",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/SpiNNakerManchester/spalloc",
    description="A client for the spalloc_server SpiNNaker machine "
                "partitioning and allocation system.",
    license="GPLv2",
    classifiers=[
        "Development Status :: 5 - Production/Stable",

        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",

        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",

        "Natural Language :: English",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="spinnaker allocation packing management supercomputer",

    # Requirements
    install_requires=["appdirs",
                      'SpiNNUtilities == 1!6.0.1'],
    # Scripts
    entry_points={
        "console_scripts": [
            "spalloc = spalloc.scripts.alloc:main",
            "spalloc-ps = spalloc.scripts.ps:main",
            "spalloc-job = spalloc.scripts.job:main",
            "spalloc-machine = spalloc.scripts.machine:main",
            "spalloc-where-is = spalloc.scripts.where_is:main",
        ],
    },
    # Booting directly needs rig; not recommended! Use SpiNNMan instead, as
    # that has an up-to-date boot image pre-built
    # Note rig does not work with python 3.11 and there are NO plans to fix it
    extras_require={
        'boot': [
            'rig',
        ]},
    maintainer="SpiNNakerTeam",
    maintainer_email="spinnakerusers@googlegroups.com"
)
