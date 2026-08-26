"""The WCA-style timer, as a state machine.

Time is passed in rather than read from a clock, so the whole thing is testable
without a window and without waiting. That matters more here than usual: a
timer wrong by a tenth is worse than no timer, and a tenth is not visible by
inspection.
"""

from enum import Enum

HOLD_SECONDS = 0.55
INSPECTION_SECONDS = 15.0


class TimerState(str, Enum):
    IDLE = "idle"
    INSPECTING = "inspecting"
    ARMING = "arming"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"


class Penalty(str, Enum):
    NONE = "none"
    PLUS_TWO = "plus_two"
    DNF = "dnf"


class SolveTimer:
    """Times one attempt, optionally split into phases.

    A drill rep is the one-phase case. A full solve ticks whichever phase
    boundaries the cuber chose, and the timer stops at the last of them, so
    timing only the cross is a configuration rather than a separate mode.
    """

    def __init__(self, phases=("total",), hold_seconds=HOLD_SECONDS,
                 inspection=False, inspection_seconds=INSPECTION_SECONDS):
        if not phases:
            raise ValueError("a timer needs at least one phase")
        self.phases = tuple(phases)
        self.hold_seconds = hold_seconds
        self.inspection = inspection
        self.inspection_seconds = inspection_seconds
        self.state = TimerState.IDLE
        self.penalty = Penalty.NONE
        self._press_at = None
        self._inspection_started = None
        self._started = None
        self._boundaries = []

    def press(self, now):
        """The cuber pressed the timer key."""
        if self.state is TimerState.RUNNING:
            self._boundaries.append(now)
            if len(self._boundaries) == len(self.phases):
                self.state = TimerState.STOPPED
            return
        if self.state in (TimerState.IDLE, TimerState.INSPECTING):
            self._press_at = now
            self.state = TimerState.ARMING

    def release(self, now):
        """The cuber let go."""
        if self.state is TimerState.ARMING:
            # Released too early, so nothing happens. That is the whole point
            # of arming: the start cannot be nudged.
            was_inspecting = self.inspection and self._inspection_started is not None
            self.state = TimerState.INSPECTING if was_inspecting else TimerState.IDLE
            self._press_at = None
        elif self.state is TimerState.READY:
            self._started = now
            self._boundaries = []
            self.state = TimerState.RUNNING

    def tick(self, now):
        """Advance time. Call once per frame so ARMING can become READY."""
        if self.state is TimerState.ARMING and self._press_at is not None:
            if now - self._press_at >= self.hold_seconds:
                self.state = TimerState.READY

    def begin_inspection(self, now):
        if self.state is not TimerState.IDLE or not self.inspection:
            return
        self._inspection_started = now
        self.state = TimerState.INSPECTING

    def elapsed(self, now):
        """Seconds since the timer started, or the final time once stopped."""
        if self._started is None:
            return 0.0
        if self.state is TimerState.STOPPED:
            return self._boundaries[-1] - self._started
        return now - self._started

    def inspection_elapsed(self, now):
        if self._inspection_started is None:
            return 0.0
        return now - self._inspection_started

    def inspection_penalty(self, now):
        """WCA inspection penalties: plus two over 15 seconds, DNF over 17."""
        used = self.inspection_elapsed(now)
        if used > self.inspection_seconds + 2:
            return Penalty.DNF
        if used > self.inspection_seconds:
            return Penalty.PLUS_TWO
        return Penalty.NONE

    def splits(self):
        """Duration of each completed phase, in seconds."""
        if self._started is None:
            return ()
        marks = [self._started] + list(self._boundaries)
        return tuple(marks[i + 1] - marks[i] for i in range(len(self._boundaries)))

    def total(self):
        """Recorded time in seconds, with any penalty applied."""
        if self.state is not TimerState.STOPPED:
            return None
        raw = self._boundaries[-1] - self._started
        if self.penalty is Penalty.PLUS_TWO:
            return raw + 2.0
        return raw

    @property
    def is_finished(self):
        return self.state is TimerState.STOPPED

    def reset(self):
        self.state = TimerState.IDLE
        self.penalty = Penalty.NONE
        self._press_at = None
        self._inspection_started = None
        self._started = None
        self._boundaries = []
