# path-sift

A command-line file finder: type a few letters of a file's name and get matching paths
ranked best first, optionally narrowed down by type, extension, size and age. With `-i`
it opens an interactive picker in the terminal and prints the path you choose, so it
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
path-sift --help
```

## Test

```bash
pip install -e '.[test]'
pytest
```

## Plans

See [ROADMAP.md](ROADMAP.md).

## License

MIT, see [LICENSE](LICENSE).
