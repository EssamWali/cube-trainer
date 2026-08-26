"""Colours and type for the interface."""

import pygame

# Sticker colours, in the orientation cubers actually hold: yellow on top,
# because a last-layer diagram is what you see looking down at a solved cross.
FACE_COLOURS = {
    "U": (255, 213, 0),     # yellow, the last layer
    "D": (245, 245, 245),   # white
    "F": (0, 155, 72),      # green
    "B": (0, 70, 173),      # blue
    "R": (183, 18, 52),     # red
    "L": (255, 88, 0),      # orange
}

BACKGROUND = (18, 20, 24)
PANEL = (28, 31, 37)
GRID_LINE = (12, 13, 16)
TEXT = (236, 238, 242)
TEXT_DIM = (140, 148, 160)
ACCENT = (94, 168, 255)
ARMED = (240, 180, 40)
READY = (60, 200, 110)
RUNNING = (236, 238, 242)
DANGER = (232, 84, 84)
HIDDEN = (58, 63, 72)

_CACHE = {}


def reset_fonts():
    """Forget every cached font.

    A Font belongs to the pygame session that created it, and using one after
    pygame has been shut down and started again crashes the interpreter rather
    than raising. Anything that re-initialises pygame must call this first.
    """
    _CACHE.clear()


def font(size, bold=False):
    """A cached font. pygame reloads on every call otherwise, which shows."""
    key = (size, bold)
    if key not in _CACHE:
        loaded = pygame.font.SysFont("consolas,dejavusansmono,couriernew", size, bold=bold)
        _CACHE[key] = loaded
    return _CACHE[key]


def text(surface, message, position, size=20, colour=TEXT, bold=False,
         centre=False, right=False):
    """Draw a line of text and return its rect."""
    rendered = font(size, bold).render(str(message), True, colour)
    rect = rendered.get_rect()
    if centre:
        rect.midtop = position
    elif right:
        rect.topright = position
    else:
        rect.topleft = position
    surface.blit(rendered, rect)
    return rect


def format_time(seconds):
    """Times the way a cuber reads them: 1.83, or 1:04.27 past a minute."""
    if seconds is None:
        return "DNF"
    if seconds >= 60:
        minutes, remainder = divmod(seconds, 60)
        return f"{int(minutes)}:{remainder:05.2f}"
    return f"{seconds:.2f}"
