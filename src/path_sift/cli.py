"""Command-line entry point for path-sift."""

import argparse
import os
import sys

from . import __version__
from .filters import Filters, normalize_ext, parse_age, parse_size
from .match import rank
from .tui import TerminalError, pick
from .walk import walk


def _arg(parse):
    """Wrap a parser so argparse reports its ValueError as a usage error."""

    def convert(text):
        try:
            return parse(text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None

    return convert


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="path-sift",
        description="Find files and directories by fuzzy name match, best match first.",
    )
    parser.add_argument("query", nargs="?", default="", help="letters to look for, in order (default: list everything)")
    parser.add_argument("paths", nargs="*", metavar="path", help="folders to search (default: current folder)")
    parser.add_argument("-i", "--interactive", action="store_true", help="pick one result in a terminal UI and print it (QUERY becomes the starting text)")
    parser.add_argument("-t", "--type", choices=["f", "d"], dest="kind", help="only files (f) or only directories (d)")
    parser.add_argument("-e", "--ext", action="append", default=[], help="only files with this extension (repeatable)")
    parser.add_argument("--min-size", type=_arg(parse_size), metavar="SIZE", help="only files at least this big (500, 10k, 1.5M, 2G)")
    parser.add_argument("--max-size", type=_arg(parse_size), metavar="SIZE", help="only files at most this big")
    parser.add_argument("--newer", type=_arg(parse_age), metavar="AGE", help="only entries modified within AGE (30m, 2h, 3d, 1w)")
    parser.add_argument("--older", type=_arg(parse_age), metavar="AGE", help="only entries last modified more than AGE ago")
    parser.add_argument("-H", "--hidden", action="store_true", help="include hidden files and directories")
    parser.add_argument("--no-ignore", action="store_true", help="also search .git, node_modules, __pycache__, .venv and similar")
    parser.add_argument("-L", "--follow", action="store_true", help="follow directory symlinks (loops are detected and not entered)")
    parser.add_argument("-n", "--limit", type=int, metavar="N", help="print at most N results")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def collect(
    roots: list[str], filters: Filters, hidden: bool, no_ignore: bool, follow: bool = False
) -> list[str]:
    """Paths of all entries below ``roots`` that pass ``filters``."""
    found = []
    for root in roots:
        for entry in walk(root, hidden=hidden, no_ignore=no_ignore, follow=follow):
            if filters.accepts(entry):
                found.append(entry.path)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.interactive and args.limit is not None:
        parser.error("--limit can't be used with --interactive")
    roots = args.paths or ["."]
    for root in roots:
        if not os.path.isdir(root):
            parser.error(f"not a directory: {root}")

    filters = Filters(
        kind=args.kind,
        exts=frozenset(normalize_ext(e) for e in args.ext),
        min_size=args.min_size,
        max_size=args.max_size,
        newer=args.newer,
        older=args.older,
    )
    candidates = collect(roots, filters, args.hidden, args.no_ignore, args.follow)
    if args.interactive:
        return _interactive(candidates, args.query)
    results = rank(args.query, candidates, args.limit)
    try:
        for path, _ in results:
            print(path)
        sys.stdout.flush()
    except BrokenPipeError:
        # `path-sift ... | head` closed the pipe early; that's fine. Point
        # stdout at /dev/null so the interpreter's final flush stays quiet.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    return 0 if results else 1


def _interactive(candidates: list[str], query: str) -> int:
    if not candidates:
        print("path-sift: nothing to pick from", file=sys.stderr)
        return 1
    try:
        choice = pick(candidates, query)
    except TerminalError as exc:
        print(f"path-sift: {exc}", file=sys.stderr)
        return 2
    if choice is None:
        return 1
    print(choice)
    return 0


if __name__ == "__main__":
    sys.exit(main())
