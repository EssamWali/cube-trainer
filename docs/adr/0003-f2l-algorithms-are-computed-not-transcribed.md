# F2L algorithms are computed, not transcribed

The 41 F2L algorithms are found by search: the shortest way to solve each case
using the triggers that turn one slot and put everything else back. The other
phases' algorithms were transcribed from what cubers use.

## Why

F2L is not like the last layer. PLL and OLL have a case list everybody agrees
on, names people say out loud, and algorithms that are genuinely standard, so
transcribing them is transcribing something real. F2L has none of that: most
cubers build their pairs by working it out rather than by recognising a case and
firing, published lists of "the 41 algorithms" disagree with each other, and the
cases have no names.

So there was no single right list to copy. Searching for the shortest solution
out of the standard triggers produces algorithms that are correct, short, and
made of the same moves a cuber would use — the four basic inserts come out as
`R U' R'`, `R U R'`, `F' U' F` and `F' U F`, and the longer ones as trigger
pairs like `R U2 R' F' U2 F`. Where a cuber prefers their own, they can set it
in the library.

## What this costs

ADR 0002 says case data is checked against the cube group rather than against
its own algorithms, because "the algorithm solves this scramble" is true by
construction and therefore worthless as a test. Computing the algorithms makes
more of the F2L tests true by construction in exactly that way, and it is worth
being plain about which:

**Still worth something.** That the case list covers all 41 classes exactly
once, checked against an enumeration derived from the cube group. That there are
41 and not 40. That every case is a genuine F2L state — cross intact, three
slots done, this one not. That the families have the sizes the enumeration
gives them. That no setup asks the cuber to rotate the cube. That every
algorithm leaves the cube as it was picked up. These catch a table assembled
wrongly, a search run against the wrong slot, or a reading that quietly folds
two cases into one.

**Now true by construction.** That each algorithm solves its own setup, and
that each case's family is the one the cube puts it in. Both are properties the
generator enforces. They are kept because they will start being worth something
again the moment anyone edits an algorithm by hand, but nobody should mistake
them for evidence today.

**The real check is the reading**, in `cases.pattern`, whose ground truth is
derived twice from directions that could disagree: as arithmetic over the ways a
pair can sit, and by exhausting a real cube's own triggers. Both say 42. If that
reading is right, a case list measured against it is right.

## Consequences

An F2L case declares no inverse. "The case that undoes this one" is a last-layer
idea: undoing an insert takes the pair back out, which is a case, but not
something a cuber says or a fact worth writing down 41 times. `Case.inverse`
became optional, and a case that does not declare one is not treated as its own
inverse. PLL and OLL still declare one and it is still checked.

If someone later transcribes a curated list, the tests that are true by
construction start earning their keep again and this decision can be revisited
without anything else moving.
