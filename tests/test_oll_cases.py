"""Reading last-layer orientation, and the 57 OLL cases read with it.

The same discipline as the PLL tests, applied to orientation. The setup is the
inverse of the algorithm, so checking one against the other proves nothing.
What is checked instead is the case data against the cube group: how many
orientation classes can exist, which of them each case is, and which case
undoes which. A mistyped algorithm lands on a different class -- or on none --
and one of these fails.
"""

import itertools

import pytest

from cubetrainer.cases import oll
from cubetrainer.cases.pattern import (
    is_canonically_oriented,
    is_first_two_layers_solved,
    is_last_layer_oriented,
    is_oll_state,
    orientation_key,
    u_layer_orientation,
)
from cubetrainer.cube import Cube, parse
from cubetrainer.cube.state import CENTRES

SOLVED_ORIENTATION = ((0, 0, 0, 0), (0, 0, 0, 0))


# --- ground truth, derived here rather than imported ------------------------

def _turn_upper_face(state):
    """The reading after one upper-face turn: every piece moves on one slot."""
    twists, flips = state
    return (tuple(twists[i - 1] for i in range(4)),
            tuple(flips[i - 1] for i in range(4)))


def _class_of(state):
    seen, current = set(), state
    for _ in range(4):
        seen.add(current)
        current = _turn_upper_face(current)
    return frozenset(seen)


def _all_orientation_classes():
    """Every last-layer orientation the cube group permits.

    The corner twists sum to zero modulo three and the edge flips sum to zero
    modulo two; nothing else is reachable. Reduced under upper-face rotation,
    because a case turned to a different angle is the same case.
    """
    twists = [t for t in itertools.product(range(3), repeat=4) if sum(t) % 3 == 0]
    flips = [f for f in itertools.product(range(2), repeat=4) if sum(f) % 2 == 0]
    return {_class_of((t, f)) for t in twists for f in flips}


ORIENTATION_CLASSES = _all_orientation_classes()
UNSOLVED_CLASSES = {c for c in ORIENTATION_CLASSES if SOLVED_ORIENTATION not in c}


# --- the measuring instrument ----------------------------------------------

def test_the_cube_group_permits_exactly_fifty_eight_orientation_classes():
    """Sanity check on the ground truth before anything is measured against it.

    Fifty-eight including the solved last layer, which is the fifty-seven of
    OLL plus the case that needs no algorithm.
    """
    assert len(ORIENTATION_CLASSES) == 58
    assert len(UNSOLVED_CLASSES) == 57


def test_a_solved_cube_reads_as_wholly_oriented():
    assert u_layer_orientation(Cube.solved()) == SOLVED_ORIENTATION


def test_a_sune_reads_as_one_corner_home_and_three_twisted():
    """Sune leaves every edge oriented and three corners turned the same way."""
    state = Cube.solved().apply("R U R' U R U2 R'")
    twists, flips = u_layer_orientation(state)
    assert flips == (0, 0, 0, 0)
    assert sorted(twists) == [0, 1, 1, 1]


def test_a_twist_is_counted_the_same_way_whichever_slot_it_is_in():
    """Otherwise two states of the same case would not compare equal, and the
    whole reading would be worthless as a key."""
    state = Cube.solved().apply("R U R' U R U2 R'")
    twists, _ = u_layer_orientation(state)
    for auf in ("U", "U2", "U'"):
        turned, _ = u_layer_orientation(state.apply(auf))
        assert sorted(turned) == sorted(twists)


def test_adjusting_the_upper_face_does_not_change_the_case():
    state = Cube.solved().apply("R U R' U R U2 R'")
    for auf in ("U", "U2", "U'"):
        assert orientation_key(state.apply(auf)) == orientation_key(state)


def test_turning_the_cube_about_the_vertical_axis_does_not_change_the_case():
    """How the cuber happens to be holding it is not a fact about the case."""
    state = Cube.solved().apply("R U R' U R U2 R'")
    for rotation in ("y", "y2", "y'"):
        assert orientation_key(state.apply(rotation)) == orientation_key(state)


def test_reading_the_orientation_refuses_a_tipped_cube():
    """The same guard the permutation reading has: tip the cube forwards and
    the top layer is no longer the last layer, so a confident answer would be
    an answer about the wrong layer."""
    tipped = Cube.solved().apply("R U R' U R U2 R'").apply("x")
    with pytest.raises(ValueError, match="not on top"):
        u_layer_orientation(tipped)


def test_reading_the_orientation_refuses_a_cube_whose_last_layer_is_elsewhere():
    """A scrambled cube has no last layer to read; saying so beats guessing."""
    with pytest.raises(ValueError):
        u_layer_orientation(Cube.solved().apply("R U F D2 L B"))


def test_an_oll_state_is_the_first_two_layers_done_and_the_top_not_yet():
    state = Cube.solved().apply("R U2 R' U' R U' R'")
    assert is_first_two_layers_solved(state)
    assert not is_last_layer_oriented(state)
    assert is_oll_state(state)


def test_a_solved_cube_is_not_an_oll_case():
    """There is no fifty-eighth algorithm; a solved last layer is finished."""
    assert not is_oll_state(Cube.solved())


def test_a_permutation_case_is_not_an_oll_case():
    """Its last layer is already oriented, which is what OLL is for."""
    from cubetrainer.cases import pll
    state = Cube.solved().apply(pll.get("T").setup)
    assert not is_oll_state(state)


def test_a_cube_with_the_first_two_layers_broken_is_not_an_oll_case():
    assert not is_oll_state(Cube.solved().apply("R U F D2 L B"))


# --- the case data ----------------------------------------------------------

def _edge_shape(flips):
    """The group a state belongs to, read off the state rather than the label."""
    upright = [i for i in range(4) if flips[i] == 0]
    if len(upright) == 4:
        return oll.CROSS
    if not upright:
        return oll.DOT
    return oll.LINE if (upright[1] - upright[0]) % 4 == 2 else oll.L_SHAPE


def _setup_state(case):
    return Cube.solved().apply(case.setup)


def test_the_case_list_has_fifty_seven_entries_with_unique_ids():
    assert len(oll.OLL_CASES) == 57
    ids = [case.id for case in oll.OLL_CASES]
    assert len(set(ids)) == 57


def test_every_id_says_which_phase_it_belongs_to():
    """History outlives the case list. An id of "21" would be a riddle once a
    second phase exists; "OLL 21" answers itself."""
    for case in oll.OLL_CASES:
        assert case.id.startswith("OLL "), case.id


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_setup_produces_a_genuine_orientation_case(case):
    state = _setup_state(case)
    assert is_first_two_layers_solved(state), f"{case.id} disturbs the first two layers"
    assert not is_last_layer_oriented(state), f"{case.id} is already oriented"
    assert is_oll_state(state)


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_setup_is_not_already_solved(case):
    assert not _setup_state(case).is_solved()


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_algorithm_solves_its_own_setup(case):
    assert _setup_state(case).apply(case.algorithm).is_solved()


def test_the_case_list_covers_every_orientation_class_exactly_once():
    """Completeness, not merely distinctness.

    Fifty-seven distinct cases that missed one real class and included one
    impossible one would pass a distinctness check. This will not.
    """
    covered = [_class_of(u_layer_orientation(_setup_state(c))) for c in oll.OLL_CASES]
    assert len(set(covered)) == 57, "two cases are the same case"
    assert set(covered) == UNSOLVED_CLASSES


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_declared_inverse_matches_the_actual_inverse(case):
    """Undoing an orientation case means untwisting what it twisted, so the
    declaration is a fact about the cube and a mistranscribed algorithm breaks
    it."""
    twists, flips = u_layer_orientation(_setup_state(case))
    undone = _class_of((tuple((-t) % 3 for t in twists), flips))
    partner = oll.get(case.inverse)
    assert undone == _class_of(u_layer_orientation(_setup_state(partner)))


def test_inverse_declarations_are_mutual():
    for case in oll.OLL_CASES:
        assert oll.get(case.inverse).inverse == case.id


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_the_declared_group_is_the_shape_the_state_actually_has(case):
    """The group is checked against the edges, not against the name it was
    given, because a miscounted group is the likeliest data-entry error."""
    _, flips = u_layer_orientation(_setup_state(case))
    assert case.group == _edge_shape(flips)


def test_the_groups_have_the_sizes_the_cube_group_predicts():
    """8, 15, 27 and 7 fall out of the enumeration above rather than out of a
    list someone typed, so a case filed under the wrong shape shows up here."""
    sizes = {group: len(cases) for group, cases in oll.by_group().items()}
    assert sizes == {oll.DOT: 8, oll.LINE: 15, oll.L_SHAPE: 27, oll.CROSS: 7}
    assert sum(sizes.values()) == 57

    expected = {}
    for klass in UNSOLVED_CLASSES:
        _, flips = sorted(klass)[0]
        expected[_edge_shape(flips)] = expected.get(_edge_shape(flips), 0) + 1
    assert sizes == expected


def test_the_cross_group_is_the_one_with_every_edge_already_oriented():
    for case in oll.by_group()[oll.CROSS]:
        _, flips = u_layer_orientation(_setup_state(case))
        assert flips == (0, 0, 0, 0), f"{case.id} still has an edge to flip"


def test_the_dot_group_is_the_one_with_no_edge_oriented():
    for case in oll.by_group()[oll.DOT]:
        _, flips = u_layer_orientation(_setup_state(case))
        assert flips == (1, 1, 1, 1), f"{case.id} already has an edge up"


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_adjusting_the_upper_face_does_not_change_which_case_it_is(case):
    """What lets a drill randomise the angle without changing what it drills."""
    base = _setup_state(case)
    for auf in ("U", "U2", "U'"):
        assert orientation_key(base.apply(auf)) == orientation_key(base)


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_every_algorithm_leaves_the_cube_the_way_it_was_picked_up(case):
    """An algorithm ending in an unmatched regrip is ambiguous as data: which
    case it solves depends on how you were holding the cube when you finished,
    and that exact defect was found twice in the PLL data."""
    finished = Cube.solved().apply(case.algorithm)
    displaced = {face: finished.facelets[index]
                 for face, index in CENTRES.items()
                 if finished.facelets[index] != face}
    assert not displaced, f"{case.id} ends rotated: {displaced}"


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_no_scramble_asks_the_cuber_to_rotate_the_cube(case):
    assert not [m for m in parse(case.setup) if m[0] in "xyz"], case.setup


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_every_setup_leaves_the_last_layer_on_top(case):
    """Otherwise the diagram and the cube in your hands disagree."""
    assert is_canonically_oriented(_setup_state(case))


@pytest.mark.parametrize("case", oll.OLL_CASES, ids=lambda c: c.id)
def test_algorithms_parse_and_are_a_sensible_length(case):
    moves = parse(case.algorithm)
    assert 6 <= len(moves) <= 26, f"{case.id} is {len(moves)} moves"


def test_lookup_rejects_unknown_ids():
    with pytest.raises(KeyError, match="OLL"):
        oll.get("OLL 58")
