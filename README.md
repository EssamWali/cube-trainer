# Cube Trainer

Targeted scramble generation and timing for practising CFOP on a physical 3x3.

Pick the OLL or PLL cases you want to work on. The trainer hands you a scramble
that leaves a solved cube showing exactly one of them, hides which one it is,
and times you WCA-style while you recognise and solve it. It records every rep,
so it can tell you which cases you are actually slow at rather than which
algorithms happen to be long.

It times whole solves too, split at whichever phase boundaries you want to press
at — including just the one, which is how you drill your cross.

The cube stays in your hands. The application never sees it.

## Running it

```
pip install -e .
cube-trainer
```

Python 3.10 or newer. The only runtime dependency is pygame.

By default your history is written to `~/.cube-trainer/history.sqlite3`. Pass a
path to use a different one:

```
cube-trainer practice.sqlite3
```

## Using it

**Drill PLL** and **Drill OLL** — choose cases, then drill them. It is the same
screen and the same keys for both, because it is the same drill; only the cases
differ. A case set you save belongs to the phase you saved it in, so "hard" can
mean one thing in PLL and another in OLL.

| key | |
| --- | --- |
| arrows | move around the grid |
| `space` | toggle the case under the cursor |
| `g` | toggle its whole group |
| `a` / `n` | select all / none |
| `s` / `o` | save the selection under a name / open a saved one |
| `enter` | start drilling |

Nothing is selected to begin with, so choosing three cases is three keypresses
rather than eighteen. Chosen cases are ringed in green; the cursor is the ring
inside the tile. Your last selection comes back next time you open the picker.

Cases are grouped the way they are taught — five families for PLL, fifteen for
OLL — because "I am slow at the fish shapes" is a sentence someone says and "I
am slow at 9, 10, 35, 37" is not. `g` takes a whole family at once.

In the drill, hold `space` until it turns green, release to start, and press it
again when the cube is solved. The case is hidden while you work: recognising
it is most of the skill. Press `p` to reveal it and its algorithm — that rep is
still recorded, but marked as peeked and left out of your averages.

Press `d` if you fumble. Every scramble assumes you are starting from a solved
cube, and a misexecuted algorithm leaves the cube somewhere the trainer cannot
follow, so the rep is logged as a DNF and you solve your cube before continuing.
Pressing `d` on a rep you have already stopped discards that rep instead: it
becomes the DNF, rather than gaining a second attempt beside it. `2` gives it
a +2 the same way.

**Time a solve** — a scramble, WCA inspection, and a timer that stops where you
tell it to.

It starts out as a plain timer: pick the cube up, put it down, read the number.
Press `enter` and go.

If you want your splits, tick the boundaries you want to press at first. All
four is a solve reported four ways. Cross alone is a cross drill: the same
screen and the same timer, stopping at the first press. A phase you leave
unticked is still being solved, so it is folded into the next split and named
there — tick Cross and PLL and your second press closes `F2L+OLL+PLL`, because
that is what it covers.

| key | |
| --- | --- |
| arrows | move between phases |
| `space` | tick the phase under the cursor |
| `a` | tick every phase |
| `n` | none on the way: back to one press at the end |
| `i` | inspection on or off, then `i` again to start inspecting |
| `enter` | start |

Then `i` to start your inspection, hold `space` to arm, and press it at each
boundary — or once, at the end, if you left it as a plain timer. Inspection runs by the WCA thresholds: over 15 seconds is a +2, over
17 is a DNF. `2` and `d` amend the attempt you just made.

A run that stops before the cube is solved leaves you holding a part-solved
cube, so it asks you to finish it before the next scramble — every scramble
here assumes a solved one too.

**Algorithm library** — the same grid, browsable, with each case's algorithm,
one entry per phase.

**F2L is here but is not drilled.** All 41 cases are in the library, drawn as a
cube seen from a corner, with algorithms to read and learn. There is no F2L
drill, because a drill hands you a scramble to apply to a solved cube and that
is not how you meet an F2L case — you meet one with the cross built and pairs
still scattered, and a nearly-solved cube with one pair out trains the wrong
recognition. See
[ADR 0004](docs/adr/0004-f2l-is-read-not-drilled.md). Timing the F2L phase of a
real solve is unaffected, and is the honest way to measure it.

F2L has no names everybody uses and no one published list of algorithms either,
so its cases are numbered and the ones shipped are the shortest solution to each
out of the standard triggers — see
[ADR 0003](docs/adr/0003-f2l-algorithms-are-computed-not-transcribed.md). Set
your own with `e`.

Press `e` to replace an algorithm with the one you actually use, and `r` to go
back to the shipped one. What you type is checked against the cube before it is
kept: it has to solve the case *and* give the cube back as you picked it up, so
an algorithm ending on a regrip you never take back is refused — left that way
it is ambiguous, because which case it solves depends on how you were holding
the cube when you finished. A refusal says what is wrong and keeps what you
typed. Your algorithm is what the drill reveals and what seconds per move is
counted against, and it lives in its own table, so updating the application
never overwrites it.

It does not change your scrambles. A scramble is the inverse of the case's
setup, not of the algorithm on screen.

**Statistics** — every drilled case, ranked. Weakness is shown as five separate
numbers rather than one score, because a case can be slow, erratic, still being
looked up, or dropped often, and those need different practice. `tab` changes
which one the ranking uses. The default is seconds per move: ranking by raw
time mostly tells you which algorithms are long, which you already knew.

One phase at a time, with the arrow keys to switch, over the phases that are
drilled. An OLL case and a PLL case in the same ranking would be two
incomparable things in one list.

Above the ranking: your solve count with its mean, ao5 and ao12, your best
single, ao5 and ao12 under those, and the mean of every phase split you have
recorded. An average you do not have enough solves for yet is left out rather
than shown as a DNF — three solves in, "ao5 DNF" would read as a failure that
never happened. Only whole solves reach the averages. A cross time is a time,
but averaged in with solve times it makes a number about nothing, so a run that
stopped early keeps its splits and stays out of the mean.

## How it works

Every scramble is the inverse of a case's algorithm, applied to a solved cube.
That is what makes the promise checkable — and it is also why the cube has to
start solved every time.

The move engine is derived geometrically in 3D rather than written as tables of
facelet indices, so face turns, slices, wide moves and rotations all come from
one definition. It is cross-checked against `kociemba`, an unrelated solver.

The picture follows from the state rather than from a stored image, which is
also what decides which of three pictures it gets, so no screen is ever asked
which one it wants. A cube with a slot still open is an F2L case, drawn as a
cube seen from a corner — half of the case is in the slot, underneath the layer
the other pictures draw — with the last layer greyed, because an F2L case says
nothing about it. A last layer already oriented is a permutation case, so it is
drawn in true colours with arrows saying where each piece has to go. One not yet
oriented is an orientation case, so it is drawn in the two tones that question
has answers, and no arrows — an arrow says where a piece travels, which is a
wrong answer about an OLL case.

The arrows are read with the AUF divided out, because a drill hands you the case
at a random one of its four angles. Read as "where does each piece belong", a T
perm met a quarter turn round has no piece at home and needs seven arrows; what
you would be shown then is the case plus an adjustment you have not made yet,
which is not a T perm and not worth practising against. So the arrows say where
each piece goes once you have adjusted the upper face, and two pieces that trade
places share one arrow with a head at each end.

The case data is not checked against its own algorithms, which would be
circular. It is checked against the cube group: the tests enumerate all 21
last-layer permutation classes, and all 57 orientation classes, and require the
shipped cases to cover them exactly once. See [docs/adr](docs/adr) for that and
for why this is a desktop application rather than a web page.

## Tests

```
pip install -e ".[dev]"
pytest
```

## Not built yet

Nothing named. All three phases drill, the timer splits a solve however you ask
it to, and the statistics rank each phase on its own.

