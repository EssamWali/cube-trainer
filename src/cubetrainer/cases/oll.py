"""The 57 OLL cases.

Grouped by shape, the way a cuber recognises them: a T, a W, a fish, a
lightning bolt. Three of the groups are structural rather than pictorial --
every edge already oriented, every corner already oriented, no edge oriented at
all -- and those the tests check against the cube. The rest are silhouettes,
which is a fact about how a case looks rather than one the cube can be asked
about, so what the tests hold there is that every case is filed exactly once
and that no group mixes two different edge shapes.

Each case also declares the case that undoes it. The inverse of an orientation
class is another orientation class, so that declaration is checkable, and it is
what catches an algorithm that was mistranscribed into a different case. See
docs/adr/0002 for why the data is checked this way rather than against its own
algorithms.

Ids carry the phase, so a stray id read back out of old history still says what
it is even when the case list it came from is long gone.
"""

from .catalogue import Case, Catalogue

ALL_EDGES = "All edges oriented"
ALL_CORNERS = "All corners oriented"
T_SHAPES = "T shapes"
W_SHAPES = "W shapes"
SQUARE_SHAPES = "Square shapes"
P_SHAPES = "P shapes"
FISH_SHAPES = "Fish shapes"
C_SHAPES = "C shapes"
SMALL_LIGHTNING = "Small lightning bolts"
BIG_LIGHTNING = "Big lightning bolts"
SMALL_L = "Small L shapes"
KNIGHT_MOVE = "Knight move shapes"
I_SHAPES = "I shapes"
AWKWARD = "Awkward shapes"
NO_EDGES = "No edges oriented"

#: The order the picker lays the groups out in: the two that are nearly
#: finished first, then the shapes, then the dot that has nothing yet.
GROUP_ORDER = (
    ALL_EDGES,
    ALL_CORNERS,
    T_SHAPES,
    W_SHAPES,
    SQUARE_SHAPES,
    P_SHAPES,
    FISH_SHAPES,
    C_SHAPES,
    SMALL_LIGHTNING,
    BIG_LIGHTNING,
    SMALL_L,
    KNIGHT_MOVE,
    I_SHAPES,
    AWKWARD,
    NO_EDGES,
)


OLL_CASES = (
    Case("OLL 21", "Double Sune", ALL_EDGES,
         "R U2 R' U' R U R' U' R U' R'",
         "Every corner twists, opposite pairs matching; it undoes itself.",
         "OLL 21"),
    Case("OLL 22", "Pi", ALL_EDGES,
         "R U2 R2 U' R2 U' R2 U2 R",
         "Every corner twists, adjacent pairs matching; it undoes itself.",
         "OLL 22"),
    Case("OLL 23", "Headlights", ALL_EDGES,
         "R2 D R' U2 R D' R' U2 R'",
         "Two corners are home, side by side; the chameleon undoes it.",
         "OLL 24"),
    Case("OLL 24", "Chameleon", ALL_EDGES,
         "r U R' U' r' F R F'",
         "Two corners are home, side by side; the headlights undoes it.",
         "OLL 23"),
    Case("OLL 25", "Bowtie", ALL_EDGES,
         "F' r U R' U' r' F R",
         "Two corners are home, diagonally opposite; it undoes itself.",
         "OLL 25"),
    Case("OLL 26", "Antisune", ALL_EDGES,
         "R U2 R' U' R U' R'",
         "Three corners twist clockwise, one is home; the sune undoes it.",
         "OLL 27"),
    Case("OLL 27", "Sune", ALL_EDGES,
         "R U R' U R U2 R'",
         "Three corners twist anticlockwise, one is home; the antisune undoes it.",
         "OLL 26"),

    Case("OLL 20", "Checkers", ALL_CORNERS,
         "r U R' U' M2 U R U' R' U' M'",
         "Every corner is already home; it undoes itself.",
         "OLL 20"),
    Case("OLL 28", "Stealth", ALL_CORNERS,
         "r U R' U' r' R U R U' R'",
         "Every corner is already home; it undoes itself.",
         "OLL 28"),
    Case("OLL 57", "Mummy", ALL_CORNERS,
         "R U R' U' M' U R U' r'",
         "Every corner is already home; it undoes itself.",
         "OLL 57"),

    Case("OLL 33", "Key", T_SHAPES,
         "R U R' U' R' F R F'",
         "Two corners are home, side by side; the t undoes it.",
         "OLL 45"),
    Case("OLL 45", "T", T_SHAPES,
         "F R U R' U' F'",
         "Two corners are home, side by side; the key undoes it.",
         "OLL 33"),

    Case("OLL 36", "Wario", W_SHAPES,
         "L' U' L U' L' U L U L F' L' F",
         "Two corners are home, diagonally opposite; the mario undoes it.",
         "OLL 38"),
    Case("OLL 38", "Mario", W_SHAPES,
         "R U R' U R U' R' U' R' F R F'",
         "Two corners are home, diagonally opposite; the wario undoes it.",
         "OLL 36"),

    Case("OLL 5", "Left Square", SQUARE_SHAPES,
         "r' U2 R U R' U r",
         "Three corners twist anticlockwise, one is home; the right square undoes it.",
         "OLL 6"),
    Case("OLL 6", "Right Square", SQUARE_SHAPES,
         "r U2 R' U' R U' r'",
         "Three corners twist clockwise, one is home; the left square undoes it.",
         "OLL 5"),

    Case("OLL 31", "Couch", P_SHAPES,
         "R' U' F U R U' R' F' R",
         "Two corners are home, side by side; the anti p undoes it.",
         "OLL 43"),
    Case("OLL 32", "Anti Couch", P_SHAPES,
         "L U F' U' L' U L F L'",
         "Two corners are home, side by side; the p undoes it.",
         "OLL 44"),
    Case("OLL 43", "Anti P", P_SHAPES,
         "F' U' L' U L F",
         "Two corners are home, side by side; the couch undoes it.",
         "OLL 31"),
    Case("OLL 44", "P", P_SHAPES,
         "F U R U' R' F'",
         "Two corners are home, side by side; the anti couch undoes it.",
         "OLL 32"),

    Case("OLL 9", "Kite", FISH_SHAPES,
         "R U R' U' R' F R2 U R' U' F'",
         "Three corners twist clockwise, one is home; the anti kite undoes it.",
         "OLL 10"),
    Case("OLL 10", "Anti Kite", FISH_SHAPES,
         "R U R' U R' F R F' R U2 R'",
         "Three corners twist anticlockwise, one is home; the kite undoes it.",
         "OLL 9"),
    Case("OLL 35", "Fish Salad", FISH_SHAPES,
         "R U2 R2 F R F' R U2 R'",
         "Two corners are home, diagonally opposite; the mounted fish undoes it.",
         "OLL 37"),
    Case("OLL 37", "Mounted Fish", FISH_SHAPES,
         "F R' F' R U R U' R'",
         "Two corners are home, diagonally opposite; the fish salad undoes it.",
         "OLL 35"),

    Case("OLL 34", "City", C_SHAPES,
         "R U R2 U' R' F R U R U' F'",
         "Two corners are home, side by side; the seeing headlights undoes it.",
         "OLL 46"),
    Case("OLL 46", "Seeing Headlights", C_SHAPES,
         "R' U' R' F R F' U R",
         "Two corners are home, side by side; the city undoes it.",
         "OLL 34"),

    Case("OLL 7", "Right Lightning", SMALL_LIGHTNING,
         "r U R' U R U2 r'",
         "Three corners twist anticlockwise, one is home; the upstairs undoes it.",
         "OLL 12"),
    Case("OLL 8", "Left Lightning", SMALL_LIGHTNING,
         "r' U' R U' R' U2 r",
         "Three corners twist clockwise, one is home; the downstairs undoes it.",
         "OLL 11"),
    Case("OLL 11", "Downstairs", SMALL_LIGHTNING,
         "r U R' U R' F R F' R U2 r'",
         "Three corners twist anticlockwise, one is home; the left lightning undoes it.",
         "OLL 8"),
    Case("OLL 12", "Upstairs", SMALL_LIGHTNING,
         "M' R' U' R U' R' U2 R U' R r'",
         "Three corners twist clockwise, one is home; the right lightning undoes it.",
         "OLL 7"),

    Case("OLL 39", "Left Big Lightning", BIG_LIGHTNING,
         "L F' L' U' L U F U' L'",
         "Two corners are home, diagonally opposite; it undoes itself.",
         "OLL 39"),
    Case("OLL 40", "Right Big Lightning", BIG_LIGHTNING,
         "R' F R U R' U' F' U R",
         "Two corners are home, diagonally opposite; it undoes itself.",
         "OLL 40"),

    Case("OLL 47", "Anti Breakneck", SMALL_L,
         "F' L' U' L U L' U' L U F",
         "Every corner twists, adjacent pairs matching; the back squeezy undoes it.",
         "OLL 49"),
    Case("OLL 48", "Breakneck", SMALL_L,
         "F R U R' U' R U R' U' F'",
         "Every corner twists, adjacent pairs matching; the front squeezy undoes it.",
         "OLL 50"),
    Case("OLL 49", "Back Squeezy", SMALL_L,
         "r U' r2 U r2 U r2 U' r",
         "Every corner twists, adjacent pairs matching; the anti breakneck undoes it.",
         "OLL 47"),
    Case("OLL 50", "Front Squeezy", SMALL_L,
         "r' U r2 U' r2 U' r2 U r'",
         "Every corner twists, adjacent pairs matching; the breakneck undoes it.",
         "OLL 48"),
    Case("OLL 53", "Anti Frying Pan", SMALL_L,
         "r' U' R U' R' U R U' R' U2 r",
         "Every corner twists, opposite pairs matching; the frying pan undoes it.",
         "OLL 54"),
    Case("OLL 54", "Frying Pan", SMALL_L,
         "r U R' U R U' R' U R U2 r'",
         "Every corner twists, opposite pairs matching; the anti frying pan undoes it.",
         "OLL 53"),

    Case("OLL 13", "Gun", KNIGHT_MOVE,
         "F U R U' R2 F' R U R U' R'",
         "Three corners twist anticlockwise, one is home; the anti squeegee undoes it.",
         "OLL 16"),
    Case("OLL 14", "Anti Gun", KNIGHT_MOVE,
         "R' F R U R' F' R F U' F'",
         "Three corners twist clockwise, one is home; the squeegee undoes it.",
         "OLL 15"),
    Case("OLL 15", "Squeegee", KNIGHT_MOVE,
         "r' U' r R' U' R U r' U r",
         "Three corners twist anticlockwise, one is home; the anti gun undoes it.",
         "OLL 14"),
    Case("OLL 16", "Anti Squeegee", KNIGHT_MOVE,
         "r U r' R U R' U' r U' r'",
         "Three corners twist clockwise, one is home; the gun undoes it.",
         "OLL 13"),

    Case("OLL 51", "Ant", I_SHAPES,
         "F U R U' R' U R U' R' F'",
         "Every corner twists, adjacent pairs matching; it undoes itself.",
         "OLL 51"),
    Case("OLL 52", "Rice Cooker", I_SHAPES,
         "R U R' U R U' B U' B' R'",
         "Every corner twists, adjacent pairs matching; it undoes itself.",
         "OLL 52"),
    Case("OLL 55", "Highway", I_SHAPES,
         "R U2 R2 U' R U' R' U2 F R F'",
         "Every corner twists, opposite pairs matching; the streetlights undoes it.",
         "OLL 56"),
    Case("OLL 56", "Streetlights", I_SHAPES,
         "r U r' U R U' R' U R U' R' r U' r'",
         "Every corner twists, opposite pairs matching; the highway undoes it.",
         "OLL 55"),

    Case("OLL 29", "Spotted Chameleon", AWKWARD,
         "R U R' U' R U' R' F' U' F R U R'",
         "Two corners are home, side by side; the right awkward fish undoes it.",
         "OLL 42"),
    Case("OLL 30", "Anti Spotted Chameleon", AWKWARD,
         "F R' F R2 U' R' U' R U R' F2",
         "Two corners are home, side by side; the left awkward fish undoes it.",
         "OLL 41"),
    Case("OLL 41", "Left Awkward Fish", AWKWARD,
         "R U R' U R U2 R' F R U R' U' F'",
         "Two corners are home, side by side; the anti spotted chameleon undoes it.",
         "OLL 30"),
    Case("OLL 42", "Right Awkward Fish", AWKWARD,
         "R' U' R U' R' U2 R F R U R' U' F'",
         "Two corners are home, side by side; the spotted chameleon undoes it.",
         "OLL 29"),

    Case("OLL 1", "Runway", NO_EDGES,
         "R U2 R2 F R F' U2 R' F R F'",
         "Every corner twists, opposite pairs matching; it undoes itself.",
         "OLL 1"),
    Case("OLL 2", "Zamboni", NO_EDGES,
         "F R U R' U' F' f R U R' U' f'",
         "Every corner twists, adjacent pairs matching; it undoes itself.",
         "OLL 2"),
    Case("OLL 3", "Anti Dotted Fish", NO_EDGES,
         "f R U R' U' f' U' F R U R' U' F'",
         "Three corners twist anticlockwise, one is home; the dotted fish undoes it.",
         "OLL 4"),
    Case("OLL 4", "Dotted Fish", NO_EDGES,
         "f R U R' U' f' U F R U R' U' F'",
         "Three corners twist clockwise, one is home; the anti dotted fish undoes it.",
         "OLL 3"),
    Case("OLL 17", "Slash", NO_EDGES,
         "R U R' U R' F R F' U2 R' F R F'",
         "Two corners are home, diagonally opposite; it undoes itself.",
         "OLL 17"),
    Case("OLL 18", "Crown", NO_EDGES,
         "r U R' U R U2 r2 U' R U' R' U2 r",
         "Two corners are home, side by side; the bunny undoes it.",
         "OLL 19"),
    Case("OLL 19", "Bunny", NO_EDGES,
         "r' R U R U R' U' M' R' F R F'",
         "Two corners are home, side by side; the crown undoes it.",
         "OLL 18"),
)

#: The OLL phase, as the screens see it.
CATALOGUE = Catalogue("OLL", OLL_CASES, GROUP_ORDER)


def get(case_id):
    """Look a case up by id, e.g. ``get("OLL 27")``."""
    return CATALOGUE.get(case_id)


def by_group():
    """Cases arranged into the groups the picker displays."""
    return CATALOGUE.by_group()
