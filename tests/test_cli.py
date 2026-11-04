import os
import subprocess
import sys
import time

import pytest

from path_sift import cli
from path_sift.cli import command_line, main


@pytest.fixture
def tree(tmp_path, monkeypatch):
    files = {
        "README.md": 300,
        "src/app/config.py": 2000,
        "src/app/main.py": 5000,
        "docs/config-guide.md": 40_000,
        "build/big.bin": 3 * 1024 * 1024,
        ".hidden/conf.txt": 10,
        "node_modules/pkg/config.js": 10,
    }
    for rel, size in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x" * size)
    old = time.time() - 10 * 86400
    os.utime(tmp_path / "docs/config-guide.md", (old, old))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(capsys, *argv):
    code = main(list(argv))
    return code, capsys.readouterr().out.splitlines()


def test_ranked_query(tree, capsys):
    code, lines = run(capsys, "config")
    assert code == 0
    assert lines[0] == os.path.join("src", "app", "config.py")
    assert os.path.join("docs", "config-guide.md") in lines
    assert not any("node_modules" in line or ".hidden" in line for line in lines)


def test_no_query_lists_everything(tree, capsys):
    code, lines = run(capsys)
    assert code == 0
    assert "README.md" in lines
    assert "src" in lines


def test_no_match_exits_1(tree, capsys):
    code, lines = run(capsys, "zzzz")
    assert code == 1
    assert lines == []


def test_type_and_ext(tree, capsys):
    _, lines = run(capsys, "", "-t", "d")
    assert set(lines) == {"build", "docs", "src", os.path.join("src", "app")}
    _, lines = run(capsys, "conf", "-e", ".MD")
    assert lines == [os.path.join("docs", "config-guide.md")]


def test_size_and_age(tree, capsys):
    _, lines = run(capsys, "", "--min-size", "1M")
    assert lines == [os.path.join("build", "big.bin")]
    _, lines = run(capsys, "", "--older", "1w")
    assert lines == [os.path.join("docs", "config-guide.md")]
    _, lines = run(capsys, "conf", "--newer", "1d", "-t", "f")
    assert lines == [os.path.join("src", "app", "config.py")]


def test_hidden_and_no_ignore(tree, capsys):
    _, lines = run(capsys, "conf", "-H")
    assert os.path.join(".hidden", "conf.txt") in lines
    _, lines = run(capsys, "conf", "--no-ignore")
    assert os.path.join("node_modules", "pkg", "config.js") in lines


def test_follow(tree, capsys):
    (tree / "docs-link").symlink_to(tree / "docs", target_is_directory=True)
    target = os.path.join("docs-link", "config-guide.md")
    _, lines = run(capsys, "guide")
    assert target not in lines
    _, lines = run(capsys, "guide", "-L")
    assert target in lines


def test_limit(tree, capsys):
    _, lines = run(capsys, "", "-n", "2")
    assert len(lines) == 2


def test_explicit_paths(tree, capsys):
    _, lines = run(capsys, "md", "docs", "src")
    assert lines == [os.path.join("docs", "config-guide.md")]


@pytest.mark.parametrize(
    "words, expected",
    [
        (["ls", "-l"], ["ls", "-l", "a", "b"]),
        (["cp", "{}", "/tmp"], ["cp", "a", "b", "/tmp"]),
        (["diff", "{}", "--", "{}"], ["diff", "a", "b", "--", "a", "b"]),
    ],
)
def test_command_line(words, expected):
    assert command_line(words, ["a", "b"]) == expected


ECHO_ARGS = "import sys; print(repr(sys.argv[1:])); sys.exit(len(sys.argv) - 1)"


def exec_argv(*words):
    return " ".join([f'"{sys.executable}"', "-c", f'"{ECHO_ARGS}"', *words])


def test_exec_runs_once_with_all_results(tree, capfd):
    code = main(["main", "src", "-t", "f", "--exec", exec_argv("first")])
    out = capfd.readouterr().out
    assert code == 2  # the command's own exit code: two arguments
    assert out == repr(["first", os.path.join("src", "app", "main.py")]) + "\n"


def test_exec_placeholder(tree, capfd):
    code = main(["", "docs", "-x", exec_argv("{}", "last")])
    assert code == 2
    assert capfd.readouterr().out == repr([os.path.join("docs", "config-guide.md"), "last"]) + "\n"


def test_exec_not_run_without_results(tree, capfd):
    assert main(["zzzz", "--exec", exec_argv()]) == 1
    assert capfd.readouterr().out == ""


def test_exec_missing_command(tree, capsys):
    assert main(["readme", "--exec", "no-such-command-path-sift"]) == 127
    assert "command not found: no-such-command-path-sift" in capsys.readouterr().err


def test_exec_with_interactive(tree, monkeypatch):
    seen = {}

    def fake_run(argv):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(cli, "pick", lambda items, query: ["README.md", "build"])
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert main(["-i", "--exec", "vim -p"]) == 0
    assert seen["argv"] == ["vim", "-p", "README.md", "build"]


@pytest.mark.parametrize(
    "argv, message",
    [
        (["x", "--min-size", "huge"], "invalid size"),
        (["x", "--newer", "3y"], "invalid age"),
        (["x", "-n", "0"], "--limit must be at least 1"),
        (["x", "missing-dir"], "not a directory"),
        (["x", "--exec", ""], "--exec needs a command"),
        (["x", "--exec", "vim 'oops"], "No closing quotation"),
    ],
)
def test_bad_arguments(tree, capsys, argv, message):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


def test_closed_pipe_is_quiet(tree):
    for i in range(20000):
        (tree / f"f{i}.txt").touch()
    script = "import sys; from path_sift.cli import main; sys.exit(main())"
    proc = subprocess.run(
        f'"{sys.executable}" -c "{script}" | head -n 1',
        shell=True, capture_output=True, text=True, cwd=tree,
    )
    assert proc.stdout.count("\n") == 1
    assert proc.stderr == ""
