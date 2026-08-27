# Cube Trainer

A local desktop application that generates targeted scrambles and times a
cuber's practice on a physical 3x3 cube. The application never observes the
cube while it is being solved; everything it knows about the cube's state it
knows because it constructed that state itself.

## Language

### The cube

**Facelet**:
One of the 54 coloured stickers on a 3x3 cube.

**Move**:
A single turn, written in standard notation: a face (`R`), a slice (`M`), a wide
turn (`r`) or a whole-cube rotation (`y`).

**Sequence**:
An ordered list of moves.
_Avoid_: Algorithm, which is reserved for a sequence that solves a case.

**Rotation**:
A move that turns the whole cube rather than a layer, changing how it is held
without changing what is solved.

**Slot**:
One of the four places in the first two layers where a corner and an edge sit
together, named for the two faces it lies between: `FR`, `FL`, `BL`, `BR`. The
cross and four filled slots are the first two layers.

**Pair**:
The corner and the edge that belong in one slot. What an F2L case is about:
where the pair's two pieces are and which way round each of them is. Read
relative to the slot, so the same case in any of the four reads the same.

**Scramble**:
The sequence handed to the cuber to apply to a solved cube before an attempt.
Always free of rotations, so the last layer is always the layer on top.

**AUF**:
Adjust Upper Face. A quarter or half turn of the top layer that changes the
angle a case is seen from without changing which case it is.

### Practice

**Phase**:
One stage of the CFOP method: Cross, F2L, OLL or PLL.

**Case**:
A configuration a phase can present, identified by name — `T perm`, `OLL 21`.
There are 21 PLL cases, 57 OLL cases and 41 F2L cases.

**Case Set**:
A named group of cases a cuber has chosen to work on. Belongs to one phase, so
two phases can each have a set of the same name.

**Group**:
A family of cases that look alike and are therefore learned and recognised
together: the fish shapes, the G perms, the pair still up in the top layer. Some
are structural facts about the cube — every edge already oriented, both pieces
of the pair still in the slot — and the rest are silhouettes, which is a fact
about how a case looks rather than one the cube can be asked about.

**Catalogue**:
Every case of one phase, together with the phase's name, the order its groups
are shown in, and whether the phase is drilled. What a screen is handed instead
of a case list, so that adding a phase is data rather than a change to every
screen.

**Drilled phase**:
A phase whose cases a drill can hand out, because a scramble applied to a solved
cube is a fair way to meet them. OLL and PLL are; F2L is not, and has a
catalogue for its algorithms without a drill.

**Algorithm**:
A sequence that solves one case and leaves the cube held as it was picked up. A
case may have several; a cuber picks which one is theirs.

**Setup**:
The sequence that turns a solved cube into a given case. Its inverse is the
algorithm, which is what lets the trainer promise a scramble lands on a case it
can name.

**Drill**:
Repeated timed attempts at cases drawn from a chosen case set, one case at a
time, continuing until the cuber stops.
_Avoid_: Grill.

**Rep**:
One timed attempt at one known case during a drill. Has a case; has no phases.

**Solve**:
One timed attempt at a scrambled cube. Has phases; has no case, because which
case arises depends on how the cuber chose to build F2L, which the application
never sees.

**Whole solve**:
A solve run all the way to a solved cube. Only these reach the solve averages. A
run that stops at an earlier boundary — timing only the cross, say — is the same
activity with fewer boundaries and is recorded the same way, but stays out of
those averages and keeps its splits instead: a cross time is a time, and
averaged in with solve times it makes a number about nothing. It also leaves the
cuber holding a part-solved cube, which the next scramble cannot assume.

**Session**:
One sitting at the timer: a single drill, or a single run of solves.

**Peek**:
Revealing a case and its algorithm during a rep. Recorded, and keeps that rep
out of the headline average, because a time achieved while reading the answer
is not a time.

**Multi-phase timing**:
Timing a solve as separate phases by having the cuber signal each boundary,
rather than recording one duration. Timing only the cross is this with a single
boundary, not a separate activity.

**Boundary**:
A point in a solve where the cuber presses the timer, closing one split and
starting the next. Which boundaries a run has is chosen before it starts, and
the run ends at the last of them. One boundary, at the end, is a plain timer.

**Split**:
The time between two boundaries, recorded under the phases it covers. A phase
nobody asked for a boundary at is not lost — it is folded into the next split
and named there, so a run with boundaries at Cross and PLL records a `Cross`
split and an `F2L+OLL+PLL` one, because that is honestly what the second
covers.
