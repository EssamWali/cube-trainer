# Cube Trainer

Targeted scramble generation and timing for practising CFOP on a physical 3x3.

Pick the PLL cases you want to work on. The trainer hands you a scramble that
leaves a solved cube showing exactly one of them, hides which one it is, and
times you WCA-style while you recognise and solve it. It records every rep, so
it can tell you which cases you are actually slow at rather than which
algorithms happen to be long.

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

**Drill PLL** — choose cases, then drill them.

| key | |
| --- | --- |
| arrows | move around the grid |
| `space` | toggle the case under the cursor |
| `g` | toggle its whole group |
| `a` / `n` | select all / none |
| `s` / `o` | save the selection under a name / open a saved one |
| `enter` | start drilling |

In the drill, hold `space` until it turns green, release to start, and press it
again when the cube is solved. The case is hidden while you work: recognising
it is most of the skill. Press `p` to reveal it and its algorithm — that rep is
still recorded, but marked as peeked and left out of your averages.

Press `d` if you fumble. Every scramble assumes you are starting from a solved
cube, and a misexecuted algorithm leaves the cube somewhere the trainer cannot
follow, so the rep is logged as a DNF and you solve your cube before continuing.

**Algorithm library** — the same grid, browsable, with each case's algorithm.

**Statistics** — every drilled case, ranked. Weakness is shown as five separate
numbers rather than one score, because a case can be slow, erratic, still being
looked up, or dropped often, and those need different practice. `tab` changes
which one the ranking uses. The default is seconds per move: ranking by raw
time mostly tells you which algorithms are long, which you already knew.

## How it works

Every scramble is the inverse of a case's algorithm, applied to a solved cube.
That is what makes the promise checkable — and it is also why the cube has to
start solved every time.

The move engine is derived geometrically in 3D rather than written as tables of
facelet indices, so face turns, slices, wide moves and rotations all come from
one definition. It is cross-checked against `kociemba`, an unrelated solver.

The case data is not checked against its own algorithms, which would be
circular. It is checked against the cube group: the tests enumerate all 21
last-layer permutation classes and require the shipped cases to cover them
exactly once. See [docs/adr](docs/adr) for that and for why this is a desktop
application rather than a web page.

## Tests

```
pip install -e ".[dev]"
pytest
```

## Not built yet

OLL, full-solve timing with phase splits, and cross drills. The domain layer
already carries them — the timer takes any number of phases, the store records
splits as their own rows — but the screens are PLL only for now.
