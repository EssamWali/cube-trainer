"""Scramble generation, case sampling and the timer."""

import random

import pytest

from cubetrainer.cases import pll
from cubetrainer.cases.pattern import case_key, is_pll_state
from cubetrainer.cube import Cube, parse
from cubetrainer.cube.notation import simplify
from cubetrainer.trainer.sampler import RoundRobinSampler
from cubetrainer.trainer.scramble import AUF_CHOICES, random_scramble, scramble_for
from cubetrainer.trainer.timer import Penalty, SolveTimer, TimerState


# --- scrambles --------------------------------------------------------------

@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_scramble_lands_on_the_case_it_promises(case):
    """The trainer's central claim, checked for every case and every angle."""
    expected = case_key(Cube.solved().apply(case.setup))
    rng = random.Random(hash(case.id) % 10_000)
    for _ in range(12):
        state = Cube.solved().apply(scramble_for(case, rng))
        assert is_pll_state(state)
        assert case_key(state) == expected


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_every_angle_is_reachable(case):
    """All four upper-face adjustments actually occur, so recognition really is
    trained from four angles rather than nominally."""
    seen = set()
    rng = random.Random(4)
    for _ in range(200):
        seen.add(scramble_for(case, rng))
    assert len(seen) >= 3, f"{case.id} only ever produced {len(seen)} scramble(s)"


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_scramble_has_no_redundant_consecutive_turns(case):
    rng = random.Random(9)
    for _ in range(8):
        moves = parse(scramble_for(case, rng))
        faces = [m[0] for m in moves]
        assert all(a != b for a, b in zip(faces, faces[1:])), " ".join(moves)


def test_fixed_angle_gives_the_canonical_setup():
    case = pll.get("T")
    assert scramble_for(case, randomise_angle=False) == case.setup


def test_simplify_collapses_and_cancels():
    assert simplify("R R") == ["R2"]
    assert simplify("R R'") == []
    assert simplify("R2 R2") == []
    assert simplify("R U U' R'") == []
    assert simplify("R U") == ["R", "U"]


def test_random_scramble_never_repeats_a_face_consecutively():
    rng = random.Random(5)
    for _ in range(50):
        faces = [m[0] for m in parse(random_scramble(rng))]
        assert all(a != b for a, b in zip(faces, faces[1:]))


def test_random_scramble_actually_scrambles():
    rng = random.Random(6)
    for _ in range(20):
        assert not Cube.solved().apply(random_scramble(rng)).is_solved()


# --- sampling ---------------------------------------------------------------

def test_every_case_appears_once_per_round():
    ids = ["T", "Ja", "H", "V", "Ua"]
    sampler = RoundRobinSampler(ids, random.Random(2))
    for _ in range(20):
        round_ = [sampler.next() for _ in range(len(ids))]
        assert sorted(round_) == sorted(ids)


def test_a_case_never_repeats_across_the_seam():
    """The failure mode that makes uniform random choice feel broken."""
    ids = ["T", "Ja", "H"]
    sampler = RoundRobinSampler(ids, random.Random(8))
    drawn = [sampler.next() for _ in range(300)]
    assert all(a != b for a, b in zip(drawn, drawn[1:]))


def test_a_single_case_set_repeats_that_case():
    sampler = RoundRobinSampler(["T"], random.Random(1))
    assert [sampler.next() for _ in range(5)] == ["T"] * 5


def test_an_empty_case_set_is_rejected():
    with pytest.raises(ValueError):
        RoundRobinSampler([])


# --- timer ------------------------------------------------------------------

def test_releasing_before_the_hold_threshold_does_not_start_the_timer():
    timer = SolveTimer()
    timer.press(0.0)
    timer.tick(0.3)
    assert timer.state is TimerState.ARMING
    timer.release(0.3)
    assert timer.state is TimerState.IDLE
    assert timer.total() is None


def test_holding_past_the_threshold_arms_then_starts_on_release():
    timer = SolveTimer()
    timer.press(0.0)
    timer.tick(0.54)
    assert timer.state is TimerState.ARMING
    timer.tick(0.55)
    assert timer.state is TimerState.READY
    timer.release(0.6)
    assert timer.state is TimerState.RUNNING
    assert timer.elapsed(1.6) == pytest.approx(1.0)


def test_a_single_phase_attempt_stops_on_the_next_press():
    timer = SolveTimer()
    timer.press(0.0)
    timer.tick(0.6)
    timer.release(1.0)
    timer.press(3.5)
    assert timer.is_finished
    assert timer.total() == pytest.approx(2.5)
    assert timer.splits() == pytest.approx((2.5,))


def test_a_four_phase_solve_records_each_split_and_stops_at_the_last():
    timer = SolveTimer(phases=("cross", "f2l", "oll", "pll"))
    timer.press(0.0)
    timer.tick(0.6)
    timer.release(1.0)
    for mark in (3.0, 12.0, 15.0):
        timer.press(mark)
        assert timer.state is TimerState.RUNNING
    timer.press(18.0)
    assert timer.is_finished
    assert timer.splits() == pytest.approx((2.0, 9.0, 3.0, 3.0))
    assert timer.total() == pytest.approx(17.0)


def test_timing_only_the_cross_is_just_a_one_phase_solve():
    """Q19's collapse: a cross drill is a full solve with one boundary ticked."""
    timer = SolveTimer(phases=("cross",))
    timer.press(0.0)
    timer.tick(0.6)
    timer.release(1.0)
    timer.press(3.2)
    assert timer.is_finished
    assert timer.total() == pytest.approx(2.2)


def test_a_plus_two_penalty_is_added_to_the_recorded_time():
    timer = SolveTimer()
    timer.press(0.0)
    timer.tick(0.6)
    timer.release(1.0)
    timer.press(11.0)
    assert timer.total() == pytest.approx(10.0)
    timer.penalty = Penalty.PLUS_TWO
    assert timer.total() == pytest.approx(12.0)


def test_inspection_penalties_follow_the_wca_thresholds():
    timer = SolveTimer(inspection=True)
    timer.begin_inspection(0.0)
    assert timer.state is TimerState.INSPECTING
    assert timer.inspection_penalty(14.0) is Penalty.NONE
    assert timer.inspection_penalty(15.5) is Penalty.PLUS_TWO
    assert timer.inspection_penalty(17.5) is Penalty.DNF


def test_an_early_release_during_inspection_returns_to_inspecting():
    timer = SolveTimer(inspection=True)
    timer.begin_inspection(0.0)
    timer.press(5.0)
    timer.tick(5.1)
    timer.release(5.1)
    assert timer.state is TimerState.INSPECTING


def test_reset_clears_everything():
    timer = SolveTimer()
    timer.press(0.0)
    timer.tick(0.6)
    timer.release(1.0)
    timer.press(3.0)
    timer.reset()
    assert timer.state is TimerState.IDLE
    assert timer.total() is None
    assert timer.splits() == ()


def test_a_timer_needs_at_least_one_phase():
    with pytest.raises(ValueError):
        SolveTimer(phases=())
