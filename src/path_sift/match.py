"""Fuzzy matching and scoring of a query against paths.

A query matches a path when its letters appear in the path in order, not
necessarily next to each other ("rdme" matches "README.md"). Space-separated
terms must all match. Matching is case-insensitive unless the query contains
an uppercase letter (smart case).

The match is found right to left, so letters land as close to the end of the
path (the file name) as possible. The score then rewards matches at word
starts, runs of consecutive letters and matches inside the file name, and
penalises gaps.
"""

import os
from dataclasses import dataclass

BOUNDARY_CHARS = "/\\_-. "

SCORE_MATCH = 16
BONUS_BOUNDARY = 10
BONUS_CONSECUTIVE = 8
BONUS_BASENAME = 6
PENALTY_GAP = 1
MAX_GAP_PENALTY = 6


@dataclass(frozen=True)
class Match:
    score: int
    positions: tuple[int, ...]


def _is_boundary(text: str, i: int) -> bool:
    if i == 0:
        return True
    prev, cur = text[i - 1], text[i]
    if prev in BOUNDARY_CHARS:
        return True
    # camelCase and letter-to-digit boundaries: "fooBar", "log2"
    return (prev.islower() and cur.isupper()) or (prev.isalpha() and cur.isdigit())


def _positions(term: str, haystack: str) -> list[int] | None:
    """Rightmost in-order positions of ``term``'s letters in ``haystack``."""
    positions = []
    end = len(haystack)
    for ch in reversed(term):
        end = haystack.rfind(ch, 0, end)
        if end < 0:
            return None
        positions.append(end)
    positions.reverse()
    return positions


def _score_positions(text: str, positions: list[int], base_start: int) -> int:
    score = 0
    prev = None
    for i in positions:
        score += SCORE_MATCH
        if _is_boundary(text, i):
            score += BONUS_BOUNDARY
        if i >= base_start:
            score += BONUS_BASENAME
        if prev is not None:
            if i == prev + 1:
                score += BONUS_CONSECUTIVE
            else:
                score -= min((i - prev - 1) * PENALTY_GAP, MAX_GAP_PENALTY)
        prev = i
    return score


def fuzzy_match(query: str, text: str) -> Match | None:
    """Return the Match of ``query`` in ``text``, or None if it doesn't match.

    An empty (or all-space) query matches everything with score 0.
    """
    terms = query.split()
    if not terms:
        return Match(0, ())
    smart_case = query != query.lower()
    haystack = text if smart_case else text.lower()
    base_start = len(text) - len(os.path.basename(text.rstrip("/\\")))

    total = 0
    used: set[int] = set()
    for term in terms:
        positions = _positions(term, haystack)
        if positions is None:
            return None
        total += _score_positions(text, positions, base_start)
        used.update(positions)
    return Match(total, tuple(sorted(used)))


def rank(query: str, paths: list[str], limit: int | None = None) -> list[tuple[str, Match]]:
    """Paths that match ``query``, best first.

    Ties go to the shorter path, then alphabetical order. With an empty query
    every path is returned in its original order.
    """
    results = []
    for path in paths:
        m = fuzzy_match(query, path)
        if m is not None:
            results.append((path, m))
    if query.strip():
        results.sort(key=lambda t: (-t[1].score, len(t[0]), t[0]))
    return results if limit is None else results[:limit]
