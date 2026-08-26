"""One phase's cases, as the screens see them.

A screen that imports the PLL module has learned something that is not true:
that PLL is the only phase there is. A catalogue is the same knowledge without
that assumption -- the phase's name, the order its groups are shown in, and
how to find a case by id -- so a screen can be handed a phase rather than
reaching for one.
"""

from dataclasses import dataclass

from ..cube.notation import derotate, format_sequence, invert


@dataclass(frozen=True)
class Case:
    """One last-layer case.

    The same shape whichever phase it belongs to: an OLL case and a PLL case
    differ in what they are a case *of*, not in what is written down about
    them.
    """

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


class Catalogue:
    """Every case of one phase, and the phase itself."""

    def __init__(self, phase, cases, group_order):
        self.phase = phase
        self.cases = tuple(cases)
        self.group_order = tuple(group_order)
        self._by_id = {case.id: case for case in self.cases}

    def get(self, case_id):
        """Look a case up by id, e.g. ``get("T")``."""
        try:
            return self._by_id[case_id]
        except KeyError:
            raise KeyError(f"no {self.phase} case named {case_id!r}") from None

    def by_group(self):
        """Cases arranged into the groups the picker displays."""
        return {
            group: tuple(c for c in self.cases if c.group == group)
            for group in self.group_order
        }

    @property
    def order(self):
        """Every case, flattened in the order the picker lays them out.

        The grid reads group by group, so moving right off the end of one
        group lands on the start of the next.
        """
        grouped = self.by_group()
        return tuple(c for group in self.group_order for c in grouped[group])

    def __len__(self):
        return len(self.cases)

    def __iter__(self):
        return iter(self.cases)

    def __repr__(self):
        return f"Catalogue({self.phase!r}, {len(self.cases)} cases)"
