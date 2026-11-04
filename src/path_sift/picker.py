"""State of the interactive picker, kept apart from curses so it can be tested."""

from .match import Match, rank


class Picker:
    """The query being typed, the ranked results, the highlighted row and the
    paths marked for multi-select."""

    def __init__(self, items: list[str], query: str = ""):
        self.items = items
        self.query = ""
        self.results: list[tuple[str, Match]] = []
        self.cursor = 0
        self.top = 0
        # A dict keeps the marks in the order they were made.
        self.marked: dict[str, None] = {}
        self.set_query(query)

    def set_query(self, query: str) -> None:
        # Typing more letters can only remove matches, so when the new query
        # extends the old one, re-rank only what matched before.
        if self.query and query.startswith(self.query):
            pool = [path for path, _ in self.results]
        else:
            pool = self.items
        self.query = query
        self.results = rank(query, pool)
        self.cursor = 0
        self.top = 0

    def insert(self, text: str) -> None:
        self.set_query(self.query + text)

    def backspace(self) -> None:
        if self.query:
            self.set_query(self.query[:-1])

    def delete_word(self) -> None:
        """Remove the last word and the spaces after it (like Ctrl-W in a shell)."""
        head = self.query.rstrip()
        self.set_query(head[: head.rfind(" ") + 1])

    def clear(self) -> None:
        self.set_query("")

    def move(self, delta: int) -> None:
        if self.results:
            self.cursor = max(0, min(len(self.results) - 1, self.cursor + delta))

    def selected(self) -> str | None:
        if not self.results:
            return None
        return self.results[self.cursor][0]

    def toggle_mark(self) -> None:
        """Mark or unmark the highlighted path, then move down a row."""
        path = self.selected()
        if path is None:
            return
        if path in self.marked:
            del self.marked[path]
        else:
            self.marked[path] = None
        self.move(1)

    def chosen(self) -> list[str]:
        """What Enter picks: the marked paths if there are any (marks survive
        query changes), otherwise the highlighted one."""
        if self.marked:
            return list(self.marked)
        path = self.selected()
        return [] if path is None else [path]

    def visible(self, height: int) -> list[tuple[int, str, Match]]:
        """Rows to draw in a list ``height`` lines tall, scrolled so the
        cursor is on screen. Each row is (result index, path, match)."""
        if height <= 0:
            return []
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + height:
            self.top = self.cursor - height + 1
        rows = self.results[self.top : self.top + height]
        return [(self.top + i, path, m) for i, (path, m) in enumerate(rows)]
