"""Test configuration.

pygame is driven headlessly so the interface can be exercised in CI and on a
machine with no display. The dummy driver has to be chosen before pygame opens
a window, which is why this sits in conftest rather than in a test module.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
