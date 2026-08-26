"""Choosing which case comes next in a drill."""

import random


class RoundRobinSampler:
    """Deals every selected case once before repeating any of them.

    Uniform random choice feels broken at the set sizes people actually drill:
    pick three cases and it will hand you the same one four times running, and
    you will assume the trainer is stuck. This shuffles a full round, deals it
    out, then shuffles again, never repeating a case across the seam.
    """

    def __init__(self, case_ids, rng=None):
        self._case_ids = list(case_ids)
        if not self._case_ids:
            raise ValueError("a drill needs at least one case")
        self._rng = rng or random
        self._queue = []
        self._last = None

    def next(self):
        if not self._queue:
            self._refill()
        self._last = self._queue.pop()
        return self._last

    def _refill(self):
        upcoming = list(self._case_ids)
        self._rng.shuffle(upcoming)
        # Dealt from the end, so the last item is the one served first.
        if len(upcoming) > 1 and upcoming[-1] == self._last:
            upcoming[-1], upcoming[0] = upcoming[0], upcoming[-1]
        self._queue = upcoming

    @property
    def case_ids(self):
        return tuple(self._case_ids)
