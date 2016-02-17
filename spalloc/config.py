"""Simple accessors for the local spalloc configuration."""

import os
import os.path
import appdirs

from six.moves.configparser import ConfigParser


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
    
    # Set default config values
    parser.read_dict({
        "spalloc": {
            "port": 22244,
            
            "keepalive": "60.0",
            "reconnect_delay": "5.0",
            "timeout": "5.0",
            
            "machine": "None",
            "tags": "None",
            "max_dead_boards": "0",
            "max_dead_links": "None",
            "require_torus": "False",
        }
    })
    
    # Attempt to read from each possible file location in turn
    for filename in filenames:
        try:
            with open(filename, "r") as f:
                parser.read_file(f, filename)
        except FileNotFoundError:
            # File did not exist, keep trying
            pass
    
    spalloc = parser["spalloc"]
    
    cfg = {}
    
    cfg["hostname"] = spalloc.get("hostname", fallback=None)
    
    cfg["port"] = spalloc.getint("port")
    
    cfg["owner"] = spalloc.get("owner", fallback=None)
    
    if spalloc.get("keepalive", fallback="None") == "None":
        cfg["keepalive"] = None
    else:
        cfg["keepalive"] = spalloc.getfloat("keepalive")
    
    cfg["reconnect_delay"] = spalloc.getfloat("reconnect_delay", fallback=None)
    
    if spalloc.get("timeout", fallback="None") == "None":
        cfg["timeout"] = None
    else:
        cfg["timeout"] = spalloc.getfloat("timeout")
    
    if spalloc.get("machine", fallback="None") == "None":
        cfg["machine"] = None
    else:
        cfg["machine"] = spalloc.get("machine")
    
    if spalloc.get("tags", fallback="None") == "None":
        cfg["tags"] = None
    else:
        cfg["tags"] = list(map(str.strip, spalloc.get("tags").split(",")))
    
    if spalloc.get("max_dead_boards", fallback="None") == "None":
        cfg["max_dead_boards"] = None
    else:
        cfg["max_dead_boards"] = spalloc.getint("max_dead_boards")
    
    if spalloc.get("max_dead_links", fallback="None") == "None":
        cfg["max_dead_links"] = None
    else:
        cfg["max_dead_links"] = spalloc.getint("max_dead_links")
    
    cfg["require_torus"] = spalloc.getboolean("require_torus", fallback=False)
    
    return cfg
