"""Turning a case into a scramble the cuber can apply.

Every scramble starts from a solved cube, which is what makes the trainer's
promise checkable: apply this and you are holding exactly that case. The cost
is that a fumbled algorithm leaves the cube somewhere the trainer cannot
follow, so the drill has to ask the cuber to reset.
"""

import random

from ..cube.notation import format_sequence, simplify

AUF_CHOICES = ("", "U", "U2", "U'")


def scramble_for(case, rng=None, randomise_angle=True):
    """The sequence that leaves a solved cube showing `case`.

    With `randomise_angle`, a random upper-face adjustment is appended so the
    case is met from one of its four angles rather than always the textbook
    one. Recognising a case from every angle is a separate skill from executing
    it, and drilling only the canonical angle never trains it.
    """
    rng = rng or random
    moves = list(simplify(case.setup))
    if randomise_angle:
        auf = rng.choice(AUF_CHOICES)
        if auf:
            moves = simplify(moves + [auf])
    return format_sequence(moves)


def random_scramble(rng=None, length=None):
    """A plain random-move scramble, for practising the cross.

    Not a random-state scramble: this is the classic random-move generator,
    which is what a cross drill needs and is honest about being.
    """
    rng = rng or random
    faces = ["R", "U", "L", "F", "D", "B"]
    modifiers = ["", "'", "2"]
    length = length or rng.randint(20, 25)
    moves = []
    last = None
    for _ in range(length):
        choices = [f for f in faces if f != last]
        face = rng.choice(choices)
        last = face
        moves.append(face + rng.choice(modifiers))
    return format_sequence(moves)
