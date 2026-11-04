# Roadmap

What comes after v0.1, with rough estimates. Total: **24.5 hours**.

## Features

- [ ] Respect `.gitignore` / `.ignore` files while walking (4 h)
- [ ] Preview pane in the picker: first lines of a text file, or a directory listing (3 h)
- [x] Multi-select in the picker (Tab to mark, Enter prints all marked paths) (2 h)
- [x] `--exec CMD` to run a command on the selected path(s) (1.5 h)
- [ ] Config file (`~/.config/path-sift/config.toml`) for default flags and skip list (2 h)

## Bugs and edge cases

- [x] `--follow` for directory symlinks, with loop detection (1.5 h)
- [ ] File names that are not valid UTF-8: display safely, print the raw bytes (1 h)
- [ ] Huge trees: show results in the picker while the walk is still running (2 h)

## Refactors

- [ ] Replace the greedy backward match with optimal DP scoring, keeping a fast prefilter (2 h)
- [ ] Make the walker a lazy generator the picker can consume incrementally (1 h)

## Tests

- [ ] Picker key-handling tests driven by a fake curses screen (1.5 h)
- [ ] Benchmark script on a generated 100k-file tree, with a target time in the README (1 h)

## Docs

- [ ] Shell integration snippets for bash, zsh and fish (key binding that inserts a path) (1 h)
- [ ] Man page generated from the argparse help (1 h)
