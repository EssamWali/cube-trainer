"""The move engine.

These tests exist because the whole application rests on one claim: that a
setup sequence produces exactly the state it says it does. If the engine turns
a face the wrong way, every scramble the trainer hands out is wrong and nothing
downstream can detect it.
"""

import random

import pytest

from cubetrainer.cube import Cube, NotationError, invert, move_count, parse
from cubetrainer.cube.geometry import TABLES

FACES = ["U", "R", "F", "D", "L", "B"]

# The six tables as they were hand-written in the original cube.py, kept here as
# an independent witness: geometry.py derives its tables from 3D reasoning, and
# these were derived by working out index swaps by hand. Agreement between two
# unrelated derivations is worth more than either alone.
LEGACY = {
    "U": (6,3,0,7,4,1,8,5,2,45,46,47,12,13,14,15,16,17,9,10,11,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,18,19,20,39,40,41,42,43,44,36,37,38,48,49,50,51,52,53),
    "R": (0,1,20,3,4,23,6,7,26,15,12,9,16,13,10,17,14,11,18,19,29,21,22,32,24,25,35,27,28,51,30,31,48,33,34,45,36,37,38,39,40,41,42,43,44,8,46,47,5,49,50,2,52,53),
    "F": (0,1,2,3,4,5,44,41,38,6,10,11,7,13,14,8,16,17,24,21,18,25,22,19,26,23,20,15,12,9,30,31,32,33,34,35,36,37,27,39,40,28,42,43,29,45,46,47,48,49,50,51,52,53),
    "D": (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,24,25,26,18,19,20,21,22,23,42,43,44,33,30,27,34,31,28,35,32,29,36,37,38,39,40,41,51,52,53,45,46,47,48,49,50,15,16,17),
    "L": (53,1,2,50,4,5,47,7,8,9,10,11,12,13,14,15,16,17,0,19,20,3,22,23,6,25,26,18,28,29,21,31,32,24,34,35,42,39,36,43,40,37,44,41,38,45,46,33,48,49,30,51,52,27),
    "B": (11,14,17,3,4,5,6,7,8,9,10,35,12,13,34,15,16,33,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,36,39,42,2,37,38,1,40,41,0,43,44,51,48,45,52,49,46,53,50,47),
}


@pytest.mark.parametrize("face", FACES)
def test_geometric_tables_match_hand_derived_tables(face):
    assert TABLES[face] == LEGACY[face]


@pytest.mark.parametrize("name", sorted(TABLES))
def test_every_move_is_a_permutation_of_order_four(name):
    assert sorted(TABLES[name]) == list(range(54))
    cube = Cube.solved().apply(f"{name} {name} {name} {name}")
    assert cube == Cube.solved()


@pytest.mark.parametrize("face", FACES)
def test_a_single_face_turn_moves_exactly_twenty_stickers(face):
    """Nine on the face, twelve on the sides, minus the centre that stays put."""
    turned = Cube.solved().apply(face)
    moved = sum(1 for i in range(54) if turned.facelets[i] != Cube.solved().facelets[i])
    # Colours repeat, so count displaced index slots via the table instead.
    displaced = sum(1 for i in range(54) if TABLES[face][i] != i)
    assert displaced == 20
    assert moved > 0


def test_sexy_move_has_order_six():
    cube = Cube.solved()
    for repeat in range(1, 6):
        cube = cube.apply("R U R' U'")
        assert not cube.is_solved(), f"returned to solved after {repeat} repetitions"
    assert cube.apply("R U R' U'").is_solved()


def test_t_perm_is_its_own_inverse():
    t_perm = "R U R' U' R' F R2 U' R' U' R U R' F'"
    assert Cube.solved().apply(t_perm).apply(t_perm).is_solved()


def test_random_sequences_round_trip_through_invert():
    rng = random.Random(20260826)
    for _ in range(200):
        seq = [
            rng.choice(FACES) + rng.choice(["", "'", "2"])
            for _ in range(rng.randint(1, 25))
        ]
        scrambled = Cube.solved().apply(seq)
        assert scrambled.apply(invert(seq)) == Cube.solved()


def test_whole_cube_rotation_leaves_the_cube_solved():
    for rotation in ("x", "y", "z", "x y z", "y2 x'"):
        assert Cube.solved().apply(rotation).is_solved()


def test_rotation_relabels_the_faces_it_turns_past():
    """After y, the layer that was L is where B now is.

    This is the property everything about case matching depends on, so it is
    checked directly rather than trusted.
    """
    rng = random.Random(7)
    scramble = [rng.choice(FACES) + rng.choice(["", "'", "2"]) for _ in range(15)]
    start = Cube.solved().apply(scramble)
    for rotated_move, original_move in (("B", "L"), ("F", "R"), ("L", "F"), ("R", "B")):
        assert start.apply("y").apply(rotated_move) == start.apply(original_move).apply("y")


def test_wide_turn_equals_face_plus_slice():
    rng = random.Random(11)
    scramble = [rng.choice(FACES) + rng.choice(["", "'", "2"]) for _ in range(15)]
    start = Cube.solved().apply(scramble)
    assert start.apply("r") == start.apply("R M'")
    assert start.apply("u") == start.apply("U E'")
    assert start.apply("f") == start.apply("F S")


def test_is_solved_accepts_a_rotated_but_solved_cube():
    assert Cube.solved().apply("y x2 z'").is_solved()
    assert not Cube.solved().apply("R").is_solved()


def test_kociemba_agrees_with_this_engine():
    """Cross-validation against an unrelated solver implementation.

    If our move semantics disagreed with kociemba's in any way, its solution
    would not solve our cube. This checks the entire engine end to end against
    software that knows nothing about our code.
    """
    kociemba = pytest.importorskip("kociemba")
    rng = random.Random(1729)
    for _ in range(8):
        scramble = []
        last = None
        for _ in range(25):
            face = rng.choice([f for f in FACES if f != last])
            last = face
            scramble.append(face + rng.choice(["", "'", "2"]))
        scrambled = Cube.solved().apply(scramble)
        solution = kociemba.solve(scrambled.to_kociemba())
        assert scrambled.apply(solution).is_solved()


def test_parse_rejects_unknown_moves():
    with pytest.raises(NotationError):
        parse("R U Q")
    with pytest.raises(NotationError):
        parse("R U R'U'")


def test_parse_accepts_common_notation_variants():
    assert parse("(R U R') U'") == ["R", "U", "R'", "U'"]
    assert parse("Rw Uw2 Lw'") == ["r", "u2", "l'"]
    assert parse("R U R’") == ["R", "U", "R'"]


def test_move_count_ignores_rotations_in_half_turn_metric():
    assert move_count("R U2 R' y F") == 4
    assert move_count("R U2 R'", metric="qtm") == 4


ORIENTATIONS = tuple(
    f"{tip} {' '.join(['y'] * spin)}".strip()
    for tip in ("", "x", "x2", "x'", "z", "z'")
    for spin in range(4)
)


def _same_up_to_rotation(first, second):
    return any(second.apply(view) == first for view in ORIENTATIONS)


def test_derotate_removes_every_rotation():
    from cubetrainer.cube.notation import derotate
    for sequence in ("y R U R'", "x' L' U L D' x", "R U y2 F' z L", "R U R'"):
        assert not [m for m in derotate(sequence) if m[0] in "xyz"], sequence


def test_derotate_preserves_the_state_up_to_how_the_cube_is_held():
    from cubetrainer.cube.notation import derotate
    rng = random.Random(31337)
    for _ in range(60):
        sequence = []
        for _ in range(rng.randint(1, 14)):
            if rng.random() < 0.25:
                sequence.append(rng.choice(["x", "y", "z"]) + rng.choice(["", "'", "2"]))
            else:
                sequence.append(rng.choice(FACES) + rng.choice(["", "'", "2"]))
        original = Cube.solved().apply(sequence)
        rewritten = Cube.solved().apply(derotate(sequence))
        assert _same_up_to_rotation(original, rewritten), " ".join(sequence)


def test_derotate_leaves_a_rotationless_sequence_alone():
    from cubetrainer.cube.notation import derotate
    assert derotate("R U R' U'") == ["R", "U", "R'", "U'"]


def test_there_are_twenty_four_ways_to_hold_a_cube():
    """Guards the helper above: a duplicate orientation would weaken the test."""
    assert len({Cube.solved().apply("R").apply(v).facelets for v in ORIENTATIONS}) == 24
