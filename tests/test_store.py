"""Persistence and the statistics computed from it."""

import pytest

from cubetrainer.store import Store
from cubetrainer.store.stats import (
    best_average,
    case_report,
    phase_summary,
    rank_by_weakness,
    rolling_average,
    solve_summary,
    trimmed_mean,
    wca_average,
)


@pytest.fixture()
def store():
    with Store.in_memory() as db:
        yield db


# --- storage ---------------------------------------------------------------

def test_a_rep_records_its_case_scramble_and_time(store):
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "T", "F R U2", 1.834)
    rep, = store.reps()
    assert rep["case_id"] == "T"
    assert rep["scramble"] == "F R U2"
    assert rep["duration_ms"] == 1834
    assert rep["peeked"] == 0
    assert rep["penalty"] == "none"


def test_a_dnf_rep_stores_no_duration(store):
    """A fumbled algorithm has no time. Storing one would be a lie."""
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "Ja", "R U", 4.2, penalty="dnf")
    rep, = store.reps()
    assert rep["duration_ms"] is None
    assert rep["penalty"] == "dnf"


def test_a_solve_stores_each_timed_phase_as_its_own_row(store):
    session = store.start_session("solve")
    store.record_solve(session, "R U F", 18.4, [
        ("cross", 2.1), ("f2l", 9.3), ("oll", 3.0), ("pll", 4.0),
    ])
    splits = store.splits()
    assert [s["phase"] for s in splits] == ["cross", "f2l", "oll", "pll"]
    assert [s["ordinal"] for s in splits] == [0, 1, 2, 3]
    assert splits[1]["duration_ms"] == 9300


def test_timing_only_the_cross_stores_one_split_not_three_nulls(store):
    """The reason phase splits are rows rather than columns."""
    session = store.start_session("solve")
    store.record_solve(session, "R U F", 2.4, [("cross", 2.4)])
    splits = store.splits()
    assert len(splits) == 1
    assert splits[0]["phase"] == "cross"


def test_reps_can_be_filtered_by_case_and_session(store):
    first = store.start_session("drill", "PLL")
    second = store.start_session("drill", "PLL")
    store.record_rep(first, "T", "x", 1.0)
    store.record_rep(first, "Ja", "x", 2.0)
    store.record_rep(second, "T", "x", 3.0)
    assert len(store.reps(case_id="T")) == 2
    assert len(store.reps(session_id=first)) == 2
    assert len(store.reps(case_id="T", session_id=second)) == 1


def test_deleting_a_session_removes_its_attempts(store):
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "T", "x", 1.0)
    store.connection.execute("DELETE FROM session WHERE id = ?", (session,))
    store.connection.commit()
    assert store.reps() == []


def test_a_case_set_can_be_saved_reloaded_and_replaced(store):
    store.save_case_set("bad ones", "PLL", ["T", "Ja", "V"])
    assert store.load_case_set("bad ones", "PLL") == ["Ja", "T", "V"]
    store.save_case_set("bad ones", "PLL", ["H"])
    assert store.load_case_set("bad ones", "PLL") == ["H"]
    assert store.case_set_names("PLL") == ["bad ones"]


def test_case_sets_are_scoped_to_a_phase(store):
    store.save_case_set("mine", "PLL", ["T"])
    store.save_case_set("mine", "OLL", ["21"])
    assert store.load_case_set("mine", "PLL") == ["T"]
    assert store.load_case_set("mine", "OLL") == ["21"]


def test_an_unknown_case_set_loads_as_none(store):
    assert store.load_case_set("nope", "PLL") is None


def test_an_algorithm_override_replaces_rather_than_duplicates(store):
    store.set_algorithm("T", "R U R2")
    store.set_algorithm("T", "R U R' F")
    assert store.algorithm_overrides() == {"T": "R U R' F"}
    store.clear_algorithm("T")
    assert store.algorithm_overrides() == {}


# --- averages --------------------------------------------------------------

def test_wca_average_drops_the_best_and_worst():
    assert wca_average([1.0, 2.0, 3.0, 4.0, 100.0]) == pytest.approx(3.0)


def test_a_single_dnf_is_absorbed_as_the_worst_attempt():
    assert wca_average([1.0, 2.0, 3.0, 4.0, None]) == pytest.approx(3.0)


def test_two_dnfs_make_the_average_a_dnf():
    assert wca_average([1.0, 2.0, 3.0, None, None]) is None


def test_an_average_needs_at_least_three_attempts():
    assert wca_average([1.0, 2.0]) is None


def test_rolling_average_uses_only_the_most_recent_window():
    times = [10.0, 10.0, 10.0, 10.0, 10.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert rolling_average(times, 5) == pytest.approx(3.0)
    assert rolling_average(times, 20) is None


def test_best_average_scans_the_whole_history():
    times = [9.0, 9.0, 9.0, 9.0, 9.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert best_average(times, 5) == pytest.approx(3.0)


def test_trimmed_mean_ignores_the_one_dropped_cube():
    assert trimmed_mean([1.0, 1.0, 1.0, 1.0, 60.0]) == pytest.approx(1.0)


def test_trimmed_mean_falls_back_to_the_plain_mean_when_data_is_thin():
    assert trimmed_mean([1.0, 3.0]) == pytest.approx(2.0)


# --- case reports ----------------------------------------------------------

def test_peeked_reps_are_excluded_from_the_average_but_still_counted(store):
    """Otherwise "my T perm averages 1.8s" is a claim about reading, not recall."""
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "T", "x", 1.0)
    store.record_rep(session, "T", "x", 1.0)
    store.record_rep(session, "T", "x", 9.0, peeked=True)
    report = case_report("T", store.reps(case_id="T"), move_count=14)
    assert report.attempts == 3
    assert report.counted == 2
    assert report.mean == pytest.approx(1.0)
    assert report.peek_rate == pytest.approx(1 / 3)


def test_dnf_rate_is_reported_separately_from_time(store):
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "V", "x", 2.0)
    store.record_rep(session, "V", "x", None, penalty="dnf")
    report = case_report("V", store.reps(case_id="V"), move_count=17)
    assert report.dnf_rate == pytest.approx(0.5)
    assert report.mean == pytest.approx(2.0)
    assert report.counted == 1


def test_seconds_per_move_normalises_for_algorithm_length(store):
    """A long algorithm is not the same thing as a badly executed one."""
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "T", "x", 2.8)
    report = case_report("T", store.reps(case_id="T"), move_count=14)
    assert report.seconds_per_move == pytest.approx(0.2)


def test_a_case_with_no_reps_has_no_report(store):
    assert case_report("T", []) is None


def test_a_report_knows_when_it_is_built_on_too_little_data(store):
    session = store.start_session("drill", "PLL")
    for _ in range(4):
        store.record_rep(session, "T", "x", 2.0)
    assert not case_report("T", store.reps(case_id="T"), 14).has_enough_data
    store.record_rep(session, "T", "x", 2.0)
    assert case_report("T", store.reps(case_id="T"), 14).has_enough_data


def test_ranking_by_time_per_move_beats_ranking_by_raw_time(store):
    """A long algorithm executed well should not outrank a short one fumbled."""
    session = store.start_session("drill", "PLL")
    for _ in range(3):
        store.record_rep(session, "Na", "x", 4.0)   # 21 moves, 0.19 s/move
        store.record_rep(session, "Ua", "x", 3.0)   # 11 moves, 0.27 s/move
    reports = [
        case_report("Na", store.reps(case_id="Na"), 21),
        case_report("Ua", store.reps(case_id="Ua"), 11),
    ]
    by_raw_time = sorted(reports, key=lambda r: r.mean, reverse=True)
    assert by_raw_time[0].case_id == "Na"
    by_execution = rank_by_weakness(reports)
    assert by_execution[0].case_id == "Ua"


# --- phase and solve summaries ---------------------------------------------

def test_phase_summary_averages_each_phase_across_solves(store):
    session = store.start_session("solve")
    store.record_solve(session, "x", 20.0, [("cross", 2.0), ("f2l", 10.0)])
    store.record_solve(session, "y", 18.0, [("cross", 4.0), ("f2l", 8.0)])
    summary = phase_summary(store.splits())
    assert summary["cross"]["mean"] == pytest.approx(3.0)
    assert summary["cross"]["best"] == pytest.approx(2.0)
    assert summary["f2l"]["count"] == 2


def test_phase_summary_only_counts_solves_that_timed_that_phase(store):
    session = store.start_session("solve")
    store.record_solve(session, "x", 20.0, [("cross", 2.0), ("f2l", 10.0)])
    store.record_solve(session, "y", 3.0, [("cross", 3.0)])
    summary = phase_summary(store.splits())
    assert summary["cross"]["count"] == 2
    assert summary["f2l"]["count"] == 1


def test_solve_summary_reports_wca_averages(store):
    session = store.start_session("solve")
    for seconds in (20.0, 18.0, 22.0, 19.0, 21.0):
        store.record_solve(session, "x", seconds)
    summary = solve_summary(store.solves())
    assert summary["count"] == 5
    assert summary["best"] == pytest.approx(18.0)
    assert summary["ao5"] == pytest.approx(20.0)
    assert summary["ao12"] is None


# --- a rep's phase comes from its session -----------------------------------

def test_reps_can_be_read_back_one_phase_at_a_time(store):
    """A rep records its case and not its phase, because the session it belongs
    to already knows. Recovering it by joining beats storing it twice and
    letting the two disagree."""
    pll_session = store.start_session("drill", "PLL")
    oll_session = store.start_session("drill", "OLL")
    store.record_rep(pll_session, "T", "R U", 2.0)
    store.record_rep(oll_session, "OLL 27", "R U", 3.0)

    assert [r["case_id"] for r in store.reps(phase="PLL")] == ["T"]
    assert [r["case_id"] for r in store.reps(phase="OLL")] == ["OLL 27"]
    assert len(store.reps()) == 2


def test_a_rep_keeps_every_column_when_read_back_by_phase(store):
    session = store.start_session("drill", "OLL")
    store.record_rep(session, "OLL 27", "R U R'", 1.5, peeked=True)
    rep, = store.reps(phase="OLL")
    assert rep["scramble"] == "R U R'"
    assert rep["duration_ms"] == 1500
    assert rep["peeked"] == 1


def test_practised_cases_can_be_asked_for_by_phase(store):
    pll_session = store.start_session("drill", "PLL")
    oll_session = store.start_session("drill", "OLL")
    store.record_rep(pll_session, "T", "R U", 2.0)
    store.record_rep(oll_session, "OLL 27", "R U", 3.0)
    store.record_rep(oll_session, "OLL 21", "R U", 4.0)

    assert store.practised_case_ids("PLL") == ["T"]
    assert store.practised_case_ids("OLL") == ["OLL 21", "OLL 27"]
    assert store.practised_case_ids() == ["OLL 21", "OLL 27", "T"]


def test_a_phase_nobody_has_drilled_has_no_practised_cases(store):
    session = store.start_session("drill", "PLL")
    store.record_rep(session, "T", "R U", 2.0)
    assert store.practised_case_ids("OLL") == []
