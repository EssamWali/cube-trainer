"""The 21 PLL cases.

The trainer's whole promise is "this scramble gives you exactly this case". The
setup sequence is the inverse of the algorithm, so checking the algorithm
against the setup would be circular and would prove nothing. Instead these
tests check the case data against facts derived from the cube group itself:
how many PLL cases can exist, and which of them are their own inverse. A typo
in an algorithm breaks one of those, because a mistyped algorithm lands on a
different case -- or on no valid case at all.
"""

import itertools

import pytest

from cubetrainer.cases import pll
from cubetrainer.cases.pattern import (
    case_key,
    is_first_two_layers_solved,
    is_last_layer_oriented,
    is_pll_state,
    u_layer_permutation,
)
from cubetrainer.cube import Cube, parse

IDENTITY = (0, 1, 2, 3)


# --- ground truth, derived here rather than imported ------------------------

def _sign(permutation):
    swaps = 0
    for i in range(len(permutation)):
        for j in range(i + 1, len(permutation)):
            if permutation[i] > permutation[j]:
                swaps ^= 1
    return swaps


def _inverse(permutation):
    result = [0] * len(permutation)
    for index, target in enumerate(permutation):
        result[target] = index
    return tuple(result)


SHIFT = (1, 2, 3, 0)


def _adjust_upper_face(state):
    corners, edges = state
    back = _inverse(SHIFT)
    return (tuple(corners[back[i]] for i in range(4)),
            tuple(edges[back[i]] for i in range(4)))


def _rotate_cube(state):
    corners, edges = state
    back = _inverse(SHIFT)
    return (tuple(SHIFT[corners[back[i]]] for i in range(4)),
            tuple(SHIFT[edges[back[i]]] for i in range(4)))


def _class_of(state):
    seen, frontier = {state}, [state]
    while frontier:
        current = frontier.pop()
        for transform in (_adjust_upper_face, _rotate_cube):
            nxt = transform(current)
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return frozenset(seen)


def _all_pll_classes():
    """Every last-layer permutation class the cube group permits."""
    permutations = list(itertools.permutations(range(4)))
    legal = [
        (corners, edges)
        for corners in permutations
        for edges in permutations
        if _sign(corners) == _sign(edges)  # a legal cube preserves parity
    ]
    classes = {_class_of(state) for state in legal}
    return {c for c in classes if (IDENTITY, IDENTITY) not in c}


PLL_CLASSES = _all_pll_classes()


# --- the tests --------------------------------------------------------------

def test_the_cube_group_permits_exactly_twenty_one_pll_cases():
    """Sanity check on the ground truth before anything is measured against it."""
    assert len(PLL_CLASSES) == 21


def test_the_case_list_has_twenty_one_entries_with_unique_ids():
    assert len(pll.PLL_CASES) == 21
    ids = [case.id for case in pll.PLL_CASES]
    assert len(set(ids)) == 21


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_setup_produces_a_genuine_last_layer_case(case):
    """F2L intact and the last layer oriented: the definition of a PLL state."""
    state = Cube.solved().apply(case.setup)
    assert is_first_two_layers_solved(state), f"{case.id} disturbs the first two layers"
    assert is_last_layer_oriented(state), f"{case.id} leaves the last layer unoriented"
    assert is_pll_state(state)


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_setup_is_not_already_solved(case):
    assert not Cube.solved().apply(case.setup).is_solved()


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_algorithm_solves_its_own_setup(case):
    assert Cube.solved().apply(case.setup).apply(case.algorithm).is_solved()


def test_every_case_is_distinct():
    keys = {case.id: case_key(Cube.solved().apply(case.setup)) for case in pll.PLL_CASES}
    collisions = {}
    for case_id, key in keys.items():
        collisions.setdefault(key, []).append(case_id)
    assert all(len(v) == 1 for v in collisions.values()), \
        f"cases coincide: {[v for v in collisions.values() if len(v) > 1]}"


def test_the_case_list_covers_every_pll_class_exactly_once():
    """Completeness, not just distinctness.

    Twenty-one distinct cases that happened to miss one real case and include
    one impossible one would pass a distinctness check. This will not.
    """
    covered = set()
    for case in pll.PLL_CASES:
        state = u_layer_permutation(Cube.solved().apply(case.setup))
        covered.add(_class_of(state))
    assert covered == PLL_CLASSES


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_declared_inverse_matches_the_actual_inverse(case):
    """The structural fact each case declares, checked against the cube.

    Seventeen PLLs undo themselves and four form two inverse pairs. Mislabel a
    case and this fails, because being self-inverse is a property of the case
    rather than of the name attached to it.
    """
    corners, edges = u_layer_permutation(Cube.solved().apply(case.setup))
    undone = _class_of((_inverse(corners), _inverse(edges)))
    partner = pll.get(case.inverse)
    expected = _class_of(u_layer_permutation(Cube.solved().apply(partner.setup)))
    assert undone == expected


def test_inverse_declarations_are_mutual():
    for case in pll.PLL_CASES:
        assert pll.get(case.inverse).inverse == case.id


def test_four_inverse_pairs_and_thirteen_self_inverse_cases():
    """Four PLLs come in pairs that undo each other; the other thirteen undo
    themselves. Which side of that line a case falls on is a property of the
    case, so a mislabelled algorithm shows up here."""
    paired = sorted(c.id for c in pll.PLL_CASES if not c.is_self_inverse)
    assert paired == ["Aa", "Ab", "Ga", "Gb", "Gc", "Gd", "Ua", "Ub"]
    assert len([c for c in pll.PLL_CASES if c.is_self_inverse]) == 13
    assert len(paired) + 13 == 21


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_adjusting_the_upper_face_does_not_change_the_case(case):
    """A case seen from a different angle is the same case.

    This is what lets a drill randomise the angle without changing what it
    claims to be drilling.
    """
    base = Cube.solved().apply(case.setup)
    for auf in ("U", "U2", "U'"):
        assert case_key(base.apply(auf)) == case_key(base)


def test_groups_have_their_canonical_sizes():
    sizes = {group: len(cases) for group, cases in pll.by_group().items()}
    assert sizes == {
        pll.EDGES_ONLY: 4,
        pll.CORNERS_ONLY: 3,
        pll.ADJACENT_SWAP: 10,
        pll.DIAGONAL_SWAP: 4,
    }
    assert sum(sizes.values()) == 21


def test_edge_only_cases_leave_every_corner_home():
    """The defining property of the group, checked rather than asserted by name."""
    for case in pll.by_group()[pll.EDGES_ONLY]:
        corners, _ = u_layer_permutation(Cube.solved().apply(case.setup))
        assert corners == IDENTITY, f"{case.id} moves a corner"


def test_corner_only_cases_leave_every_edge_home():
    for case in pll.by_group()[pll.CORNERS_ONLY]:
        _, edges = u_layer_permutation(Cube.solved().apply(case.setup))
        assert edges == IDENTITY, f"{case.id} moves an edge"


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_algorithms_parse_and_are_a_sensible_length(case):
    moves = parse(case.algorithm)
    assert 7 <= len(moves) <= 25, f"{case.id} is {len(moves)} moves"


def test_lookup_rejects_unknown_ids():
    with pytest.raises(KeyError):
        pll.get("Q")


def test_every_algorithm_leaves_the_cube_the_way_it_was_picked_up():
    """An algorithm ending in an unmatched regrip is ambiguous as data.

    Which case it solves then depends on how you happened to be holding the
    cube when you finished, so the trailing rotation has to be written down.
    """
    from cubetrainer.cube.state import CENTRES
    solved = Cube.solved()
    for case in pll.PLL_CASES:
        finished = solved.apply(case.algorithm)
        displaced = {
            face: finished.facelets[index]
            for face, index in CENTRES.items()
            if finished.facelets[index] != face
        }
        assert not displaced, f"{case.id} ends rotated: {displaced}"


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_no_scramble_asks_the_cuber_to_rotate_the_cube(case):
    assert not [m for m in parse(case.setup) if m[0] in "xyz"], case.setup


@pytest.mark.parametrize("case", pll.PLL_CASES, ids=lambda c: c.id)
def test_every_setup_leaves_the_last_layer_on_top(case):
    """Otherwise the diagram and the cube in your hands disagree."""
    from cubetrainer.cases.pattern import is_canonically_oriented
    assert is_canonically_oriented(Cube.solved().apply(case.setup))


def test_reading_the_last_layer_refuses_a_tipped_cube():
    """The bug this guard exists for: reading the top layer of a cube that has
    been tipped forwards returns a confident answer about the wrong layer."""
    from cubetrainer.cases.pattern import is_canonically_oriented
    tipped = Cube.solved().apply(pll.get("T").setup).apply("x")
    assert not is_canonically_oriented(tipped)
    with pytest.raises(ValueError, match="not on top"):
        u_layer_permutation(tipped)


def test_turning_the_cube_about_the_vertical_axis_is_still_readable():
    """A y rotation keeps the last layer on top, so it must still work."""
    turned = Cube.solved().apply(pll.get("T").setup).apply("y")
    assert case_key(turned) == case_key(Cube.solved().apply(pll.get("T").setup))
