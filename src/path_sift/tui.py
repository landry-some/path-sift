"""Curses front end for the interactive picker."""

import curses
import os
import sys
from contextlib import contextmanager

from .picker import Picker

ACCEPT = "accept"
CANCEL = "cancel"

_ENTER = {"\n", "\r", curses.KEY_ENTER}
_CANCEL = {"\x1b", "\x03", "\x07"}  # Esc, Ctrl-C, Ctrl-G
_BACKSPACE = {"\x7f", "\x08", curses.KEY_BACKSPACE}
_UP = {"\x10", curses.KEY_UP}  # Ctrl-P
_DOWN = {"\x0e", curses.KEY_DOWN}  # Ctrl-N


class TerminalError(Exception):
    """The picker can't run because there is no usable terminal."""


def handle_key(picker: Picker, key: str | int, page: int) -> str | None:
    """Apply one key to the picker. Returns ACCEPT, CANCEL or None (keep going).

    ``key`` is what curses ``get_wch`` returns: a str for characters, an int
    for special keys. ``page`` is how many rows PageUp/PageDown move.
    """
    if key in _ENTER:
        return ACCEPT
    if key in _CANCEL:
        return CANCEL
    if key in _BACKSPACE:
        picker.backspace()
    elif key == "\t":
        picker.toggle_mark()
    elif key == "\x17":  # Ctrl-W
        picker.delete_word()
    elif key == "\x15":  # Ctrl-U
        picker.clear()
    elif key in _UP:
        picker.move(-1)
    elif key in _DOWN:
        picker.move(1)
    elif key == curses.KEY_PPAGE:
        picker.move(-page)
    elif key == curses.KEY_NPAGE:
        picker.move(page)
    elif isinstance(key, str) and key.isprintable():
        picker.insert(key)
    return None


def fit(path: str, width: int) -> str:
    """Shorten ``path`` to ``width`` columns by cutting from the left, so the
    file name stays visible."""
    if width <= 0:
        return ""
    if len(path) <= width:
        return path
    if width == 1:
        return "…"
    return "…" + path[len(path) - width + 1 :]


def _draw(screen, picker: Picker) -> None:
    height, width = screen.getmaxyx()
    screen.erase()
    rows = picker.visible(height - 2)
    for y, (index, path, match) in enumerate(rows, start=2):
        shown = fit(path, width - 3)
        cut = len(path) - len(shown)
        selected = index == picker.cursor
        base = curses.A_REVERSE if selected else curses.A_NORMAL
        marker = (">" if selected else " ") + ("*" if path in picker.marked else " ")
        screen.addstr(y, 0, marker, base)
        bold = {i - cut for i in match.positions}
        for x, ch in enumerate(shown):
            attr = base | (curses.A_BOLD | curses.A_UNDERLINE if x in bold else 0)
            screen.addstr(y, 2 + x, ch, attr)
    count = f"  {len(picker.results)}/{len(picker.items)}"
    if picker.marked:
        count += f"  ({len(picker.marked)} marked)"
    screen.addnstr(1, 0, count, width - 1, curses.A_DIM)
    prompt = "> " + picker.query
    screen.addnstr(0, 0, prompt[-(width - 1) :], width - 1)
    screen.move(0, min(len(prompt), width - 1))
    screen.refresh()


def _loop(screen, picker: Picker) -> list[str] | None:
    curses.use_default_colors()
    # Raw mode so Ctrl-C arrives as a key and cancels the picker, instead of
    # a SIGINT that would also kill the calling shell script.
    curses.raw()
    while True:
        _draw(screen, picker)
        try:
            key = screen.get_wch()
        except KeyboardInterrupt:
            return None
        if key == curses.KEY_RESIZE:
            continue
        action = handle_key(picker, key, page=max(1, screen.getmaxyx()[0] - 2))
        if action == ACCEPT:
            return picker.chosen() or None
        if action == CANCEL:
            return None


@contextmanager
def _terminal_fds():
    """Point stdin and stdout at /dev/tty while the picker runs.

    curses draws on stdout and reads stdin, but in ``vim "$(path-sift -i)"``
    stdout is a pipe. The original descriptors are restored afterwards, so the
    chosen path still goes to the real stdout.
    """
    try:
        tty = os.open("/dev/tty", os.O_RDWR)
    except OSError as exc:
        raise TerminalError("the picker needs a terminal (/dev/tty)") from exc
    sys.stdout.flush()
    saved = os.dup(0), os.dup(1)
    try:
        os.dup2(tty, 0)
        os.dup2(tty, 1)
        yield
    finally:
        os.dup2(saved[0], 0)
        os.dup2(saved[1], 1)
        for fd in (*saved, tty):
            os.close(fd)


def pick(items: list[str], query: str = "") -> list[str] | None:
    """Show the picker and return the chosen paths, or None if cancelled.

    That is the marked paths if any were marked with Tab, otherwise just the
    highlighted one."""
    os.environ.setdefault("ESCDELAY", "25")  # make Esc respond quickly
    picker = Picker(items, query)
    with _terminal_fds():
        try:
            return curses.wrapper(_loop, picker)
        except curses.error as exc:
            raise TerminalError(f"could not start the picker: {exc}") from exc
