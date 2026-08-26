"""SQLite persistence.

A timer that forgets is a stopwatch. Everything the trainer measures lands
here raw: durations, penalties, whether the cuber peeked. Statistics are
computed on the way out rather than on the way in, so changing what counts as
a weak case never means having recorded the wrong thing.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")

DEFAULT_PATH = Path.home() / ".cube-trainer" / "history.sqlite3"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ms(seconds):
    return None if seconds is None else int(round(seconds * 1000))


class Store:
    """A cuber's practice history."""

    def __init__(self, path=None):
        if path is None:
            path = DEFAULT_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    @classmethod
    def in_memory(cls):
        return cls(":memory:")

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # -- sessions ---------------------------------------------------------
    def start_session(self, kind, phase=None):
        cursor = self.connection.execute(
            "INSERT INTO session (kind, phase, started_at) VALUES (?, ?, ?)",
            (kind, phase, _now()),
        )
        self.connection.commit()
        return cursor.lastrowid

    def end_session(self, session_id):
        self.connection.execute(
            "UPDATE session SET ended_at = ? WHERE id = ?", (_now(), session_id)
        )
        self.connection.commit()

    def sessions(self):
        return [dict(r) for r in self.connection.execute(
            "SELECT * FROM session ORDER BY id"
        )]

    # -- attempts ---------------------------------------------------------
    def record_rep(self, session_id, case_id, scramble, duration,
                   peeked=False, penalty="none"):
        """Store one drill rep. A DNF has no duration, which is the truth."""
        duration_ms = None if penalty == "dnf" else _ms(duration)
        cursor = self.connection.execute(
            "INSERT INTO rep (session_id, case_id, scramble, duration_ms, peeked,"
            " penalty, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, case_id, scramble, duration_ms, int(peeked), penalty, _now()),
        )
        self.connection.commit()
        return cursor.lastrowid

    def record_solve(self, session_id, scramble, duration, splits=(), penalty="none"):
        """Store one full solve and whichever phases were timed."""
        duration_ms = None if penalty == "dnf" else _ms(duration)
        cursor = self.connection.execute(
            "INSERT INTO solve (session_id, scramble, duration_ms, penalty,"
            " recorded_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, scramble, duration_ms, penalty, _now()),
        )
        solve_id = cursor.lastrowid
        self.connection.executemany(
            "INSERT INTO phase_split (solve_id, phase, ordinal, duration_ms)"
            " VALUES (?, ?, ?, ?)",
            [(solve_id, phase, i, _ms(seconds))
             for i, (phase, seconds) in enumerate(splits)],
        )
        self.connection.commit()
        return solve_id

    # -- reading ----------------------------------------------------------
    def reps(self, case_id=None, session_id=None, phase=None):
        """Stored reps, oldest first.

        A rep records which case it was and not which phase, because the
        session it belongs to already knows. Recovering the phase by joining
        beats writing the same fact down twice and letting the two disagree.
        """
        sql = "SELECT rep.* FROM rep"
        clauses, params = [], []
        if phase is not None:
            sql += " JOIN session ON session.id = rep.session_id"
            clauses.append("session.phase = ?")
            params.append(phase)
        if case_id is not None:
            clauses.append("rep.case_id = ?")
            params.append(case_id)
        if session_id is not None:
            clauses.append("rep.session_id = ?")
            params.append(session_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY rep.id"
        return [dict(r) for r in self.connection.execute(sql, params)]

    def solves(self, session_id=None):
        sql = "SELECT * FROM solve"
        params = []
        if session_id is not None:
            sql += " WHERE session_id = ?"
            params.append(session_id)
        sql += " ORDER BY id"
        return [dict(r) for r in self.connection.execute(sql, params)]

    def splits(self, phase=None):
        """Every recorded phase split, optionally for one phase only."""
        sql = ("SELECT phase_split.*, solve.recorded_at FROM phase_split"
               " JOIN solve ON solve.id = phase_split.solve_id")
        params = []
        if phase is not None:
            sql += " WHERE phase_split.phase = ?"
            params.append(phase)
        sql += " ORDER BY phase_split.solve_id, phase_split.ordinal"
        return [dict(r) for r in self.connection.execute(sql, params)]

    def practised_case_ids(self, phase=None):
        """Every case that has ever been drilled, optionally in one phase."""
        sql = "SELECT DISTINCT rep.case_id FROM rep"
        params = []
        if phase is not None:
            sql += (" JOIN session ON session.id = rep.session_id"
                    " WHERE session.phase = ?")
            params.append(phase)
        sql += " ORDER BY rep.case_id"
        return [r["case_id"] for r in self.connection.execute(sql, params)]

    # -- case sets --------------------------------------------------------
    def save_case_set(self, name, phase, case_ids):
        existing = self.connection.execute(
            "SELECT id FROM case_set WHERE name = ? AND phase = ?", (name, phase)
        ).fetchone()
        if existing is None:
            cursor = self.connection.execute(
                "INSERT INTO case_set (name, phase) VALUES (?, ?)", (name, phase)
            )
            set_id = cursor.lastrowid
        else:
            set_id = existing["id"]
            self.connection.execute(
                "DELETE FROM case_set_member WHERE case_set_id = ?", (set_id,)
            )
        self.connection.executemany(
            "INSERT INTO case_set_member (case_set_id, case_id) VALUES (?, ?)",
            [(set_id, case_id) for case_id in case_ids],
        )
        self.connection.commit()
        return set_id

    def load_case_set(self, name, phase):
        row = self.connection.execute(
            "SELECT id FROM case_set WHERE name = ? AND phase = ?", (name, phase)
        ).fetchone()
        if row is None:
            return None
        members = self.connection.execute(
            "SELECT case_id FROM case_set_member WHERE case_set_id = ?"
            " ORDER BY case_id", (row["id"],)
        )
        return [m["case_id"] for m in members]

    def case_set_names(self, phase):
        rows = self.connection.execute(
            "SELECT name FROM case_set WHERE phase = ? ORDER BY name", (phase,)
        )
        return [r["name"] for r in rows]

    def delete_case_set(self, name, phase):
        self.connection.execute(
            "DELETE FROM case_set WHERE name = ? AND phase = ?", (name, phase)
        )
        self.connection.commit()

    # -- algorithms -------------------------------------------------------
    def set_algorithm(self, case_id, algorithm):
        """Record a cuber's own algorithm for a case.

        Kept in its own table rather than edited into the shipped data, so
        updating the application never overwrites what someone has learned.
        """
        self.connection.execute(
            "INSERT INTO algorithm_override (case_id, algorithm, updated_at)"
            " VALUES (?, ?, ?) ON CONFLICT (case_id) DO UPDATE SET"
            " algorithm = excluded.algorithm, updated_at = excluded.updated_at",
            (case_id, algorithm, _now()),
        )
        self.connection.commit()

    def clear_algorithm(self, case_id):
        self.connection.execute(
            "DELETE FROM algorithm_override WHERE case_id = ?", (case_id,)
        )
        self.connection.commit()

    def algorithm_overrides(self):
        rows = self.connection.execute(
            "SELECT case_id, algorithm FROM algorithm_override"
        )
        return {r["case_id"]: r["algorithm"] for r in rows}
