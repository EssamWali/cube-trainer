"""Reading the last layer off a cube state.

A case is a fact about the cube, not about the algorithm that solves it. This
module is how the trainer answers "which case am I looking at" from a state
alone, which is what lets the case data be checked rather than trusted.
"""

from ..cube.state import CENTRES, Cube

CENTRE_U = CENTRES["U"]

#: Facelet indices of each U-layer corner slot, going clockwise from back-left.
#: Within a slot the upper-face sticker comes first, then the two side stickers
#: in clockwise order seen from above. That ordering is what makes a twist a
#: number rather than a description: the U-coloured sticker sits at index 0, 1
#: or 2, and the count means the same thing in every slot.
CORNER_SLOTS = ((0, 36, 47), (2, 45, 11), (8, 9, 20), (6, 18, 38))
CORNER_SLOT_NAMES = ("UBL", "UBR", "UFR", "UFL")

#: Facelet indices of each U-layer edge slot, going clockwise from back. Upper
#: face first here too, so a flipped edge reads as 1.
EDGE_SLOTS = ((1, 46), (5, 10), (7, 19), (3, 37))
EDGE_SLOT_NAMES = ("UB", "UR", "UF", "UL")

_CORNER_HOMES = {frozenset(s): i for i, s in enumerate([{"U", "L", "B"}, {"U", "B", "R"}, {"U", "R", "F"}, {"U", "F", "L"}])}
_EDGE_HOMES = {frozenset(s): i for i, s in enumerate([{"U", "B"}, {"U", "R"}, {"U", "F"}, {"U", "L"}])}

#: The 16 ways of looking at the same case: four U-layer adjustments, times
#: four whole-cube rotations. A case is the same case seen from any of them.
_VIEWS = tuple(
    " ".join(["U"] * turns + ["y"] * rotations)
    for turns in range(4)
    for rotations in range(4)
)


def is_canonically_oriented(cube):
    """True when the last layer is the layer on top.

    Colour labels are read relative to the centres, so a cube turned about the
    vertical axis reads correctly either way. Tipping it forwards or sideways
    is different: the last layer is then not the top layer at all, and reading
    the top layer would answer a question nobody asked.
    """
    return cube.facelets[CENTRE_U] == "U"


def u_layer_permutation(cube):
    """Where each U-layer piece belongs.

    Returns ``(corners, edges)``, where ``corners[i]`` is the home slot of the
    piece currently sitting in slot ``i``.
    """
    if not is_canonically_oriented(cube):
        raise ValueError(
            "the last layer is not on top; derotate the sequence first"
        )
    face_of = cube.orientation()
    corners = []
    for slot in CORNER_SLOTS:
        colours = frozenset(face_of[cube.facelets[i]] for i in slot)
        if colours not in _CORNER_HOMES:
            raise ValueError(f"slot {slot} does not hold a U-layer corner")
        corners.append(_CORNER_HOMES[colours])
    edges = []
    for slot in EDGE_SLOTS:
        colours = frozenset(face_of[cube.facelets[i]] for i in slot)
        if colours not in _EDGE_HOMES:
            raise ValueError(f"slot {slot} does not hold a U-layer edge")
        edges.append(_EDGE_HOMES[colours])
    return tuple(corners), tuple(edges)


def u_layer_cycles(cube):
    """Where each U-layer piece travels once the upper face has been adjusted.

    `u_layer_permutation` answers where every piece belongs, which is the whole
    truth about the state and the wrong reading to draw. A T perm met a quarter
    turn round has no piece at home, so that reading calls for seven arrows
    over a case that moves four pieces, and what the cuber is shown stops
    looking like the case they are learning.

    The AUF is what the extra arrows are, so it is divided out. The cuber
    adjusts the upper face before they start; this is what is left to do once
    they have, still read at the angle they are holding the cube now.

    Which of the four adjustments is taken is decided by what a cuber is
    taught, in this order: fewest pieces travelling, then the shortest longest
    cycle, then fewest corners travelling. The middle one is the G perms. Every
    adjustment moves six of their pieces, but one shows two corners trading and
    four edges going round, and the other shows corners and edges each cycling
    in threes -- which is the G perms, and is the reason they are a family. Read
    the other way a G perm wears a corner swap it does not have, which is the
    one thing a cuber must not see on it.
    """
    reading = u_layer_permutation(cube)

    def adjusted(auf):
        return tuple(tuple((home - auf) % 4 for home in permutation)
                     for permutation in reading)

    def travelling(permutation):
        return sum(1 for slot, home in enumerate(permutation) if slot != home)

    def longest(permutation):
        return max(cycle_structure(permutation), default=0)

    def taught_shape(candidate):
        corners, edges = candidate
        return (travelling(corners) + travelling(edges),
                max(longest(corners), longest(edges)),
                travelling(corners), candidate)

    return min((adjusted(auf) for auf in range(4)), key=taught_shape)


def u_layer_orientation(cube):
    """How each U-layer piece is turned.

    Returns ``(twists, flips)``. ``twists[i]`` is where the upper-face colour
    sits on the corner in slot ``i`` -- 0 on top, 1 or 2 a third of a turn
    round -- and ``flips[i]`` is 1 when the edge there shows its upper-face
    colour on the side instead of the top.

    This is orientation only. Which piece is in which slot is the permutation
    reading's question, and answering both at once would make two cases that
    OLL treats as one compare unequal.
    """
    if not is_canonically_oriented(cube):
        raise ValueError(
            "the last layer is not on top; derotate the sequence first"
        )
    face_of = cube.orientation()

    def turned(slot, kind):
        faces = [face_of[cube.facelets[i]] for i in slot]
        if "U" not in faces:
            raise ValueError(f"slot {slot} does not hold a U-layer {kind}")
        return faces.index("U")

    return (tuple(turned(slot, "corner") for slot in CORNER_SLOTS),
            tuple(turned(slot, "edge") for slot in EDGE_SLOTS))


def orientation_key(cube):
    """A value equal for two states iff they are the same orientation case.

    The counterpart of `case_key`, read from the same sixteen angles, so the
    answer survives both an upper-face adjustment and a cuber who turned the
    whole cube round before looking.
    """
    return min(u_layer_orientation(cube.apply(view)) for view in _VIEWS)


def is_last_layer_oriented(cube):
    """True when every U-layer sticker on top shows the U colour."""
    up = cube.facelets[4]
    return all(cube.facelets[i] == up for i in range(9))


def is_first_two_layers_solved(cube):
    """True when everything below the last layer is finished.

    That is the precondition for a state to be a PLL case at all, and it is
    what distinguishes a real last-layer case from a cube that merely happens
    to have some pieces in place.
    """
    face_of = cube.orientation()
    for face in "RFDLB":
        base = "URFDLB".index(face) * 9
        centre = cube.facelets[base + 4]
        # Skip the top row of the side faces; that belongs to the last layer.
        cells = range(9) if face == "D" else range(3, 9)
        if any(cube.facelets[base + i] != centre for i in cells):
            return False
    return True


def is_pll_state(cube):
    """True when the cube is solved except for permuting the last layer."""
    return (is_canonically_oriented(cube)
            and is_first_two_layers_solved(cube)
            and is_last_layer_oriented(cube))


def is_oll_state(cube):
    """True when the first two layers are done and the last layer is not.

    The precondition for a state to be an OLL case: something is left to
    orient. A solved last layer is not the fifty-eighth case, it is finished.
    """
    return (is_canonically_oriented(cube)
            and is_first_two_layers_solved(cube)
            and not is_last_layer_oriented(cube))


def case_key(cube):
    """A value equal for two states iff they are the same permutation case.

    The permutation reading's answer, as `orientation_key` is the orientation
    reading's. Built by looking at the state from all sixteen equivalent angles
    and taking the smallest reading, so the answer does not depend on how the
    cube happens to be held or on where the U layer happens to be turned to.
    """
    return min(u_layer_permutation(cube.apply(view)) for view in _VIEWS)


def cycle_structure(permutation):
    """Sorted lengths of the permutation's non-trivial cycles."""
    seen = set()
    cycles = []
    for start in range(len(permutation)):
        if start in seen:
            continue
        length, current = 0, start
        while current not in seen:
            seen.add(current)
            current = permutation[current]
            length += 1
        if length > 1:
            cycles.append(length)
    return tuple(sorted(cycles, reverse=True))


def compose(outer, inner):
    """The permutation applying `inner` and then `outer`."""
    return tuple(outer[inner[i]] for i in range(len(inner)))


def invert_permutation(permutation):
    result = [0] * len(permutation)
    for i, target in enumerate(permutation):
        result[target] = i
    return tuple(result)


def permutation_order(permutation):
    """How many times the permutation must repeat to return to the start."""
    identity = tuple(range(len(permutation)))
    current, order = permutation, 1
    while current != identity:
        current = compose(current, permutation)
        order += 1
    return order
