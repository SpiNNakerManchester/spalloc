from setuptools import setup, find_packages

with open("spalloc/version.py", "r") as f:
    exec(f.read())

setup(
    name="spalloc",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/project-rig/spalloc",
    author="Jonathan Heathcote",
    description="A client for the spalloc_server SpiNNaker machine partitioning and allocation system.",
    license="GPLv2",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",

        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="spinnaker allocation packing management supercomputer",

    # Requirements
    install_requires=["six>=1.8.0", "appdirs", "enum-compat"],

    # Scripts
    entry_points={
        "console_scripts": [
            "spalloc = spalloc.scripts.alloc:main",
            "spalloc-ps = spalloc.scripts.ps:main",
            "spalloc-job = spalloc.scripts.job:main",
            "spalloc-machine = spalloc.scripts.machine:main",
            "spalloc-where-is = spalloc.scripts.where_is:main",
        ],
    }
)
