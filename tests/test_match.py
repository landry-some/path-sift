from path_sift.match import fuzzy_match, rank


def best(query, paths):
    return [p for p, _ in rank(query, paths)]


def test_subsequence_matches():
    assert fuzzy_match("rdme", "README.md") is not None
    assert fuzzy_match("rmde", "README.md") is None


def test_positions_point_at_matched_letters():
    m = fuzzy_match("cfg", "app/config.toml")
    assert "".join("app/config.toml"[i] for i in m.positions) == "cfg"


def test_match_prefers_the_file_name():
    m = fuzzy_match("main", "main/src/main.py")
    assert m.positions == (9, 10, 11, 12)


def test_smart_case():
    assert fuzzy_match("readme", "README.md") is not None
    assert fuzzy_match("Readme", "README.md") is None
    assert fuzzy_match("README", "README.md") is not None


def test_empty_query_matches_everything():
    assert fuzzy_match("", "anything").score == 0
    assert fuzzy_match("   ", "anything").score == 0


def test_all_terms_must_match():
    assert fuzzy_match("src test", "src/tests/test_cli.py") is not None
    assert fuzzy_match("src docs", "src/tests/test_cli.py") is None


def test_consecutive_beats_scattered():
    assert best("conf", ["c/o/n/f.txt", "app.conf"]) == ["app.conf", "c/o/n/f.txt"]


def test_word_start_beats_middle():
    assert best("log", ["catalog.txt", "server.log"]) == ["server.log", "catalog.txt"]


def test_camel_case_counts_as_word_start():
    assert best("ub", ["UserButton.tsx", "tubular.tsx"])[0] == "UserButton.tsx"


def test_basename_beats_directory():
    assert best("notes", ["notes/todo.txt", "work/notes.txt"])[0] == "work/notes.txt"


def test_ties_go_to_shorter_then_alphabetical():
    assert best("a", ["b/a", "c/a", "a"]) == ["a", "b/a", "c/a"]


def test_rank_filters_out_non_matches_and_limits():
    paths = ["alpha.txt", "beta.txt", "gamma.txt", "delta.md"]
    assert best("md", paths) == ["delta.md"]
    assert len(rank("a", paths, limit=2)) == 2


def test_empty_query_keeps_original_order():
    paths = ["z", "a", "m"]
    assert best("", paths) == ["z", "a", "m"]
