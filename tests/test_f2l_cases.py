"""The 41 F2L cases.

The algorithms here are computed rather than transcribed, which changes what
these tests are worth. ADR 0003 sets out which of them still catch something and
which are now true by construction; the short version is that completeness,
family sizes, and "is this a genuine F2L state" still earn their keep, and "the
algorithm solves its own setup" no longer does.

The reading in `cases.pattern` is what everything here is measured against, and
its own ground truth is derived twice over in `test_f2l_pattern.py`.
"""

import pytest

from cubetrainer.cases import f2l, oll, pll
from cubetrainer.cases.pattern import (F2L_SLOTS, IN_SLOT, f2l_pair,
                                       is_f2l_state, is_slot_finished,
                                       pair_key)
from cubetrainer.cube import Cube, parse

SLOT = f2l.SLOT
TRIGGERS = ("U", "R U R'", "F' U' F")


def _state(case):
    return Cube.solved().apply(case.setup)


def _every_class():
    """Every F2L class the cube permits, reached by turning the slot itself.

    The same closure `test_f2l_pattern` counts, kept here as the thing the case
    list is measured against rather than a number copied between files.
    """
    first = Cube.solved()
    found = {f2l_pair(first, SLOT): first}
    frontier = [first]
    while frontier:
        following = []
        for state in frontier:
            for trigger in TRIGGERS:
                moved = state.apply(trigger)
                reading = f2l_pair(moved, SLOT)
                if reading not in found:
                    found[reading] = moved
                    following.append(moved)
        frontier = following
    return {pair_key(state, SLOT) for state in found.values()}


EVERY_CLASS = _every_class()
SOLVED_CLASS = pair_key(Cube.solved(), SLOT)


def _family_from_the_cube(case):
    """Which family the cube puts a case in, rather than what it was labelled."""
    (corner_place, _), (edge_place, _) = f2l_pair(_state(case), SLOT)
    if corner_place != IN_SLOT and edge_place != IN_SLOT:
        return f2l.PAIR_UP
    if corner_place != IN_SLOT:
        return f2l.CORNER_UP
    if edge_place != IN_SLOT:
        return f2l.EDGE_UP
    return f2l.BOTH_IN


# --- the list ---------------------------------------------------------------

def test_the_case_list_has_forty_one_entries_with_unique_ids():
    assert len(f2l.F2L_CASES) == 41
    assert len({case.id for case in f2l.F2L_CASES}) == 41


def test_every_id_says_which_phase_it_belongs_to():
    """History outlives the case list. An id of "7" would be a riddle once a
    fourth phase exists."""
    for case in f2l.F2L_CASES:
        assert case.id.startswith("F2L ")


def test_the_case_list_covers_every_class_exactly_once():
    """Completeness, not merely distinctness. A list of 41 cases with two the
    same and one missing passes every other test in this file."""
    covered = [pair_key(_state(case), SLOT) for case in f2l.F2L_CASES]
    assert len(set(covered)) == 41, "two cases are the same case"
    assert set(covered) == EVERY_CLASS - {SOLVED_CLASS}


def test_a_finished_pair_is_not_one_of_the_cases():
    """There is no forty-second algorithm."""
    assert SOLVED_CLASS not in {pair_key(_state(c), SLOT) for c in f2l.F2L_CASES}


def test_lookup_rejects_unknown_ids():
    with pytest.raises(KeyError, match="F2L"):
        f2l.get("F2L 99")


def test_every_case_has_its_own_description():
    """It is what tells two cases apart in the panel under the grid, so two
    cases sharing one is a case a cuber cannot look up."""
    described = [case.description for case in f2l.F2L_CASES]
    assert len(set(described)) == len(described)


# --- what the setups produce ------------------------------------------------

@pytest.mark.parametrize("case", f2l.F2L_CASES, ids=lambda c: c.id)
def test_setup_produces_a_genuine_f2l_case(case):
    state = _state(case)
    assert is_f2l_state(state, SLOT)
    for other in F2L_SLOTS:
        if other != SLOT:
            assert is_slot_finished(state, other), f"{other} was disturbed"


@pytest.mark.parametrize("case", f2l.F2L_CASES, ids=lambda c: c.id)
def test_no_scramble_asks_the_cuber_to_rotate_the_cube(case):
    """A scramble with a rotation in it leaves the cuber holding the cube
    differently from how they picked it up, and the slot they are drilling is
    then not the slot in front of them."""
    for move in parse(case.setup):
        assert move[0] in "URFDLB", case.id


@pytest.mark.parametrize("case", f2l.F2L_CASES, ids=lambda c: c.id)
def test_every_algorithm_leaves_the_cube_the_way_it_was_picked_up(case):
    """An algorithm ending in an unmatched regrip is ambiguous as data: which
    case it solves depends on how you were holding the cube when you finished."""
    assert Cube.solved().apply(case.setup).apply(case.algorithm) == Cube.solved()


@pytest.mark.parametrize("case", f2l.F2L_CASES, ids=lambda c: c.id)
def test_adjusting_the_upper_face_does_not_change_which_case_it_is(case):
    """What lets a drill randomise the angle without changing what it drills."""
    state = _state(case)
    for auf in ("U", "U2", "U'"):
        assert pair_key(state.apply(auf), SLOT) == pair_key(state, SLOT)


@pytest.mark.parametrize("case", f2l.F2L_CASES, ids=lambda c: c.id)
def test_algorithms_parse_and_are_a_sensible_length(case):
    moves = parse(case.algorithm)
    assert 3 <= len(moves) <= 12, f"{case.id} is {len(moves)} moves"


# --- families ---------------------------------------------------------------

@pytest.mark.parametrize("case", f2l.F2L_CASES, ids=lambda c: c.id)
def test_the_declared_family_is_the_one_the_cube_puts_the_case_in(case):
    assert case.group == _family_from_the_cube(case)


def test_the_families_have_the_sizes_the_enumeration_gives_them():
    """24 with both pieces up, 6 and 6 with one of each, and 5 with both in --
    six ways for both to be in the slot, less the one that is finished."""
    sizes = {group: len(cases) for group, cases in f2l.by_group().items()}
    assert sizes == {
        f2l.PAIR_UP: 24,
        f2l.CORNER_UP: 6,
        f2l.EDGE_UP: 6,
        f2l.BOTH_IN: 5,
    }
    assert sum(sizes.values()) == 41


def test_every_case_is_filed_in_exactly_one_family():
    filed = [case.id for group in f2l.GROUP_ORDER for case in f2l.by_group()[group]]
    assert sorted(filed) == sorted(case.id for case in f2l.F2L_CASES)


# --- the inverse declaration is a last-layer idea ---------------------------

def test_an_f2l_case_declares_no_inverse():
    """Undoing an insert takes the pair back out, which is a case but not
    something a cuber says about F2L."""
    for case in f2l.F2L_CASES:
        assert case.inverse is None


def test_a_case_with_no_inverse_is_not_treated_as_its_own():
    """Not saying is not the same as saying no. A case nobody asked the
    question of must not answer it by accident."""
    for case in f2l.F2L_CASES:
        assert not case.is_self_inverse


def test_the_last_layer_phases_still_declare_an_inverse():
    """Making the field optional must not quietly excuse the phases where the
    declaration is what catches a mistranscribed algorithm."""
    for catalogue in (pll.CATALOGUE, oll.CATALOGUE):
        for case in catalogue:
            assert case.inverse is not None, case.id
            assert catalogue.get(case.inverse) is not None
