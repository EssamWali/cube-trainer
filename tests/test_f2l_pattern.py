"""Reading an F2L pair off a cube state.

The measuring instrument, built before the thing it measures. The case data for
a phase is checked against the cube group rather than against its own
algorithms, which would be circular, so the reading has to exist and be trusted
first. See docs/adr/0002.

The ground truth here is derived twice over, from two directions that could
disagree. Once as arithmetic: every way one pair can sit, reduced under
upper-face adjustment. Once on a real cube: turn the slot's own triggers until
nothing new comes back, and count what was reached. Both have to say 42.
"""

import pytest

from cubetrainer.cases.pattern import (F2L_SLOTS, IN_SLOT, f2l_pair,
                                       is_cross_solved, is_f2l_state,
                                       is_slot_finished, pair_key)
from cubetrainer.cube import Cube

#: A pair put back in its slot with the edge the wrong way round. Both pieces
#: are out of the upper face, which is what makes it the case to test the last
#: layer against: nothing done up there can move them.
EDGE_FLIPPED_IN_SLOT = "R U R' U2 R U2 R' U F' U' F"

#: Turning the front-right slot without touching anything else. Every F2L case
#: for that slot is reachable with these and nothing else is.
TRIGGERS = ("U", "R U R'", "F' U' F")


# --- ground truth, derived here rather than imported ------------------------

def _adjusted(state):
    """The same pair after one upper-face turn.

    A U turn moves whatever is in the upper face on by one place and leaves a
    piece already in its slot alone. It turns those pieces too, but a piece
    carried round is not turned relative to itself, and orientation here is a
    fact about the piece rather than about the cube it is sitting on.
    """
    corner_place, twist, edge_place, flip = state

    def moved(place):
        return place if place == "slot" else (place + 1) % 4

    return (moved(corner_place), twist, moved(edge_place), flip)


def _f2l_classes():
    """Every class the pair can be in: 150 ways of sitting, reduced under AUF."""
    places = ("slot", 0, 1, 2, 3)
    seen, classes = set(), []
    for corner_place in places:
        for twist in range(3):
            for edge_place in places:
                for flip in range(2):
                    state = (corner_place, twist, edge_place, flip)
                    if state in seen:
                        continue
                    orbit, current = set(), state
                    for _ in range(4):
                        orbit.add(current)
                        current = _adjusted(current)
                    seen |= orbit
                    classes.append(frozenset(orbit))
    assert len(seen) == 150, "the ways of sitting were miscounted"
    return classes


F2L_CLASSES = _f2l_classes()
SOLVED_PAIR = ("slot", 0, "slot", 0)


def _reachable(slot="FR"):
    """Every reading the slot's own triggers can produce, and a cube showing it.

    Breadth-first until nothing new comes back. The triggers act on the pair the
    same way whatever the last layer is doing, so the readings close even though
    the cube states behind them never repeat.
    """
    first = Cube.solved()
    found = {f2l_pair(first, slot): first}
    frontier = [first]
    while frontier:
        following = []
        for state in frontier:
            for trigger in TRIGGERS:
                moved = state.apply(trigger)
                reading = f2l_pair(moved, slot)
                if reading not in found:
                    found[reading] = moved
                    following.append(moved)
        frontier = following
    return found


REACHABLE = _reachable()


# --- the two counts have to agree -------------------------------------------

def test_the_cube_group_permits_exactly_forty_two_f2l_classes():
    """Sanity check on the ground truth before anything is measured against it.

    41 is the number everybody quotes. It has to come from the group, because
    the point of this file is to be the thing that says whether a case list is
    complete, and a list checked against a number someone typed proves nothing.
    """
    assert len(F2L_CLASSES) == 42
    solved = [c for c in F2L_CLASSES if SOLVED_PAIR in c]
    assert len(solved) == 1
    assert len(F2L_CLASSES) - 1 == 41, "41 once the finished pair is set aside"


def test_the_reading_finds_exactly_those_classes_on_a_real_cube():
    """The other direction: turn the slot until nothing new appears."""
    assert len(REACHABLE) == 150, "not every way of sitting was reached"
    assert len({pair_key(state, "FR") for state in REACHABLE.values()}) == 42


def test_every_reachable_state_is_one_pair_from_finished():
    """The triggers are the claim that they only touch this slot, and the claim
    is checked rather than trusted."""
    for state in REACHABLE.values():
        assert is_cross_solved(state)
        for other in F2L_SLOTS:
            if other != "FR":
                assert is_slot_finished(state, other)


# --- what the reading says --------------------------------------------------

def test_a_solved_cube_has_every_pair_home():
    solved = Cube.solved()
    for slot in F2L_SLOTS:
        (corner_place, _), (edge_place, _) = f2l_pair(solved, slot)
        assert corner_place == IN_SLOT
        assert edge_place == IN_SLOT
        assert is_slot_finished(solved, slot)


def test_adjusting_the_upper_face_does_not_change_the_case():
    """What lets a drill hand the case out at a random angle."""
    state = Cube.solved().apply("R U R'")
    readings = {f2l_pair(state.apply(auf), "FR") for auf in ("", "U", "U2", "U'")}
    assert len(readings) == 4, "the angle is not visible in the reading at all"
    assert len({pair_key(state.apply(auf), "FR")
                for auf in ("", "U", "U2", "U'")}) == 1


def test_the_same_case_in_another_slot_reads_the_same():
    """Four slots, not four sets of cases. The reading is relative to the slot
    it is given, so the same case anywhere reads identically."""
    right = Cube.solved().apply("R U R'")
    back_left = Cube.solved().apply("L U L'")
    assert pair_key(right, "FR") == pair_key(back_left, "BL")


def test_a_mirrored_case_is_not_the_same_case():
    """Otherwise the reading would be quietly folding two cases into one, and a
    case list checked against it would come up short without saying so."""
    right = Cube.solved().apply("R U R'")
    mirrored = Cube.solved().apply("L' U' L")
    assert pair_key(right, "FR") != pair_key(mirrored, "FL")


def test_the_last_layer_is_not_part_of_the_question():
    """Which OLL case you are about to be left with is not a fact about the F2L
    case in front of you."""
    state = Cube.solved().apply(EDGE_FLIPPED_IN_SLOT)
    before = pair_key(state, "FR")
    for last_layer in ("R U R' U' R' F R2 U' R' U' R U R' F'",
                       "M2 U M2 U2 M2 U M2",
                       "R U R' U R U2 R'"):
        after = state.apply(last_layer)
        assert pair_key(after, "FR") == before
        assert is_f2l_state(after, "FR")


# --- what the reading refuses -----------------------------------------------

def test_reading_refuses_a_tipped_cube():
    """The same guard the last-layer readings have. Tip the cube and the cross
    is not on the bottom, so the slots are not where they are being looked for."""
    with pytest.raises(ValueError, match="cross"):
        f2l_pair(Cube.solved().apply("x"), "FR")


def test_reading_refuses_a_slot_that_does_not_exist():
    with pytest.raises(ValueError, match="slot"):
        f2l_pair(Cube.solved(), "FU")


def test_reading_refuses_a_pair_buried_in_another_slot():
    """Every piece has an angle round the vertical axis, so a reading that
    asked only for the angle would answer just as confidently for a piece in
    the slot next door and name a case that is not on the cube."""
    with pytest.raises(ValueError, match="upper face"):
        f2l_pair(Cube.solved().apply("R2"), "FR")   # the edge lands in BR
    with pytest.raises(ValueError, match="upper face"):
        f2l_pair(Cube.solved().apply("D"), "FR")    # the corner lands in BR


# --- whether a state is a case at all ---------------------------------------

def test_an_f2l_state_is_the_cross_and_three_slots_done_and_one_not():
    state = Cube.solved().apply("R U R'")
    assert is_f2l_state(state, "FR")
    for other in F2L_SLOTS:
        if other != "FR":
            assert not is_f2l_state(state, other), "that slot is finished"


def test_a_finished_pair_is_not_a_case():
    """There is no forty-second algorithm; a pair already in is done."""
    assert not is_f2l_state(Cube.solved(), "FR")


def test_a_cube_with_two_slots_out_is_not_a_case_for_either():
    """One pair from finished, or it is not an F2L case. A cuber with two slots
    open has a choice to make, which is not something a drill can hand out."""
    state = Cube.solved().apply("R U R'").apply("L' U' L")
    assert not is_f2l_state(state, "FR")
    assert not is_f2l_state(state, "FL")


def test_a_broken_cross_is_not_a_case():
    state = Cube.solved().apply("D")
    assert not is_f2l_state(state, "FR")


def test_the_cross_is_the_four_edges_and_not_the_corners():
    """A cuber who has just finished their cross is not holding a finished
    bottom face, and a reading that waited for one would never fire."""
    state = Cube.solved().apply("R U R'")
    assert is_cross_solved(state), "the cross survives an F2L pair coming out"
    assert not is_slot_finished(state, "FR")
    assert not is_cross_solved(Cube.solved().apply("F"))


def test_the_cross_has_to_be_on_the_bottom():
    assert not is_cross_solved(Cube.solved().apply("x"))
