import pytest

from path_sift.filters import Filters, parse_age, parse_size
from path_sift.walk import Entry

NOW = 1_000_000.0


def file(path, size=100, age=0.0):
    return Entry(path, False, size, NOW - age)


def folder(path, age=0.0):
    return Entry(path, True, 0, NOW - age)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("0", 0),
        ("200", 200),
        ("10k", 10 * 1024),
        ("10K", 10 * 1024),
        ("1.5M", int(1.5 * 1024**2)),
        ("2G", 2 * 1024**3),
        ("2GiB", 2 * 1024**3),
        ("3kb", 3 * 1024),
        ("512b", 512),
        (" 7 m ", 7 * 1024**2),
    ],
)
def test_parse_size(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("text", ["", "k", "-5", "10x", "1.2.3M"])
def test_parse_size_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_size(text)


@pytest.mark.parametrize(
    "text, expected",
    [("90s", 90), ("30m", 1800), ("2h", 7200), ("3d", 3 * 86400), ("1w", 604800), ("1.5h", 5400)],
)
def test_parse_age(text, expected):
    assert parse_age(text) == expected


@pytest.mark.parametrize("text", ["", "3", "d", "3y", "-2d"])
def test_parse_age_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_age(text)


def test_no_filters_accept_everything():
    assert Filters().accepts(file("a.txt"), NOW)
    assert Filters().accepts(folder("dir"), NOW)


def test_kind():
    assert Filters(kind="f").accepts(file("a"), NOW)
    assert not Filters(kind="f").accepts(folder("a"), NOW)
    assert Filters(kind="d").accepts(folder("a"), NOW)
    assert not Filters(kind="d").accepts(file("a"), NOW)


def test_extensions_are_case_insensitive_and_skip_dirs():
    f = Filters(exts=frozenset({"py", "md"}))
    assert f.accepts(file("src/cli.py"), NOW)
    assert f.accepts(file("README.MD"), NOW)
    assert not f.accepts(file("notes.txt"), NOW)
    assert not f.accepts(file("Makefile"), NOW)
    assert not f.accepts(folder("pkg.py"), NOW)


def test_size_limits_are_inclusive():
    f = Filters(min_size=100, max_size=200)
    assert f.accepts(file("a", size=100), NOW)
    assert f.accepts(file("a", size=200), NOW)
    assert not f.accepts(file("a", size=99), NOW)
    assert not f.accepts(file("a", size=201), NOW)


def test_size_limits_drop_directories():
    assert not Filters(min_size=0).accepts(folder("d"), NOW)


def test_newer_and_older():
    hour = 3600.0
    assert Filters(newer=2 * hour).accepts(file("a", age=hour), NOW)
    assert not Filters(newer=2 * hour).accepts(file("a", age=3 * hour), NOW)
    assert Filters(older=2 * hour).accepts(file("a", age=3 * hour), NOW)
    assert not Filters(older=2 * hour).accepts(file("a", age=hour), NOW)
    window = Filters(newer=3 * hour, older=hour)
    assert window.accepts(folder("d", age=2 * hour), NOW)
    assert not window.accepts(folder("d", age=4 * hour), NOW)
