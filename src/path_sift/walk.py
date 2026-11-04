"""Walk directory trees and collect the entries path-sift can match against."""

import os
from dataclasses import dataclass
from typing import Iterator

# Directory names skipped by default: version control and tool caches that are
# almost never what you are looking for and can hold huge numbers of files.
DEFAULT_SKIP = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
    }
)


@dataclass(frozen=True)
class Entry:
    path: str
    is_dir: bool
    size: int
    mtime: float


def _join(root: str, name: str) -> str:
    if root == ".":
        return name
    return os.path.join(root, name)


def _dir_id(path: str) -> tuple[int, int] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_dev, st.st_ino


def _stat(item: os.DirEntry, follow: bool) -> os.stat_result:
    """Stat ``item``, through a symlink when ``follow`` is set. A broken
    symlink falls back to the link itself, so it is still listed."""
    if follow:
        try:
            return item.stat()
        except OSError:
            pass
    return item.stat(follow_symlinks=False)


def walk(
    root: str, hidden: bool = False, no_ignore: bool = False, follow: bool = False
) -> Iterator[Entry]:
    """Yield every file and directory below ``root`` (not ``root`` itself).

    A directory's entries are yielded in name order, then its subdirectories
    are walked one by one, in the same order.
    Hidden names (leading dot) are skipped unless ``hidden`` is set, and
    directories in DEFAULT_SKIP are skipped unless ``no_ignore`` is set.
    Directory symlinks are listed but not followed unless ``follow`` is set.
    When following, a link back to a directory that is already being walked
    (a loop) is listed but not entered. Directories that can't be read are
    skipped silently.
    """
    # Each stack item carries the (device, inode) ids of the directories
    # above it, so a symlink pointing back up the tree can be spotted.
    stack = [(root, frozenset({_dir_id(root)}))]
    while stack:
        current, ancestors = stack.pop()
        try:
            with os.scandir(current) as it:
                items = sorted(it, key=lambda e: e.name)
        except OSError:
            continue

        subdirs = []
        for item in items:
            if not hidden and item.name.startswith("."):
                continue
            try:
                is_dir = item.is_dir(follow_symlinks=follow)
                if is_dir and not no_ignore and item.name in DEFAULT_SKIP:
                    continue
                st = _stat(item, follow)
            except OSError:
                continue
            path = _join(current, item.name)
            yield Entry(path, is_dir, 0 if is_dir else st.st_size, st.st_mtime)
            if is_dir:
                dir_id = (st.st_dev, st.st_ino)
                if dir_id not in ancestors:
                    subdirs.append((path, ancestors | {dir_id}))
        # Reversed so the first subdirectory is popped (and walked) first.
        stack.extend(reversed(subdirs))
