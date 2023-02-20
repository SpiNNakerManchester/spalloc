# Copyright (c) 2016 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

        "License :: OSI Approved :: Apache License 2.0",

        "Natural Language :: English",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="spinnaker allocation packing management supercomputer",

    # Requirements
    install_requires=['SpiNNUtilities == 1!6.0.1'],
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
