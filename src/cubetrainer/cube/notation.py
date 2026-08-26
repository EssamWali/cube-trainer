"""Parsing, inverting and normalising move sequences."""

from .geometry import TABLES

# Aliases used by published algorithms: Rw and r mean the same wide turn.
_ALIASES = {"Uw": "u", "Rw": "r", "Fw": "f", "Dw": "d", "Lw": "l", "Bw": "b"}


class NotationError(ValueError):
    """Raised when a token is not a move this cube understands."""


def parse(sequence):
    """Split a sequence into validated move tokens.

    Accepts a string ("R U R' U'") or an iterable of tokens. Rotations, slices
    and wide turns are all legal.
    """
    if isinstance(sequence, str):
        tokens = sequence.replace("(", " ").replace(")", " ").split()
    else:
        tokens = [str(t) for t in sequence]

    moves = []
    for token in tokens:
        raw = token.strip()
        if not raw:
            continue
        suffix = ""
        if raw[-1] in ("'", "2", "’"):
            suffix = "'" if raw[-1] == "’" else raw[-1]
            raw = raw[:-1]
        raw = _ALIASES.get(raw, raw)
        if raw not in TABLES:
            raise NotationError(f"unknown move {token!r}")
        moves.append(raw + suffix)
    return moves


def invert(sequence):
    """The sequence that undoes `sequence`."""
    inverted = []
    for move in reversed(parse(sequence)):
        if move.endswith("2"):
            inverted.append(move)
        elif move.endswith("'"):
            inverted.append(move[:-1])
        else:
            inverted.append(move + "'")
    return inverted


def format_sequence(sequence):
    """Render a sequence for display."""
    return " ".join(parse(sequence))


def quarter_turns(move):
    """How many clockwise quarter turns `move` represents."""
    if move.endswith("2"):
        return 2
    if move.endswith("'"):
        return 3
    return 1


def move_count(sequence, metric="htm"):
    """Length of a sequence.

    Half Turn Metric counts a double turn as one move and ignores whole-cube
    rotations, which is the convention algorithm lists are quoted in.
    """
    moves = [m for m in parse(sequence) if m[0] not in "xyz"]
    if metric == "htm":
        return len(moves)
    if metric == "qtm":
        # A prime turn is one quarter turn, not three: `quarter_turns` counts
        # table applications, which is a different question from move count.
        return sum(2 if m.endswith("2") else 1 for m in moves)
    raise ValueError(f"unknown metric {metric!r}")


def simplify(sequence):
    """Collapse consecutive turns of the same face.

    Setups are built by joining sequences end to end, which regularly produces
    things like ``R' R2``. Cubers read a scramble as instructions, and
    instructions that undo themselves are noise.
    """
    suffix = {1: "", 2: "2", 3: "'"}
    result = []
    for move in parse(sequence):
        face = move[0]
        if result and result[-1][0] == face:
            total = (quarter_turns(result[-1]) + quarter_turns(move)) % 4
            result.pop()
            if total:
                result.append(face + suffix[total])
        else:
            result.append(move)
    return result


def derotate(sequence):
    """Rewrite a sequence so it performs no whole-cube rotations.

    Published algorithms often start with a rotation and never undo it, which
    leaves the cuber holding the cube differently from how they picked it up.
    In a scramble that is worse than untidy: the last layer ends up somewhere
    other than the top, so the diagram and the cube disagree.

    A rotation can always be pushed to the end of a sequence by relabelling the
    moves that follow it, and a rotation at the very end only changes how the
    cube is held. So it is dropped.
    """
    from .geometry import TABLES

    identity = tuple(range(54))

    def then(first, second):
        return tuple(first[second[i]] for i in range(54))

    def inverse(table):
        result = [0] * 54
        for index, source in enumerate(table):
            result[source] = index
        return tuple(result)

    by_table = {table: name for name, table in TABLES.items()}
    rotation = identity
    rewritten = []
    for move in parse(sequence):
        base, suffix = move[0], move[1:]
        if base in "xyz":
            for _ in range(quarter_turns(move)):
                rotation = then(rotation, TABLES[base])
            continue
        conjugated = then(then(rotation, TABLES[base]), inverse(rotation))
        name = by_table.get(conjugated)
        if name is None:
            raise NotationError(f"cannot express {move!r} without a rotation")
        rewritten.append(name + suffix)
    return rewritten
