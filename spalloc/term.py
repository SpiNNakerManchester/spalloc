"""Fancy terminal colour shenanigans."""

import os
import sys

from functools import partial
from collections import defaultdict

from six import iteritems

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

    def clear_screen(self):
        """Clear the screen and reset cursor to top-left corner."""
        return self("\033[2J\033[;H")

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


def render_table(table, column_sep="  "):
    """Render an ASCII table.

    Parameters
    ----------
    table : [row, ...]
        A table to render. Each row contains an iterable of column values which
        may be either values or a tuples (f, value) where value is the string
        to print, or an integer to print right-aligned, and f is a formatting
        function which is applied to the string before the table is finally
        displayed.
    column_sep : str
        String inserted between each column.

    Returns
    -------
    str
        The formatted table.
    """
    # Determine maximum column widths
    column_widths = defaultdict(lambda: 0)
    for row in table:
        for i, column in enumerate(row):
            if isinstance(column, str):
                string = column
            elif isinstance(column, int):
                string = str(column)
            else:
                _, string = column
            column_widths[i] = max(len(str(string)), column_widths[i])

    # Render the table cells with padding [[str, ...], ...]
    out = []
    for row in table:
        rendered_row = []
        out.append(rendered_row)
        for i, column in enumerate(row):
            # Get string length and formatted string
            if isinstance(column, str):
                string = column
                length = len(string)
                right_align = False
            elif isinstance(column, int):
                string = str(column)
                length = len(string)
                right_align = True
            elif isinstance(column[1], str):
                f, string = column
                length = len(string)
                right_align = False
                string = f(string)
            elif isinstance(column[1], int):
                f, string = column
                length = len(str(string))
                right_align = True
                string = f(string)

            padding = " " * (column_widths[i] - length)
            if right_align:
                rendered_row.append(padding + string)
            else:
                rendered_row.append(string + padding)

    # Render the final table
    return "\n".join(column_sep.join(row).rstrip() for row in out)


def render_definitions(definitions, seperator=": "):
    """Render a definition list.

    Such a list looks like this::

              Key: Value
        Something: Else
          Another: Thing

    Parameters
    ----------
    definitions : :py:class:`collections.OrderedDict`
        The key/value set to display.
    seperator : str
        The seperator inserted between keys and values.
    """
    # Special case since max would fail
    if not definitions:
        return ""

    col_width = max(map(len, definitions))
    return "\n".join("{:>{}s}{}{}".format(key, col_width, seperator, value)
                     for key, value in iteritems(definitions))
