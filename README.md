# path-sift

A command-line file finder: type a few letters of a file's name and get matching paths
ranked best first, optionally narrowed down by type, extension, size and age. With `-i`
it opens an interactive picker in the terminal and prints the paths you choose, so it
can feed other commands (`vim "$(path-sift -i)"`).

It's for people who live in a terminal and are tired of writing long `find` expressions
to locate one file.

Built with Python 3.11+ and only the standard library (`os.scandir`, `argparse`,
`curses`). Tests use pytest. Linux and macOS; the picker needs a terminal with curses.

## Install

```bash
git clone https://github.com/landry-some/path-sift.git
cd path-sift
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Run

```bash
path-sift conf                      # paths matching "conf", best first
path-sift conf ~/projects ~/notes   # search these folders instead of "."
path-sift -e png --min-size 1M      # PNG files of 1 MiB or more
path-sift log --newer 2d -t f       # files matching "log" changed in the last 2 days
path-sift -t d                      # every directory, no query
path-sift -i                        # interactive picker, prints the chosen path(s)
vim "$(path-sift -i conf)"          # open the picked file
path-sift --help                    # all options
```

Example output (`path-sift conf`, run inside a made-up `projects` folder):

```
site-config
blog/config.toml
notes/conference-ideas.txt
site-config/nginx/default.conf
blog/posts/configuring-backups.md
site-config/nginx
```

### How matching works

The letters of the query must appear in the path in the same order, but not
necessarily next to each other: `rdme` finds `README.md`. Space-separated words must
all match (`src test` finds `src/tests/test_cli.py`). Matching ignores case unless
the query has an uppercase letter.

Results are ranked higher when the letters fall at the start of words (`/`, `_`, `-`,
`.`, camelCase), come in runs, and are in the file name rather than in a parent folder.
Ties go to the shorter path. With no query, entries are listed in walk order.

### Options

| Option | Meaning |
|---|---|
| `-i`, `--interactive` | Open the picker; the query becomes its starting text |
| `-t f` / `-t d` | Only files / only directories |
| `-e EXT`, `--ext EXT` | Only files with this extension, case-insensitive; repeatable |
| `--min-size SIZE`, `--max-size SIZE` | File size limits, inclusive: `500`, `10k`, `1.5M`, `2G` (powers of 1024). Directories are left out |
| `--newer AGE`, `--older AGE` | Modified within / more than AGE ago: `90s`, `30m`, `2h`, `3d`, `1w` |
| `-H`, `--hidden` | Include names starting with a dot |
| `--no-ignore` | Also go into `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.hg`, `.svn`, `.tox`, `.mypy_cache`, `.pytest_cache` |
| `-L`, `--follow` | Follow directory symlinks; a link back up into a folder already being walked is listed but not entered |
| `-n N`, `--limit N` | Print at most N results (not with `-i`) |

Directory symlinks are listed but not followed unless you pass `-L`. Folders that can't be read are skipped.

### Picker keys

| Key | Action |
|---|---|
| typing | Edit the query, results update as you type |
| Backspace, Ctrl-W, Ctrl-U | Delete a letter, the last word, everything |
| Up / Down, Ctrl-P / Ctrl-N | Move the highlight |
| PageUp / PageDown | Move a screen at a time |
| Tab | Mark or unmark the highlighted path (shown with `*`) and move down |
| Enter | Print the marked paths, one per line, in the order marked; with no marks, the highlighted path |
| Esc, Ctrl-C, Ctrl-G | Exit without printing |

Marks stay when you change the query, so you can collect paths from several searches.
The picker draws on `/dev/tty`, so it works inside `$(...)` and pipes.

### Exit codes

`0` something was printed, `1` no matches or the picker was cancelled, `2` bad
arguments or no terminal for the picker.

## Test

```bash
pip install -e '.[test]'
pytest
```

## Plans

See [ROADMAP.md](ROADMAP.md).

## License

MIT, see [LICENSE](LICENSE).
