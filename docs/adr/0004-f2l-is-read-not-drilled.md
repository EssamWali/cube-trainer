# F2L is read, not drilled

The trainer ships all 41 F2L cases with algorithms and a library to browse them
in, and does not offer an F2L drill. OLL and PLL are drilled.

## Why

Every drill works the same way: it hands out a scramble and asks the cuber to
apply it to a solved cube. That is what makes the trainer's promise checkable —
apply this and you are holding exactly that case — and for the last layer it is
also how a cuber genuinely meets those cases. You finish F2L, you look at the
top, and there is a case.

F2L is not met that way. You meet an F2L case with the cross built and pairs
still scattered, having just put the one before it in. Reaching a single F2L
case from a solved cube means undoing one pair and nothing else, which is fiddly
to set up by hand, and what you are then looking at is a nearly-solved cube with
one pair out. Recognising a case on that is not the recognition the drill is
supposed to train, and the reps it records would be times for something a cuber
never actually does.

So the drill would have been measuring the wrong thing, accurately.

## What is kept

Everything except the drill. The 41 cases, their algorithms, the families they
are taught in, and the picture — an F2L case still draws as a cube seen from a
corner. They are reachable through the library, which is the picker in browse
mode, and any of them can be replaced with a cuber's own algorithm. Someone
learning F2L algorithms has what they need to read and memorise them.

The reading in `cases.pattern` stays too, and stays tested. It is what checks
the case list is complete and what the picture is drawn from; neither depends on
there being a drill.

**F2L stays a phase you can time.** Pressing at the F2L boundary while timing a
solve is unaffected, and is the honest way to measure F2L: on a real solve,
where the case arrives the way it does.

## Consequences

A `Catalogue` says whether its phase is drilled. The home screen builds a
library for every catalogue it is handed and a drill for each one that says it
is drilled, so the screens still name no phase and adding one is still data.

The statistics rank only phases that are drilled. A ranking of a phase nobody
can drill is a page that is always empty, for a reason the cuber cannot see.

If F2L drilling is ever wanted, the thing to change is not this flag but the
scramble: a drill that put the cuber in front of a cross and three empty slots
would be measuring the right thing, and would need a scramble generator that
does not start from a solved cube.
