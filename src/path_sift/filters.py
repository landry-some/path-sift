"""Entry filters: type, extension, size and modification age."""

import os
import re
import time
from dataclasses import dataclass

from .walk import Entry

SIZE_UNITS = {"": 1, "b": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}
AGE_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 7 * 86400}

_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([kmgt]?)(?:i?b)?", re.IGNORECASE)
_AGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([smhdw])", re.IGNORECASE)


def parse_size(text: str) -> int:
    """Parse "200", "10k", "1.5M", "2GiB" into bytes (units are powers of 1024)."""
    m = _SIZE_RE.fullmatch(text.strip())
    if not m:
        raise ValueError(f"invalid size: {text!r} (examples: 500, 10k, 1.5M, 2G)")
    return int(float(m.group(1)) * SIZE_UNITS[m.group(2).lower()])


def parse_age(text: str) -> float:
    """Parse "90s", "30m", "2h", "3d", "1w" into seconds."""
    m = _AGE_RE.fullmatch(text.strip())
    if not m:
        raise ValueError(f"invalid age: {text!r} (examples: 30m, 2h, 3d, 1w)")
    return float(m.group(1)) * AGE_UNITS[m.group(2).lower()]


def normalize_ext(ext: str) -> str:
    return ext.lower().lstrip(".")


@dataclass(frozen=True)
class Filters:
    """Conditions an entry must meet. Unset fields don't filter anything.

    ``kind`` is "f" for files or "d" for directories. ``exts`` are compared
    without the leading dot, case-insensitively. Size limits only apply to
    files, so they also drop directories. ``newer``/``older`` are ages in
    seconds, compared against the modification time.
    """

    kind: str | None = None
    exts: frozenset[str] = frozenset()
    min_size: int | None = None
    max_size: int | None = None
    newer: float | None = None
    older: float | None = None

    def accepts(self, entry: Entry, now: float | None = None) -> bool:
        if self.kind == "f" and entry.is_dir:
            return False
        if self.kind == "d" and not entry.is_dir:
            return False
        if self.exts:
            ext = os.path.splitext(entry.path)[1]
            if entry.is_dir or normalize_ext(ext) not in self.exts:
                return False
        if self.min_size is not None or self.max_size is not None:
            if entry.is_dir:
                return False
            if self.min_size is not None and entry.size < self.min_size:
                return False
            if self.max_size is not None and entry.size > self.max_size:
                return False
        if self.newer is not None or self.older is not None:
            age = (time.time() if now is None else now) - entry.mtime
            if self.newer is not None and age > self.newer:
                return False
            if self.older is not None and age < self.older:
                return False
        return True
