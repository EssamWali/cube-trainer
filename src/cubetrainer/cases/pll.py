"""The 21 PLL cases.

Each case carries an algorithm and, separately, the structural facts that make
it that case: which group it belongs to, and whether it is its own inverse.
Those facts are written down independently of the algorithms so the test suite
can check one against the other. See docs/adr/0002 for why that matters.

The setup a drill hands out is the inverse of the algorithm, so a cuber who
applies the scramble to a solved cube is left holding exactly this case.
"""

from dataclasses import dataclass

from ..cube.notation import derotate, format_sequence, invert

#: Groups as speedcubers learn them - by what the case does to the corners,
#: because that is what you recognise first when you look down at the cube.
EDGES_ONLY = "Edges only"
CORNERS_ONLY = "Corners only"
ADJACENT_SWAP = "Adjacent corner swap"
DIAGONAL_SWAP = "Diagonal corner swap"

GROUP_ORDER = (EDGES_ONLY, CORNERS_ONLY, ADJACENT_SWAP, DIAGONAL_SWAP)


@dataclass(frozen=True)
class Case:
    """One last-layer case."""

    id: str
    name: str
    group: str
    #: Written so the cube ends in the orientation it started in. Some published
    #: algorithms include a regrip and never turn back; left that way they are
    #: ambiguous as data, because the case they solve depends on how you were
    #: holding the cube when you finished.
    algorithm: str
    description: str
    #: id of the case that undoes this one; equal to `id` when self-inverse.
    inverse: str

    @property
    def setup(self):
        """The sequence that takes a solved cube to this case.

        Rewritten without whole-cube rotations, so applying a scramble never
        leaves the cuber holding the cube differently from how they picked it
        up, and the last layer is always the layer on top.
        """
        return format_sequence(derotate(invert(self.algorithm)))

    @property
    def is_self_inverse(self):
        return self.inverse == self.id


PLL_CASES = (
    Case("Ua", "Ua perm", EDGES_ONLY,
         "R U' R U R U R U' R' U' R2",
         "Three edges cycle; corners are already home.", "Ub"),
    Case("Ub", "Ub perm", EDGES_ONLY,
         "R2 U R U R' U' R' U' R' U R'",
         "Three edges cycle the other way; corners are already home.", "Ua"),
    Case("H", "H perm", EDGES_ONLY,
         "M2 U M2 U2 M2 U M2",
         "Both pairs of opposite edges swap; corners are already home.", "H"),
    Case("Z", "Z perm", EDGES_ONLY,
         "M2 U M2 U M' U2 M2 U2 M' U2",
         "Both pairs of adjacent edges swap; corners are already home.", "Z"),

    Case("Aa", "Aa perm", CORNERS_ONLY,
         "R' F R' B2 R F' R' B2 R2",
         "Three corners cycle; edges are already home.", "Ab"),
    Case("Ab", "Ab perm", CORNERS_ONLY,
         "R2 B2 R F R' B2 R F' R",
         "Three corners cycle the other way; edges are already home.", "Aa"),
    Case("E", "E perm", CORNERS_ONLY,
         "x' L' U L D' L' U' L D L' U' L D' L' U L D x",
         "Two pairs of corners swap; edges are already home.", "E"),

    Case("T", "T perm", ADJACENT_SWAP,
         "R U R' U' R' F R2 U' R' U' R U R' F'",
         "Two adjacent corners swap and two opposite edges swap.", "T"),
    Case("Ja", "Ja perm", ADJACENT_SWAP,
         "R' U L' U2 R U' R' U2 R L",
         "Two adjacent corners and the two edges beside them swap.", "Ja"),
    Case("Jb", "Jb perm", ADJACENT_SWAP,
         "R U R' F' R U R' U' R' F R2 U' R' U'",
         "Mirror of Ja: two adjacent corners and two adjacent edges swap.", "Jb"),
    Case("F", "F perm", ADJACENT_SWAP,
         "R' U' F' R U R' U' R' F R2 U' R' U' R U R' U R",
         "Two adjacent corners swap and two edges swap across the layer.", "F"),
    Case("Ra", "Ra perm", ADJACENT_SWAP,
         "R U' R' U' R U R D R' U' R D' R' U2 R' U'",
         "Two adjacent corners swap alongside an edge swap.", "Ra"),
    Case("Rb", "Rb perm", ADJACENT_SWAP,
         "R' U2 R U2 R' F R U R' U' R' F' R2 U'",
         "Mirror of Ra.", "Rb"),
    Case("Ga", "Ga perm", ADJACENT_SWAP,
         "R2 U R' U R' U' R U' R2 U' D R' U R D'",
         "Corners and edges each cycle in threes.", "Gb"),
    Case("Gb", "Gb perm", ADJACENT_SWAP,
         "R' U' R U D' R2 U R' U R U' R U' R2 D",
         "Undoes Ga.", "Ga"),
    Case("Gc", "Gc perm", ADJACENT_SWAP,
         "R2 U' R U' R U R' U R2 U D' R U' R' D",
         "Corners and edges each cycle in threes, the other pairing.", "Gd"),
    Case("Gd", "Gd perm", ADJACENT_SWAP,
         "R U R' U' D R2 U' R U' R' U R' U R2 D'",
         "Undoes Gc.", "Gc"),

    Case("V", "V perm", DIAGONAL_SWAP,
         "R' U R' U' y R' F' R2 U' R' U R' F R F y'",
         "Two diagonal corners swap along with two adjacent edges.", "V"),
    Case("Y", "Y perm", DIAGONAL_SWAP,
         "F R U' R' U' R U R' F' R U R' U' R' F R F'",
         "Two diagonal corners swap along with two adjacent edges, offset from V.", "Y"),
    Case("Na", "Na perm", DIAGONAL_SWAP,
         "R U R' U R U R' F' R U R' U' R' F R2 U' R' U2 R U' R'",
         "Two diagonal corners and two opposite edges swap.", "Na"),
    Case("Nb", "Nb perm", DIAGONAL_SWAP,
         "R' U R U' R' F' U' F R U R' F R' F' R U' R",
         "Mirror of Na.", "Nb"),
)

BY_ID = {case.id: case for case in PLL_CASES}


def get(case_id):
    """Look a case up by id, e.g. ``get("T")``."""
    try:
        return BY_ID[case_id]
    except KeyError:
        raise KeyError(f"no PLL case named {case_id!r}") from None


def by_group():
    """Cases arranged into the groups the picker displays."""
    return {
        group: tuple(c for c in PLL_CASES if c.group == group)
        for group in GROUP_ORDER
    }
