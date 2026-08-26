# A Python desktop application, not a web app

The trainer is a local pygame application in Python, distributed as source on
GitHub. A stranger who wants to use it has to install Python and the
dependencies and run a script.

## Considered options

A browser application served from GitHub Pages was the obvious alternative and
would have been better on one axis that genuinely matters: a stranger clicks a
link and it works, on any machine, including a phone. It needs no hosting and
no CI — GitHub Pages serves a static site straight from the repository — so the
usual objection to it does not apply.

Three requirements were in play and no option satisfied all three:

1. written in Python
2. zero friction for someone who finds the repository
3. durable local statistics in SQLite

A pygame desktop application gets 1 and 3. A browser application gets 2, and
only an approximation of 3, because browser storage is per-browser,
per-device, and can be cleared. Compiling the pygame application to
WebAssembly with pygbag would have got 1 and 2 while losing 3 anyway, and
would have added a fragile toolchain to debug alongside the application.

## Consequences

Sharing is the thing being given up, deliberately, and it is the requirement
this project is worst at. The statistics are the compensation: they are real
SQLite, queryable, and they will still be there in a year. Nothing about the
domain layer assumes pygame — the engine, the case data, the scramble
generation, the timer and the store have no import from `ui/` — so a future
web front end would be a rewrite of one package rather than of the project.
