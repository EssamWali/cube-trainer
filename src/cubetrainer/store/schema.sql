-- A sitting at the timer: one drill, or one run of full-solve timing.
-- Scoped this way so "my average this session" is a number about one activity
-- rather than a bucket mixing drilling and solving.
CREATE TABLE IF NOT EXISTS session (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('drill', 'solve')),
    phase       TEXT,
    started_at  TEXT NOT NULL,
    ended_at    TEXT
);

-- One attempt at one known case. Reps know their case because the trainer
-- built it; full solves never do.
CREATE TABLE IF NOT EXISTS rep (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    case_id     TEXT NOT NULL,
    scramble    TEXT NOT NULL,
    duration_ms INTEGER,
    peeked      INTEGER NOT NULL DEFAULT 0,
    penalty     TEXT NOT NULL DEFAULT 'none',
    recorded_at TEXT NOT NULL
);

-- One full solve of a scrambled cube. Has phases; has no case.
CREATE TABLE IF NOT EXISTS solve (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    scramble    TEXT NOT NULL,
    duration_ms INTEGER,
    penalty     TEXT NOT NULL DEFAULT 'none',
    recorded_at TEXT NOT NULL
);

-- One recorded phase of one solve. A table rather than four columns on `solve`
-- because a cuber may time only the cross, and a null column meaning "not
-- timed" is a variant hiding inside a schema.
CREATE TABLE IF NOT EXISTS phase_split (
    id          INTEGER PRIMARY KEY,
    solve_id    INTEGER NOT NULL REFERENCES solve(id) ON DELETE CASCADE,
    phase       TEXT NOT NULL,
    ordinal     INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL
);

-- A named selection of cases, so choosing eight OLLs is done once, not nightly.
CREATE TABLE IF NOT EXISTS case_set (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    phase   TEXT NOT NULL,
    UNIQUE (name, phase)
);

CREATE TABLE IF NOT EXISTS case_set_member (
    case_set_id INTEGER NOT NULL REFERENCES case_set(id) ON DELETE CASCADE,
    case_id     TEXT NOT NULL,
    PRIMARY KEY (case_set_id, case_id)
);

-- The cuber's own algorithm for a case, kept apart from the shipped defaults
-- so updating the application never overwrites what someone has learned.
CREATE TABLE IF NOT EXISTS algorithm_override (
    case_id    TEXT PRIMARY KEY,
    algorithm  TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS rep_by_case ON rep (case_id);
CREATE INDEX IF NOT EXISTS rep_by_session ON rep (session_id);
CREATE INDEX IF NOT EXISTS split_by_solve ON phase_split (solve_id);
CREATE INDEX IF NOT EXISTS split_by_phase ON phase_split (phase);
