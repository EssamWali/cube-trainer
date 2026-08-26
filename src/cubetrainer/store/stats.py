"""Turning stored attempts into the numbers a cuber acts on.

Two deliberate choices live here.

Averages follow the WCA definition rather than the arithmetic mean, because
the point of measuring is comparability: an average that does not match the
one csTimer shows cannot be compared against it.

Weakness is reported as several separate signals instead of one score. Cases
are weak in different ways -- slow to execute, inconsistent, still being
looked up, dropped often -- and collapsing those into a single number hides
exactly the distinction that tells you what to do about it.
"""

import statistics
from dataclasses import dataclass


def _durations(rows):
    """Recorded seconds per attempt, with DNFs as None."""
    values = []
    for row in rows:
        if row["penalty"] == "dnf" or row["duration_ms"] is None:
            values.append(None)
        else:
            values.append(row["duration_ms"] / 1000.0)
    return values


def wca_average(times):
    """The WCA average: drop the best and worst, mean the rest.

    A DNF counts as the worst attempt, so a single one is absorbed by the trim.
    Two or more make the whole average a DNF, which is returned as None.
    """
    if len(times) < 3:
        return None
    dnf_count = sum(1 for t in times if t is None)
    if dnf_count > 1:
        return None
    finished = sorted(t for t in times if t is not None)
    if dnf_count == 1:
        trimmed = finished[1:]          # the DNF is the discarded worst
    else:
        trimmed = finished[1:-1]
    if not trimmed:
        return None
    return sum(trimmed) / len(trimmed)


def rolling_average(times, window):
    """The most recent average over `window` attempts, or None if too few."""
    if len(times) < window:
        return None
    return wca_average(times[-window:])


def best_average(times, window):
    """The best average of `window` seen anywhere in the history."""
    if len(times) < window:
        return None
    averages = [
        wca_average(times[i:i + window])
        for i in range(len(times) - window + 1)
    ]
    finished = [a for a in averages if a is not None]
    return min(finished) if finished else None


def mean(times):
    finished = [t for t in times if t is not None]
    return sum(finished) / len(finished) if finished else None


def trimmed_mean(times):
    """Mean after discarding the best and worst, once there are enough to spare.

    Protects a per-case average from the single rep where the cube was dropped,
    without the WCA round structure that does not apply to drill reps.
    """
    finished = sorted(t for t in times if t is not None)
    if len(finished) < 5:
        return mean(times)
    kept = finished[1:-1]
    return sum(kept) / len(kept)


@dataclass(frozen=True)
class CaseReport:
    """What the history says about one case."""

    case_id: str
    attempts: int
    counted: int          # attempts behind the headline average
    mean: float
    trimmed_mean: float
    spread: float         # standard deviation, in seconds
    seconds_per_move: float
    peek_rate: float
    dnf_rate: float
    best: float

    @property
    def has_enough_data(self):
        """Below this, an average is noise dressed as a measurement."""
        return self.counted >= 5


def case_report(case_id, rows, move_count=None):
    """Summarise every recorded rep of one case.

    Peeked reps are excluded from the headline average -- a time achieved while
    reading the answer is not a time -- but they are counted, because how often
    you still need the answer is itself the most direct measure of a case you
    have not learned.
    """
    attempts = len(rows)
    if attempts == 0:
        return None
    peeks = sum(1 for r in rows if r["peeked"])
    dnfs = sum(1 for r in rows if r["penalty"] == "dnf")
    honest = [r for r in rows if not r["peeked"] and r["penalty"] != "dnf"]
    times = _durations(honest)
    finished = [t for t in times if t is not None]
    average = mean(times)
    return CaseReport(
        case_id=case_id,
        attempts=attempts,
        counted=len(finished),
        mean=average,
        trimmed_mean=trimmed_mean(times),
        spread=statistics.pstdev(finished) if len(finished) > 1 else 0.0,
        seconds_per_move=(average / move_count) if average and move_count else None,
        peek_rate=peeks / attempts,
        dnf_rate=dnfs / attempts,
        best=min(finished) if finished else None,
    )


def rank_by_weakness(reports, signal="seconds_per_move"):
    """Order cases worst-first by one of the reported signals.

    `seconds_per_move` is the default because raw time mostly ranks algorithms
    by length, which you already knew. Time per move asks the more useful
    question of how well you execute the algorithm you have.
    """
    valid = [r for r in reports if r is not None and getattr(r, signal) is not None]
    return sorted(valid, key=lambda r: getattr(r, signal), reverse=True)


def phase_summary(split_rows):
    """Mean and count for each phase across every solve that recorded it."""
    by_phase = {}
    for row in split_rows:
        by_phase.setdefault(row["phase"], []).append(row["duration_ms"] / 1000.0)
    return {
        phase: {
            "count": len(values),
            "mean": sum(values) / len(values),
            "best": min(values),
        }
        for phase, values in sorted(by_phase.items())
    }


def solve_summary(solve_rows):
    """Headline numbers for a run of full solves."""
    times = _durations(solve_rows)
    finished = [t for t in times if t is not None]
    return {
        "count": len(times),
        "mean": mean(times),
        "best": min(finished) if finished else None,
        "ao5": rolling_average(times, 5),
        "ao12": rolling_average(times, 12),
        "best_ao5": best_average(times, 5),
        "best_ao12": best_average(times, 12),
    }
