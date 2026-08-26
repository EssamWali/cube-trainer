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
There are 21 PLL cases and 57 OLL cases.

**Case Set**:
A named group of cases a cuber has chosen to work on.

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
One timed attempt at a whole scrambled cube. Has phases; has no case, because
which case arises depends on how the cuber chose to build F2L, which the
application never sees.

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
