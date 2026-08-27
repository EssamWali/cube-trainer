"""The 41 F2L cases.

Unlike the last-layer phases, F2L has no set of names everybody uses and no one
published list of algorithms: most cubers build their pairs by working it out
rather than by recognising a case and firing. So the cases are numbered, what
distinguishes them is written down as a description, and the algorithms here are
the shortest way to solve each case out of the triggers that turn one slot and
put everything else back.

They are correct by construction rather than transcribed, which changes what the
tests here are worth: see the note in docs/adr/0003. A cuber who prefers their
own algorithm for a case can set it in the library, which is what that feature
is for.

The setup a drill hands out is the inverse of the algorithm, so a cuber who
applies the scramble to a solved cube is left holding exactly this case.
"""

from .catalogue import Case, Catalogue

#: The slot the shipped cases are written for. The same case in another slot is
#: the same case -- the reading in `cases.pattern` is relative to the slot it is
#: given -- so the data says which slot it is written for rather than shipping
#: four copies of everything.
SLOT = "FR"

#: Where a piece is and which way it faces are described for the front-right
#: slot, since that is the slot the cases are written for.

#: Families, by where the two pieces are, because that is what a cuber looks for
#: before anything else. Structural, so the tests read them off the cube rather
#: than trusting the label.
PAIR_UP = "Pair in the upper face"
CORNER_UP = "Corner up, edge in"
EDGE_UP = "Edge up, corner in"
BOTH_IN = "Both in the slot"

GROUP_ORDER = (PAIR_UP, CORNER_UP, EDGE_UP, BOTH_IN)

F2L_CASES = (
    Case("F2L 1", "F2L 1", PAIR_UP,
         "F' U' F",
         "Corner above its slot, cross colour front; "
         "edge back-left, front colour up."),
    Case("F2L 2", "F2L 2", PAIR_UP,
         "F' U F",
         "Corner back-right, cross colour back; "
         "edge above its slot, front colour up."),
    Case("F2L 3", "F2L 3", PAIR_UP,
         "R U' R'",
         "Corner front-left, cross colour left; "
         "edge front-left, front colour front."),
    Case("F2L 4", "F2L 4", PAIR_UP,
         "R U R'",
         "Corner above its slot, cross colour right; "
         "edge back-right, front colour back."),
    Case("F2L 5", "F2L 5", PAIR_UP,
         "R U R' F' U' F",
         "Corner back-left, cross colour up; "
         "edge front-left, front colour up."),
    Case("F2L 6", "F2L 6", PAIR_UP,
         "F' U' F R U R'",
         "Corner back-left, cross colour up; "
         "edge above its slot, front colour right."),
    Case("F2L 7", "F2L 7", PAIR_UP,
         "F' U' F U' F' U' F",
         "Corner front-left, cross colour left; "
         "edge above its slot, front colour up."),
    Case("F2L 8", "F2L 8", PAIR_UP,
         "F' U F U' F' U' F",
         "Corner front-left, cross colour left; "
         "edge back-left, front colour up."),
    Case("F2L 9", "F2L 9", PAIR_UP,
         "F' U2 F U F' U' F",
         "Corner above its slot, cross colour up; "
         "edge front-left, front colour up."),
    Case("F2L 10", "F2L 10", PAIR_UP,
         "R U2 R' U F' U' F",
         "Corner back-right, cross colour right; "
         "edge back-right, front colour up."),
    Case("F2L 11", "F2L 11", PAIR_UP,
         "R U' R' U2 F' U' F",
         "Corner above its slot, cross colour right; "
         "edge above its slot, front colour up."),
    Case("F2L 12", "F2L 12", PAIR_UP,
         "F' U2 F U' F' U F",
         "Corner back-right, cross colour up; "
         "edge front-left, front colour up."),
    Case("F2L 13", "F2L 13", PAIR_UP,
         "F' U' F U2 F' U F",
         "Corner front-left, cross colour front; "
         "edge back-right, front colour up."),
    Case("F2L 14", "F2L 14", PAIR_UP,
         "F' U2 F U2 F' U F",
         "Corner front-left, cross colour front; "
         "edge above its slot, front colour up."),
    Case("F2L 15", "F2L 15", PAIR_UP,
         "R U2 R' U R U' R'",
         "Corner front-left, cross colour up; "
         "edge above its slot, front colour right."),
    Case("F2L 16", "F2L 16", PAIR_UP,
         "R U R' U2 R U' R'",
         "Corner back-right, cross colour right; "
         "edge back-left, front colour left."),
    Case("F2L 17", "F2L 17", PAIR_UP,
         "R U2 R' U2 R U' R'",
         "Corner back-right, cross colour right; "
         "edge front-left, front colour front."),
    Case("F2L 18", "F2L 18", PAIR_UP,
         "F' U F U' R U R'",
         "Corner front-left, cross colour front; "
         "edge back-right, front colour back."),
    Case("F2L 19", "F2L 19", PAIR_UP,
         "F' U2 F U' R U R'",
         "Corner front-left, cross colour front; "
         "edge back-left, front colour left."),
    Case("F2L 20", "F2L 20", PAIR_UP,
         "R U2 R' U' R U R'",
         "Corner above its slot, cross colour up; "
         "edge above its slot, front colour right."),
    Case("F2L 21", "F2L 21", PAIR_UP,
         "R U' R' U R U R'",
         "Corner back-right, cross colour back; "
         "edge back-right, front colour back."),
    Case("F2L 22", "F2L 22", PAIR_UP,
         "F' U F U2 R U R'",
         "Corner above its slot, cross colour front; "
         "edge front-left, front colour front."),
    Case("F2L 23", "F2L 23", PAIR_UP,
         "F' U' F R U' R' F' U' F",
         "Corner above its slot, cross colour up; "
         "edge above its slot, front colour up."),
    Case("F2L 24", "F2L 24", PAIR_UP,
         "F' U' F R U2 R' F' U' F",
         "Corner front-left, cross colour up; "
         "edge back-left, front colour left."),

    Case("F2L 25", "F2L 25", CORNER_UP,
         "R U2 R' F' U' F",
         "Corner front-left, cross colour up; edge in but flipped."),
    Case("F2L 26", "F2L 26", CORNER_UP,
         "F' U2 F U' F' U' F",
         "Corner front-left, cross colour left; "
         "edge in, the right way round."),
    Case("F2L 27", "F2L 27", CORNER_UP,
         "R U' R' U' F' U' F",
         "Corner back-left, cross colour back; edge in but flipped."),
    Case("F2L 28", "F2L 28", CORNER_UP,
         "F' U F U2 F' U F",
         "Corner front-left, cross colour front; "
         "edge in, the right way round."),
    Case("F2L 29", "F2L 29", CORNER_UP,
         "F' U' F U R U' R'",
         "Corner back-left, cross colour left; edge in but flipped."),
    Case("F2L 30", "F2L 30", CORNER_UP,
         "F' U' F U' R U' R' F' U' F",
         "Corner above its slot, cross colour up; "
         "edge in, the right way round."),

    Case("F2L 31", "F2L 31", EDGE_UP,
         "R U' R' F' U' F",
         "Corner in but twisted, cross colour front; "
         "edge back-right, front colour up."),
    Case("F2L 32", "F2L 32", EDGE_UP,
         "R U2 R' F' U2 F",
         "Corner in but twisted, cross colour right; "
         "edge front-left, front colour up."),
    Case("F2L 33", "F2L 33", EDGE_UP,
         "F' U F R U R'",
         "Corner in but twisted, cross colour right; "
         "edge back-left, front colour left."),
    Case("F2L 34", "F2L 34", EDGE_UP,
         "F' U2 F R U2 R'",
         "Corner in but twisted, cross colour front; "
         "edge above its slot, front colour right."),
    Case("F2L 35", "F2L 35", EDGE_UP,
         "R U R' U' F' U' F",
         "Corner in, the right way up; edge back-left, front colour up."),
    Case("F2L 36", "F2L 36", EDGE_UP,
         "F' U F U R U' R'",
         "Corner in, the right way up; "
         "edge back-right, front colour back."),

    Case("F2L 37", "F2L 37", BOTH_IN,
         "R U' R' F' U F U2 F' U' F",
         "Corner in but twisted, cross colour right; "
         "edge in but flipped."),
    Case("F2L 38", "F2L 38", BOTH_IN,
         "F' U F R U' R' U2 R U R'",
         "Corner in but twisted, cross colour front; "
         "edge in but flipped."),
    Case("F2L 39", "F2L 39", BOTH_IN,
         "F' U2 F U' F' U F U' F' U' F",
         "Corner in but twisted, cross colour front; "
         "edge in, the right way round."),
    Case("F2L 40", "F2L 40", BOTH_IN,
         "F' U' F U F' U2 F U F' U' F",
         "Corner in but twisted, cross colour right; "
         "edge in, the right way round."),
    Case("F2L 41", "F2L 41", BOTH_IN,
         "R U2 R' U R U2 R' U F' U' F",
         "Corner in, the right way up; edge in but flipped."),
)

#: The F2L phase, as the screens see it. Not drilled: a scramble applied to a
#: solved cube is not how a cuber meets an F2L case, and the drill's promise is
#: built on that scramble. The algorithms are here to read and learn from --
#: see docs/adr/0004.
CATALOGUE = Catalogue("F2L", F2L_CASES, GROUP_ORDER, drilled=False)


def get(case_id):
    """Look a case up by id, e.g. ``get("F2L 1")``."""
    return CATALOGUE.get(case_id)


def by_group():
    """Cases arranged into the groups the picker displays."""
    return CATALOGUE.by_group()
