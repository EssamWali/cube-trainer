"""Reading the last layer off a cube state.

A case is a fact about the cube, not about the algorithm that solves it. This
module is how the trainer answers "which case am I looking at" from a state
alone, which is what lets the case data be checked rather than trusted.
"""

from ..cube.state import CENTRES, Cube

CENTRE_U = CENTRES["U"]

#: Facelet indices of each U-layer corner slot, going clockwise from back-left.
CORNER_SLOTS = ((0, 36, 47), (2, 45, 11), (8, 9, 20), (6, 18, 38))
CORNER_SLOT_NAMES = ("UBL", "UBR", "UFR", "UFL")

#: Facelet indices of each U-layer edge slot, going clockwise from back.
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


def case_key(cube):
    """A value equal for two states iff they are the same case.

    Built by looking at the state from all sixteen equivalent angles and taking
    the smallest reading, so the answer does not depend on how the cube happens
    to be held or on where the U layer happens to be turned to.
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
