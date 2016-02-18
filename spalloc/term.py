"""Fancy terminal colour shenanigans."""

import os
import sys

from functools import partial

from enum import IntEnum


class ANSIDisplayAttributes(IntEnum):
    reset = 0
    bright = 1
    dim = 2
    underscore = 4
    blink = 5
    reverse = 7
    hidden = 8

    # foreground colours
    black = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    magenta = 35
    cyan = 36
    white = 37

    # background colours
    bg_black = 40
    bg_red = 41
    bg_green = 42
    bg_yellow = 43
    bg_blue = 44
    bg_magenta = 45
    bg_cyan = 46
    bg_white = 47


class Terminal(object):
    """Fancy terminal colour shenanigans.

    Utilities for printing colourful output on ANSI terminals and simple cursor
    operations. When output is not directed to a tty, or when running under
    Windows, no ANSI control characters are produced.

    Example::

        t = Terminal()

        # Printing in colours
        print(t.red("I'm in red!"))

        # Updating a status line
        for num in range(100):
            print(t.update("Now at {}%".format(num)))
            time.sleep(0.05)

        # Combining style attributes
        print(t.bg_red_white_blink("Woah!"))

    This module was inspired by the 'blessings' module which I initially liked
    but proved to be just a little too buggy.

    Attributes
    ----------
    stream
        The IO stream which is being used.
    enabled : bool
        Is colour enabled?
    """

    def __init__(self, stream=None, force=None):
        """
        Parameters
        ----------
        stream
            The IO stream being written to (by default sys.stdout).
        force : None or bool
            If a bool, forces styling to be enabled or disabled as specified.
            If None, checks whether the stream is a TTY (and that we're not o
            non-posix OS) before enabling colouring automatically.
        """
        self.stream = stream if stream is not None else sys.stdout

        if force is None:
            self.enabled = os.name == "posix" and self.stream.isatty()
        else:
            self.enabled = force

        self._location_saved = False

    def __call__(self, string):
        """If enabled, passes through the given value, otherwise passes through
        an empty string.
        """
        if self.enabled:
            return string
        else:
            return ""

    def update(self, string="", start_again=False):
        """Print before a line and it will replace the previous line prefixed
        with :py:meth:`.update`.

        Parameters
        ----------
        string : str
            The string to print (optional).
        start_again : bool
            If False, overwrites the last thing printed. If True, starts a new
            line.
        """
        if start_again:
            self._location_saved = False

        if not self._location_saved:
            # No previous line to update, just save the cursor.
            self._location_saved = True
            return "".join((self("\0337"), str(string)))
        else:
            # Restore to previous location and clear line.
            return "".join((self("\0338\033[K"), str(string)))

    def set_attrs(self, attrs=tuple()):
        """Construct an ANSI control sequence which sets the given attribute
        numbers.
        """
        if attrs:
            return self("\033[{}m".format(";".join(str(attr)
                                                   for attr in attrs)))
        else:
            return ""

    def wrap(self, string=None, pre="", post=""):
        """Wrap a string in the suppled pre and post strings or just print the
        pre string if no string given.
        """
        if string is not None:
            return "".join((pre, str(string), post))
        else:
            return pre

    def __getattr__(self, name):
        """Implements all the 'magic' style methods."""
        attrs = []
        while name:
            for attr in ANSIDisplayAttributes:
                if name.startswith(attr.name):
                    attrs.append(int(attr))
                    name = name[len(attr.name):].lstrip("_")
                    break
            else:
                # No attr name matched! Fail!
                raise AttributeError(name)
        return partial(self.wrap,
                       pre=self.set_attrs(attrs),
                       post=self("\033[0m"))
