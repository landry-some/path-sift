import pytest

from path_sift.match import rank
from path_sift.picker import Picker

ITEMS = ["README.md", "src/cli.py", "src/match.py", "tests/test_cli.py", "docs/notes.txt"]


def paths(picker):
    return [p for p, _ in picker.results]


def test_starts_with_everything_in_order():
    p = Picker(ITEMS)
    assert paths(p) == ITEMS
    assert p.selected() == "README.md"


def test_initial_query():
    p = Picker(ITEMS, "cli")
    assert paths(p) == ["src/cli.py", "tests/test_cli.py"]


def test_typing_narrows_and_backspace_widens():
    p = Picker(ITEMS)
    p.insert("c")
    p.insert("l")
    assert paths(p) == [x for x, _ in rank("cl", ITEMS)]
    p.backspace()
    p.backspace()
    assert paths(p) == ITEMS
    p.backspace()  # nothing left to delete
    assert p.query == ""


def test_narrowing_matches_a_full_rank():
    p = Picker(ITEMS)
    for ch in "src p":
        p.insert(ch)
        assert paths(p) == [x for x, _ in rank(p.query, ITEMS)]


@pytest.mark.parametrize(
    "query, expected",
    [("src cli", "src "), ("src cli  ", "src "), ("cli", ""), ("", ""), ("a b c", "a b ")],
)
def test_delete_word(query, expected):
    p = Picker(ITEMS, query)
    p.delete_word()
    assert p.query == expected


def test_clear():
    p = Picker(ITEMS, "notes")
    p.clear()
    assert p.query == ""
    assert paths(p) == ITEMS


def test_move_is_clamped_and_reset_by_typing():
    p = Picker(ITEMS)
    p.move(-1)
    assert p.cursor == 0
    p.move(100)
    assert p.selected() == "docs/notes.txt"
    p.insert("s")
    assert p.cursor == 0


def test_no_results():
    p = Picker(ITEMS, "zzz")
    p.move(1)
    assert p.selected() is None
    assert p.visible(5) == []


def test_visible_scrolls_with_cursor():
    p = Picker([f"file{i}" for i in range(10)])
    assert [i for i, _, _ in p.visible(3)] == [0, 1, 2]
    p.move(4)
    assert [i for i, _, _ in p.visible(3)] == [2, 3, 4]
    p.move(-3)
    assert [i for i, _, _ in p.visible(3)] == [1, 2, 3]
    assert p.visible(0) == []
