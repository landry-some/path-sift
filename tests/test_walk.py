import os

from path_sift.walk import walk


def make_tree(root, paths):
    for rel in paths:
        target = root / rel
        if rel.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x" * len(rel))


def paths_of(root, **kwargs):
    return [os.path.relpath(e.path, root) for e in walk(str(root), **kwargs)]


def test_lists_files_and_dirs_in_order(tmp_path):
    make_tree(tmp_path, ["b.txt", "a/z.txt", "a/y/", "c/"])
    assert paths_of(tmp_path) == ["a", "b.txt", "c", "a/y", "a/z.txt"]


def test_entry_fields(tmp_path):
    make_tree(tmp_path, ["notes.md", "docs/"])
    entries = {os.path.basename(e.path): e for e in walk(str(tmp_path))}
    assert entries["notes.md"].size == len("notes.md")
    assert not entries["notes.md"].is_dir
    assert entries["docs"].is_dir
    assert entries["docs"].size == 0
    assert entries["notes.md"].mtime > 0


def test_skips_hidden_unless_asked(tmp_path):
    make_tree(tmp_path, [".env", ".config/app.toml", "visible.txt"])
    assert paths_of(tmp_path) == ["visible.txt"]
    assert paths_of(tmp_path, hidden=True) == [
        ".config", ".env", "visible.txt", ".config/app.toml",
    ]


def test_skips_default_dirs_unless_no_ignore(tmp_path):
    make_tree(tmp_path, ["node_modules/pkg/index.js", "__pycache__/m.pyc", "src/m.py"])
    assert paths_of(tmp_path) == ["src", "src/m.py"]
    assert "node_modules/pkg/index.js" in paths_of(tmp_path, no_ignore=True)


def test_hidden_flag_alone_still_skips_git(tmp_path):
    make_tree(tmp_path, [".git/HEAD", ".github/ci.yml"])
    assert paths_of(tmp_path, hidden=True) == [".github", ".github/ci.yml"]


def test_dot_root_gives_bare_relative_paths(tmp_path, monkeypatch):
    make_tree(tmp_path, ["a/b.txt"])
    monkeypatch.chdir(tmp_path)
    assert [e.path for e in walk(".")] == ["a", os.path.join("a", "b.txt")]


def test_does_not_follow_dir_symlinks(tmp_path):
    make_tree(tmp_path, ["real/inside.txt"])
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    paths = paths_of(tmp_path)
    assert "link" in paths
    assert "link/inside.txt" not in paths
    link = next(e for e in walk(str(tmp_path)) if e.path.endswith("link"))
    assert not link.is_dir


def test_unreadable_dir_is_skipped(tmp_path):
    make_tree(tmp_path, ["locked/secret.txt", "open.txt"])
    os.chmod(tmp_path / "locked", 0)
    try:
        if os.access(tmp_path / "locked", os.R_OK):  # running as root
            return
        assert paths_of(tmp_path) == ["locked", "open.txt"]
    finally:
        os.chmod(tmp_path / "locked", 0o755)


def test_missing_root_yields_nothing(tmp_path):
    assert list(walk(str(tmp_path / "nope"))) == []
