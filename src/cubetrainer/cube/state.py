"""The cube state: 54 facelets in URFDLB order."""

from .geometry import FACE_BASE, FACE_ORDER, TABLES
from .notation import parse, quarter_turns

SOLVED_FACELETS = tuple(face for face in FACE_ORDER for _ in range(9))

#: Index of each face's centre. Centres never move relative to one another, so
#: they are what tells you which way a cube is oriented.
CENTRES = {face: FACE_BASE[face] + 4 for face in FACE_ORDER}


class Cube:
    """An immutable cube state.

    Every operation returns a new Cube. Drills hand the same state to a
    renderer, a validator and a store, and shared mutable state between those
    three is a class of bug worth designing out rather than remembering.
    """

    __slots__ = ("facelets",)

    def __init__(self, facelets=None):
        self.facelets = tuple(facelets) if facelets is not None else SOLVED_FACELETS
        if len(self.facelets) != 54:
            raise ValueError(f"expected 54 facelets, got {len(self.facelets)}")

    @classmethod
    def solved(cls):
        return cls()

    def apply(self, sequence):
        """Return the state reached by performing `sequence`."""
        facelets = self.facelets
        for move in parse(sequence):
            table = TABLES[move[0]]
            for _ in range(quarter_turns(move)):
                facelets = tuple(facelets[i] for i in table)
        return Cube(facelets)

    def is_solved(self):
        """True when every face is a single colour.

        Judged against each face's own centre, so a cube that has merely been
        rotated still counts as solved -- which is what a cuber means by it.
        """
        return all(
            self.facelets[FACE_BASE[face] + i] == self.facelets[CENTRES[face]]
            for face in FACE_ORDER
            for i in range(9)
        )

    def orientation(self):
        """Map from face colour to the position that colour's centre now sits at.

        After a whole-cube rotation the sticker labelled 'F' is no longer on the
        front, so anything reasoning about where a piece *belongs* has to go
        through this rather than through the labels.
        """
        return {self.facelets[CENTRES[face]]: face for face in FACE_ORDER}

    def to_kociemba(self):
        """The 54-character string the kociemba solver expects."""
        return "".join(self.facelets)

    def __eq__(self, other):
        return isinstance(other, Cube) and self.facelets == other.facelets

    def __hash__(self):
        return hash(self.facelets)

    def __repr__(self):
        return f"Cube({self.to_kociemba()!r})"

    def to_net(self):
        """Human-readable unfolded net, matching the classic terminal layout."""
        f = self.facelets

        def row(*indices):
            return " ".join(f[i] for i in indices)

        lines = [f"      {row(0, 1, 2)}", f"      {row(3, 4, 5)}", f"      {row(6, 7, 8)}"]
        for a, b, c, d in ((36, 18, 9, 45), (39, 21, 12, 48), (42, 24, 15, 51)):
            lines.append(
                "  ".join(row(x, x + 1, x + 2) for x in (a, b, c, d))
            )
        lines += [f"      {row(27, 28, 29)}", f"      {row(30, 31, 32)}", f"      {row(33, 34, 35)}"]
        return "\n".join(lines)
