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


def test_follow_enters_dir_symlinks(tmp_path):
    make_tree(tmp_path, ["real/inside.txt"])
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    entries = {os.path.relpath(e.path, tmp_path): e for e in walk(str(tmp_path), follow=True)}
    assert "link/inside.txt" in entries
    assert entries["link"].is_dir


def test_follow_stats_file_symlink_targets(tmp_path):
    make_tree(tmp_path, ["data.bin"])
    (tmp_path / "data.bin").write_bytes(b"x" * 5000)
    (tmp_path / "alias").symlink_to(tmp_path / "data.bin")
    sizes = {os.path.basename(e.path): e.size for e in walk(str(tmp_path), follow=True)}
    assert sizes["alias"] == 5000


def test_follow_lists_broken_symlinks(tmp_path):
    (tmp_path / "dangling").symlink_to(tmp_path / "gone")
    entries = list(walk(str(tmp_path), follow=True))
    assert [os.path.basename(e.path) for e in entries] == ["dangling"]
    assert not entries[0].is_dir


def test_follow_does_not_loop(tmp_path):
    make_tree(tmp_path, ["a/b/file.txt"])
    (tmp_path / "a/b/up").symlink_to(tmp_path / "a", target_is_directory=True)
    (tmp_path / "a/self").symlink_to(tmp_path / "a", target_is_directory=True)
    (tmp_path / "root").symlink_to(tmp_path, target_is_directory=True)
    assert paths_of(tmp_path, follow=True) == [
        "a", "root", "a/b", "a/self", "a/b/file.txt", "a/b/up",
    ]


def test_follow_walks_a_sibling_twice(tmp_path):
    # Not a loop: the same folder reached by two paths is listed under both.
    make_tree(tmp_path, ["shared/x.txt", "user/"])
    (tmp_path / "user/shared").symlink_to(tmp_path / "shared", target_is_directory=True)
    paths = paths_of(tmp_path, follow=True)
    assert "shared/x.txt" in paths
    assert "user/shared/x.txt" in paths


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
