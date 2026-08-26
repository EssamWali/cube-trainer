# Case data is checked against the cube group, not against its own algorithms

Every scramble the trainer hands out is the inverse of a case's algorithm. That
makes "the algorithm solves this scramble" true by construction and therefore
worthless as a test: a mistyped algorithm would generate the scramble for the
mistyped case and pass. The case data is instead checked against facts derived
from the structure of the cube itself.

## What is actually checked

The test suite enumerates every last-layer permutation the cube group permits
— 288 states, which fall into 22 classes under upper-face adjustment and
whole-cube rotation, 21 of them unsolved. It then requires that the 21 shipped
cases cover those 21 classes exactly once, that each produces a state with the
first two layers intact and the last layer oriented, and that each case sits on
the correct side of a structural line: four PLLs form two inverse pairs and the
other thirteen are their own inverse. None of those facts comes from the
algorithm list, so a typo in an algorithm breaks one of them.

## Consequences

Algorithms can be sourced from anywhere, including transcription by hand from a
video, because a transcription error is caught rather than trusted. This is
what makes it safe to ship a curated set and let a cuber replace any of it with
their own.

Two related constraints follow, and both are enforced by tests:

- **Algorithms must end with the cube held as it was picked up.** Some published
  algorithms include a regrip and never turn back. Left that way they are
  ambiguous as data, because which case they solve depends on how you were
  holding the cube when you finished. The E perm and V perm entries carry an
  explicit closing rotation for this reason.
- **Scrambles must contain no rotations at all.** A scramble is rewritten into a
  rotationless equivalent before it is shown, so the last layer is always the
  layer on top. Without this the case diagram and the cube in the cuber's hands
  can disagree — which is exactly how the bug was found.
