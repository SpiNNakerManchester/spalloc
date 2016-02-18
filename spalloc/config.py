"""Simple accessors for the local spalloc configuration."""

import os
import os.path
import appdirs

from six import iteritems
from six.moves.configparser import ConfigParser, NoOptionError


# The application name to use in config file names
_name = "spalloc"

# Standard config file names/locations
SYSTEM_CONFIG_FILE = appdirs.site_config_dir(_name)
USER_CONFIG_FILE = appdirs.user_config_dir(_name)
CWD_CONFIG_FILE = os.path.join(os.curdir, ".{}".format(_name))

# Search path for config files (lowest to highest priority)
SEARCH_PATH = [
    SYSTEM_CONFIG_FILE,
    USER_CONFIG_FILE,
    CWD_CONFIG_FILE,
]


def read_config(filenames=SEARCH_PATH):
    """Attempt to read local configuration files to determine spalloc client
    settings.
    
    Parameters
    ----------
    filenames : [str, ...]
        Filenames to attempt to read. Later config file have higher priority.
    
    Returns
    -------
    dict
        The configuration loaded.
    """
    parser = ConfigParser()
    
    # Set default config values (NB: No read_dict in Python 2.7)
    parser.add_section("spalloc")
    for key, value in iteritems({"port": "22244",
                                 "keepalive": "60.0",
                                 "reconnect_delay": "5.0",
                                 "timeout": "5.0",
                                 "machine": "None",
                                 "tags": "None",
                                 "min_ratio": "0.333",
                                 "max_dead_boards": "0",
                                 "max_dead_links": "None",
                                 "require_torus": "False"}):
        parser.set("spalloc", key, value)
    
    # Attempt to read from each possible file location in turn
    for filename in filenames:
        try:
            with open(filename, "r") as f:
                parser.readfp(f, filename)
        except (IOError, OSError):
            # File did not exist, keep trying
            pass
    
    cfg = {}
    
    try:
        cfg["hostname"] = parser.get("spalloc", "hostname")
    except NoOptionError:
        cfg["hostname"] = None
    
    cfg["port"] = parser.getint("spalloc", "port")
    
    try:
        cfg["owner"] = parser.get("spalloc", "owner")
    except NoOptionError:
        cfg["owner"] = None
    
    if parser.get("spalloc", "keepalive") == "None":
        cfg["keepalive"] = None
    else:
        cfg["keepalive"] = parser.getfloat("spalloc", "keepalive")
    
    cfg["reconnect_delay"] = parser.getfloat("spalloc", "reconnect_delay")
    
    if parser.get("spalloc", "timeout") == "None":
        cfg["timeout"] = None
    else:
        cfg["timeout"] = parser.getfloat("spalloc", "timeout")
    
    if parser.get("spalloc", "machine") == "None":
        cfg["machine"] = None
    else:
        cfg["machine"] = parser.get("spalloc", "machine")
    
    if parser.get("spalloc", "tags") == "None":
        cfg["tags"] = None
    else:
        cfg["tags"] = list(map(str.strip, parser.get("spalloc", "tags").split(",")))
    
    cfg["min_ratio"] = parser.getfloat("spalloc", "min_ratio")
    
    if parser.get("spalloc", "max_dead_boards") == "None":
        cfg["max_dead_boards"] = None
    else:
        cfg["max_dead_boards"] = parser.getint("spalloc", "max_dead_boards")
    
    if parser.get("spalloc", "max_dead_links") == "None":
        cfg["max_dead_links"] = None
    else:
        cfg["max_dead_links"] = parser.getint("spalloc", "max_dead_links")
    
    cfg["require_torus"] = parser.getboolean("spalloc", "require_torus")
    
    return cfg
