import curses

import pytest

from path_sift import cli
from path_sift.picker import Picker
from path_sift.tui import ACCEPT, CANCEL, fit, handle_key

ITEMS = [f"dir/file{i}.txt" for i in range(20)]


def press(picker, *keys, page=5):
    action = None
    for key in keys:
        action = handle_key(picker, key, page)
    return action


def test_typing_and_editing_keys():
    p = Picker(ITEMS)
    assert press(p, "f", "1", "x", "\x7f") is None
    assert p.query == "f1"
    press(p, curses.KEY_BACKSPACE)
    assert p.query == "f"
    press(p, " ", "t", "\x17")
    assert p.query == "f "
    press(p, "\x15")
    assert p.query == ""


def test_non_printable_keys_are_ignored():
    p = Picker(ITEMS)
    press(p, "\t", curses.KEY_F1, curses.KEY_LEFT)
    assert p.query == ""


def test_navigation_keys():
    p = Picker(ITEMS)
    press(p, curses.KEY_DOWN, "\x0e")
    assert p.cursor == 2
    press(p, curses.KEY_UP)
    assert p.cursor == 1
    press(p, curses.KEY_NPAGE)
    assert p.cursor == 6
    press(p, "\x10", curses.KEY_PPAGE)
    assert p.cursor == 0


@pytest.mark.parametrize("key", ["\n", "\r", curses.KEY_ENTER])
def test_accept(key):
    assert press(Picker(ITEMS), key) == ACCEPT


@pytest.mark.parametrize("key", ["\x1b", "\x03", "\x07"])
def test_cancel(key):
    assert press(Picker(ITEMS), key) == CANCEL


@pytest.mark.parametrize(
    "path, width, expected",
    [
        ("short.txt", 20, "short.txt"),
        ("a/very/long/path/name.txt", 12, "…th/name.txt"),
        ("abc", 1, "…"),
        ("abc", 0, ""),
    ],
)
def test_fit(path, width, expected):
    assert fit(path, width) == expected
    assert len(fit(path, width)) <= max(width, 0)


@pytest.fixture
def small_tree(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "todo.md").write_text("x")
    monkeypatch.chdir(tmp_path)


def test_interactive_prints_choice(small_tree, monkeypatch, capsys):
    seen = {}

    def fake_pick(items, query):
        seen["items"], seen["query"] = sorted(items), query
        return "todo.md"

    monkeypatch.setattr(cli, "pick", fake_pick)
    assert cli.main(["-i", "to"]) == 0
    assert capsys.readouterr().out == "todo.md\n"
    assert seen == {"items": ["notes.txt", "todo.md"], "query": "to"}


def test_interactive_cancel_exits_1(small_tree, monkeypatch, capsys):
    monkeypatch.setattr(cli, "pick", lambda items, query: None)
    assert cli.main(["-i"]) == 1
    assert capsys.readouterr().out == ""


def test_interactive_without_terminal(small_tree, monkeypatch, capsys):
    def no_tty(items, query):
        raise cli.TerminalError("the picker needs a terminal (/dev/tty)")

    monkeypatch.setattr(cli, "pick", no_tty)
    assert cli.main(["-i"]) == 2
    assert "needs a terminal" in capsys.readouterr().err


def test_interactive_with_nothing_to_pick(small_tree, capsys):
    assert cli.main(["-i", "-t", "d"]) == 1
    assert "nothing to pick from" in capsys.readouterr().err


def test_interactive_rejects_limit(small_tree):
    with pytest.raises(SystemExit) as exc:
        cli.main(["-i", "-n", "3"])
    assert exc.value.code == 2
