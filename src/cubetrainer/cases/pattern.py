"""Reading the last layer off a cube state.

A case is a fact about the cube, not about the algorithm that solves it. This
module is how the trainer answers "which case am I looking at" from a state
alone, which is what lets the case data be checked rather than trusted.
"""

from ..cube.geometry import FACE_BASE, FACE_ORDER, POSITIONS
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


# --- the first two layers ---------------------------------------------------
#
# A last-layer case is about one layer, and the tables above describe it slot by
# slot. An F2L case is about one corner-edge pair and the slot it belongs in,
# which is half in the layer those tables describe and half underneath it, so it
# is read from the geometry the engine is already built on rather than from a
# second set of hand-written indices.

#: The four slots the first two layers are built from, named for the faces they
#: sit between. Reading takes one: they are the same cases seen from a different
#: side of the cube, and a reading that assumed front-right would quietly only
#: work there.
F2L_SLOTS = ("FR", "FL", "BL", "BR")

#: Where a piece of the pair is. The four upper-face places are numbered
#: clockwise from the one above its own slot, so a U turn adds one to each.
IN_SLOT = 4

#: Which way a piece is turned, said as the direction its anchor sticker faces:
#: up, down, or one of the four sides, numbered like the places above.
FACING_UP = 0
FACING_DOWN = 1
FACING_SIDE = 2


def _cubie_of(index):
    """The little cube a sticker belongs to.

    A sticker sits on a face plane, three units out; the piece it is stuck to
    sits two units out. Pulling the one coordinate in is the whole difference,
    and it is what lets three stickers be recognised as one corner.
    """
    return tuple(2 * (c > 0) - 2 * (c < 0) if abs(c) == 3 else c
                 for c in POSITIONS[index])


def _eighth_of(point):
    """Where a point stands round the vertical axis, in eighths of a turn.

    Corners of a layer land on the odd eighths and edges on the even ones,
    which is what lets one number order both. A U turn adds two.
    """
    x, z = (2 * (v > 0) - 2 * (v < 0) for v in (point[0], point[2]))
    return {(2, 0): 0, (2, 2): 1, (0, 2): 2, (-2, 2): 3, (-2, 0): 4,
            (-2, -2): 5, (0, -2): 6, (2, -2): 7}[(x, z)]


_STICKERS_ON = {}
for _index in range(54):
    _STICKERS_ON.setdefault(_cubie_of(_index), []).append(_index)

_NORMAL_OF = {face: tuple(c // 3 for c in POSITIONS[FACE_BASE[face] + 4])
              for face in FACE_ORDER}


def _cubie_for(faces):
    """The piece that meets the given faces: a corner for three, an edge for two."""
    return tuple(2 * sum(_NORMAL_OF[face][axis] for face in faces)
                 for axis in range(3))


_SLOT_PIECES = {
    slot: (_cubie_for(("D",) + tuple(slot)), _cubie_for(tuple(slot)))
    for slot in F2L_SLOTS
}


def _place_of(cubie, slot):
    """Where a piece stands relative to `slot`: a numbered upper-face place,
    IN_SLOT when it is already home, or None when it is somewhere an F2L case
    cannot have put it.

    The last is not a formality. Every piece has an angle round the vertical
    axis, so asking only for the angle answers just as confidently for a piece
    buried in the slot next door, and the reading would name a case that is not
    on the cube.
    """
    corner, edge = _SLOT_PIECES[slot]
    if cubie in (corner, edge):
        return IN_SLOT
    if cubie[1] != 2:
        return None
    return ((_eighth_of(cubie) - _eighth_of(corner) + 1) // 2) % 4


def _facing_of(index, slot):
    """Which way the sticker at `index` faces, relative to `slot`."""
    normal = _NORMAL_OF[FACE_ORDER[index // 9]]
    if normal[1] > 0:
        return FACING_UP
    if normal[1] < 0:
        return FACING_DOWN
    corner, _ = _SLOT_PIECES[slot]
    turn = ((_eighth_of(normal) - _eighth_of(corner) + 1) // 2) % 4
    return FACING_SIDE + turn


def _anchor_faces(slot):
    """The colours the pair is read by: the cross colour for the corner, and for
    the edge whichever of the slot's two faces comes first going clockwise.

    Any consistent choice would do. What matters is that it is the same one at
    every place a piece can stand, so that "how is this turned" has one answer
    rather than one per position.
    """
    corner, _ = _SLOT_PIECES[slot]
    first = min(slot, key=lambda face: (_eighth_of(_NORMAL_OF[face])
                                        - _eighth_of(corner) + 1) % 8)
    return "D", first


def _read_piece(cube, faces, anchor, slot, name):
    """Where one piece of the pair is and which way it is turned."""
    face_of = cube.orientation()
    wanted = frozenset(faces)
    for cubie, indices in _STICKERS_ON.items():
        if len(indices) != len(faces):
            continue
        if frozenset(face_of[cube.facelets[i]] for i in indices) != wanted:
            continue
        place = _place_of(cubie, slot)
        if place is None:
            raise ValueError(
                f"the {slot} {name} is neither in its slot nor in the upper "
                f"face, so more than this pair is unfinished")
        found = next(i for i in indices if face_of[cube.facelets[i]] == anchor)
        return place, _facing_of(found, slot)
    raise ValueError(f"no piece showing {sorted(wanted)} on this cube")


def f2l_pair(cube, slot):
    """Where `slot`'s pair is and how it is turned.

    Returns ``((corner place, corner facing), (edge place, edge facing))``,
    every number read relative to the slot, so the same case in the front-left
    slot reads exactly as it does in the front-right. That is what makes one
    reading serve all four rather than four readings that drift apart.

    This is position and orientation, and nothing about the last layer. Which
    OLL case you are about to be left with is not a fact about the F2L case in
    front of you, and answering it here would answer a question nobody asked.
    """
    if slot not in _SLOT_PIECES:
        raise ValueError(f"no slot named {slot!r}")
    if not is_canonically_oriented(cube):
        raise ValueError("the cross is not on the bottom; derotate first")
    corner_anchor, edge_anchor = _anchor_faces(slot)
    return (_read_piece(cube, ("D",) + tuple(slot), corner_anchor, slot, "corner"),
            _read_piece(cube, tuple(slot), edge_anchor, slot, "edge"))


def pair_key(cube, slot):
    """A value equal for two states iff they are the same F2L case.

    The counterpart of `case_key` and `orientation_key`. Read from all four
    upper-face adjustments and the smallest taken, because turning the top
    layer changes where the pair stands without changing which case it is --
    which is what lets a drill hand the case out at a random angle.

    Only the four adjustments, not the sixteen the last-layer readings use: the
    reading is already relative to a slot, so the cube being held round the
    other way is already accounted for.
    """
    return min(f2l_pair(cube.apply(" ".join(["U"] * turns)), slot)
               for turns in range(4))


def _piece_is_home(cube, faces):
    """Whether the piece showing `faces` is in its own place, the right way up."""
    face_of = cube.orientation()
    return all(face_of[cube.facelets[i]] == FACE_ORDER[i // 9]
               for i in _STICKERS_ON[_cubie_for(faces)])


def is_slot_finished(cube, slot):
    """Whether `slot` holds its own pair, both pieces the right way round."""
    return (_piece_is_home(cube, ("D",) + tuple(slot))
            and _piece_is_home(cube, tuple(slot)))


def is_cross_solved(cube):
    """Whether the cross is built: the bottom centre and its four edges.

    Nothing about the corners, because the cross is the four edges and a cuber
    who has just finished it is not holding a finished bottom face.
    """
    if not is_canonically_oriented(cube):
        return False
    return all(_piece_is_home(cube, ("D", face)) for face in "FRBL")


#: Every sticker on a piece of the upper layer. Constant, because which pieces
#: are up there is a fact about the cube and not about any state of it.
UPPER_LAYER_STICKERS = frozenset(
    index for index in range(54) if _cubie_of(index)[1] == 2)


def pair_stickers(cube, slot):
    """Every sticker on the two pieces `slot`'s pair is made of, wherever they
    are.

    Which stickers those are moves with the case, so it is asked of the state
    rather than looked up: a corner in the upper face and the same corner
    stuck in its slot are the same piece and not the same three stickers.
    """
    face_of = cube.orientation()
    wanted = (frozenset(("D",) + tuple(slot)), frozenset(slot))
    found = set()
    for indices in _STICKERS_ON.values():
        if frozenset(face_of[cube.facelets[i]] for i in indices) in wanted:
            found.update(indices)
    return frozenset(found)


def slot_in_progress(cube):
    """The one slot an F2L case is about, or None when the state is not one.

    Asked of the state rather than passed in, so that a screen handed a cube
    does not have to know which phase it came from. A last-layer case has every
    slot finished and answers None; a cube with two slots open is not a case at
    all and answers None as well.
    """
    if not is_cross_solved(cube):
        return None
    open_slots = [slot for slot in F2L_SLOTS if not is_slot_finished(cube, slot)]
    if len(open_slots) != 1:
        return None
    return open_slots[0] if is_f2l_state(cube, open_slots[0]) else None


def is_f2l_state(cube, slot):
    """Whether the cube is one pair from finished, and that pair is `slot`'s.

    The precondition for a state to be an F2L case: the cross built, the other
    three slots done, this one not, and its pair somewhere a cuber can work
    with -- in the upper face or stuck in its own slot. A pair scattered into
    another slot is a cube with two slots to fix, which is not a case.

    The last layer is not asked about. It can be anything, and usually is.
    """
    if not is_cross_solved(cube):
        return False
    if any(not is_slot_finished(cube, other)
           for other in F2L_SLOTS if other != slot):
        return False
    if is_slot_finished(cube, slot):
        return False
    try:
        f2l_pair(cube, slot)
    except ValueError:
        return False
    return True
