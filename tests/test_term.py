import pytest

from spalloc.term import Terminal, render_table


@pytest.mark.parametrize("force", [True, False])
def test_force(force):
    t = Terminal(force=force)
    assert t.enabled is force


def test_call():
    t = Terminal()
    t.enabled = False
    assert t("foo") == ""
    t.enabled = True
    assert t("foo") == "foo"


def test_clear_screen():
    t = Terminal(force=True)
    assert t.clear_screen() == "\033[2J\033[;H"
    t.enabled = False
    assert t.clear_screen() == ""


def test_update():
    t = Terminal(force=True)

    # First time just save the cursor
    assert t.update() == "\0337"

    # Subsequent times restore the cursor and clear the line
    assert t.update() == "\0338\033[K"
    assert t.update() == "\0338\033[K"
    assert t.update() == "\0338\033[K"

    # Start again
    assert t.update(start_again=True) == "\0337"
    assert t.update() == "\0338\033[K"
    assert t.update() == "\0338\033[K"

    # Wrap a string
    assert t.update("foo", start_again=True) == "\0337foo"
    assert t.update("bar") == "\0338\033[Kbar"

    # Cast to string
    assert t.update(123) == "\0338\033[K123"

    # Disable
    t.enabled = False
    assert t.update(start_again=True) == ""
    assert t.update() == ""
    assert t.update() == ""

    assert t.update("foo", start_again=True) == "foo"
    assert t.update("bar") == "bar"
    assert t.update(123) == "123"


def test_set_attr():
    t = Terminal(force=True)

    # Empty list
    assert t.set_attrs() == ""

    # Single item
    assert t.set_attrs([1]) == "\033[1m"

    # Many items
    assert t.set_attrs([1, 2, 3]) == "\033[1;2;3m"

    # When disabled should do nothing
    t.enabled = False
    assert t.set_attrs() == ""
    assert t.set_attrs([1]) == ""
    assert t.set_attrs([1, 2, 3]) == ""


def test_wrap():
    t = Terminal()

    # Default do nothing
    assert t.wrap("foo") == "foo"

    # Cast to string
    assert t.wrap(123) == "123"

    # Pre and post
    assert t.wrap(123, pre="<") == "<123"
    assert t.wrap(123, post=">") == "123>"
    assert t.wrap(123, pre="<", post=">") == "<123>"

    # Without string should just get pre
    assert t.wrap(pre="<") == "<"
    assert t.wrap(post=">") == ""
    assert t.wrap(pre="<", post=">") == "<"


def test_getattr():
    t = Terminal(force=True)

    # Single things should work
    assert t.reset() == "\033[0m"
    assert t.red() == "\033[31m"
    assert t.bg_red() == "\033[41m"

    # Multiple things should too
    assert t.red_bg_blue_bright() == "\033[31;44;1m"

    # Should wrap strings
    assert t.green("I'm a tree") == "\033[32mI'm a tree\033[0m"

    # When disabled should do nothing but passthrough
    t.enabled = False
    assert t.red_bg_blue_bright() == ""
    assert t.red_bg_blue_bright("foo") == "foo"

    # Should fail when unrecognised things appear
    with pytest.raises(AttributeError):
        t.bad
    with pytest.raises(AttributeError):
        t.red_bad
    with pytest.raises(AttributeError):
        t.bad_red


def test_render_table():
    t = Terminal(force=True)

    # Empty
    assert render_table([]) == ""

    # Singleton
    assert render_table([["a"]]) == "a"

    # Single row
    assert render_table([["a", "bc", "def"]]) == "a  bc  def"

    # Column padding
    assert render_table([
        ("a", "bc", "def"),
        ("def", "bc", "a"),
    ]) == ("a    bc  def\n"
           "def  bc  a")

    # Column padding and formatting
    assert render_table([
        ("a", "bc", "def"),
        ((t.red, "def"), "bc", "a"),
    ]) == ("a    bc  def\n"
           "\033[31mdef\033[0m  bc  a")

    # Casting from ints and right-aligning them
    assert render_table([
        ("a", "bc", "integers"),
        ("def", "bc", 1234),
    ]) == ("a    bc  integers\n"
           "def  bc      1234")

    # Formatted ints
    assert render_table([
        ("a", "bc", "integers"),
        ("def", "bc", (t.red, 1234)),
    ]) == ("a    bc  integers\n"
           "def  bc      \033[31m1234\033[0m")
