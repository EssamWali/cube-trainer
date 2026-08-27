"""Geometric derivation of every move's facelet permutation.

The engine is defined once, in 3D, instead of as six hand-written tables of
index swaps. Every move is the same three-line idea -- "rotate the stickers
lying in this slab of the cube about this axis" -- so face turns, wide moves,
slices and whole-cube rotations all fall out of one definition. That makes the
engine auditable by a reader who knows which way a cube turns, rather than one
willing to hold 54 indices in their head.

Coordinates are integers on a scale where a face plane sits at +/-3 and the
sticker offsets within a face are +/-2. Axes: +x right, +y up, +z front.
"""

FACE_ORDER = "URFDLB"
FACE_BASE = {face: i * 9 for i, face in enumerate(FACE_ORDER)}

# (outward normal, direction of increasing row, direction of increasing column)
# Read off the standard URFDLB net: U with Back at the top, D with Front at the
# top, and the side faces each viewed head-on with Up at the top.
_FRAME = {
    "U": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    "R": ((1, 0, 0), (0, -1, 0), (0, 0, -1)),
    "F": ((0, 0, 1), (0, -1, 0), (1, 0, 0)),
    "D": ((0, -1, 0), (0, 0, -1), (1, 0, 0)),
    "L": ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "B": ((0, 0, -1), (0, -1, 0), (-1, 0, 0)),
}


def _position(index):
    """3D coordinate of the sticker at `index`."""
    face = FACE_ORDER[index // 9]
    cell = index % 9
    row, col = divmod(cell, 3)
    normal, rowdir, coldir = _FRAME[face]
    return tuple(
        normal[a] * 3 + rowdir[a] * (row - 1) * 2 + coldir[a] * (col - 1) * 2
        for a in range(3)
    )


POSITIONS = tuple(_position(i) for i in range(54))


def sticker_corners(index):
    """The four corners of a sticker, going round its edge.

    The engine only ever needs a sticker's centre. A picture of the cube needs
    its outline, and the outline follows from the same frame the centre does --
    half a cell along each of the face's two directions -- rather than from a
    second description of where the faces are.
    """
    _, rowdir, coldir = _FRAME[FACE_ORDER[index // 9]]
    centre = POSITIONS[index]
    return tuple(
        tuple(centre[a] + rowdir[a] * down + coldir[a] * across for a in range(3))
        for down, across in ((-1, -1), (-1, 1), (1, 1), (1, -1))
    )
_INDEX_AT = {p: i for i, p in enumerate(POSITIONS)}
assert len(_INDEX_AT) == 54, "facelet positions are not distinct"


def _rot_x(v):
    return (v[0], v[2], -v[1])


def _rot_y(v):
    return (-v[2], v[1], v[0])


def _rot_z(v):
    return (v[1], -v[0], v[2])


_AXIS = {"x": (_rot_x, 0), "y": (_rot_y, 1), "z": (_rot_z, 2)}

# name -> (axis, quarter turns clockwise about that axis, slab predicate)
# A quarter-turn count of 3 means the move goes the opposite way to the axis,
# which is what makes D the mirror of U, L of R, and B of F.
_MOVES = {
    "U": ("y", 1, lambda c: c >= 2),
    "D": ("y", 3, lambda c: c <= -2),
    "R": ("x", 1, lambda c: c >= 2),
    "L": ("x", 3, lambda c: c <= -2),
    "F": ("z", 1, lambda c: c >= 2),
    "B": ("z", 3, lambda c: c <= -2),
    # Slices, each following the face it runs parallel to.
    "M": ("x", 3, lambda c: c == 0),
    "E": ("y", 3, lambda c: c == 0),
    "S": ("z", 1, lambda c: c == 0),
    # Wide turns: the outer layer plus the slice beside it.
    "u": ("y", 1, lambda c: c >= 0),
    "d": ("y", 3, lambda c: c <= 0),
    "r": ("x", 1, lambda c: c >= 0),
    "l": ("x", 3, lambda c: c <= 0),
    "f": ("z", 1, lambda c: c >= 0),
    "b": ("z", 3, lambda c: c <= 0),
    # Whole-cube rotations.
    "x": ("x", 1, lambda c: True),
    "y": ("y", 1, lambda c: True),
    "z": ("z", 1, lambda c: True),
}


def _build(axis_name, quarters, in_slab):
    rotate, axis = _AXIS[axis_name]
    table = list(range(54))
    for src, pos in enumerate(POSITIONS):
        if not in_slab(pos[axis]):
            continue
        moved = pos
        for _ in range(quarters):
            moved = rotate(moved)
        table[_INDEX_AT[moved]] = src
    return tuple(table)


#: name -> permutation table, where ``new[i] = old[TABLES[name][i]]``.
TABLES = {name: _build(*spec) for name, spec in _MOVES.items()}
