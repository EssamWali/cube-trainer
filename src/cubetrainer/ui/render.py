"""Drawing a last-layer case.

The picture is drawn from the cube state the trainer built, never from a stored
image. A case picture and the scramble that produces it therefore cannot
disagree: there is only one source for both.

The layout is the one every last-layer diagram uses: the upper face seen from
above, ringed by the side stickers of the pieces in it.

How it is coloured follows from what the state is. A last layer already
oriented is a permutation case, so it is drawn in true colours with arrows
showing where each piece has to go. A last layer not yet oriented is an
orientation case, so it is drawn in two tones -- facing up, or not -- and no
arrows, because an arrow says where a piece has to travel and an orientation
case is not about where anything travels. Both readings come from the same
state, which is why the picture and the scramble cannot disagree.
"""

import math

import pygame

from ..cases.pattern import CENTRE_U, is_last_layer_oriented, u_layer_permutation
from .theme import (ACCENT, FACE_COLOURS, GRID_LINE, HIDDEN, ORIENTED, READY,
                    TEXT, TEXT_DIM, TILE, TILE_FOCUS, UNORIENTED, font)

# Slot positions on the 3x3 grid, as (row, column) with row 0 at the back.
# Order matches CORNER_SLOTS and EDGE_SLOTS in cases.pattern.
CORNER_GRID = ((0, 0), (0, 2), (2, 2), (2, 0))
EDGE_GRID = ((0, 1), (1, 2), (2, 1), (1, 0))

# Side stickers of the last layer, as (facelet index, grid row, grid column,
# which edge of that cell the tab sits on).
SIDE_TABS = (
    (47, 0, 0, "top"), (46, 0, 1, "top"), (45, 0, 2, "top"),
    (11, 0, 2, "right"), (10, 1, 2, "right"), (9, 2, 2, "right"),
    (18, 2, 0, "bottom"), (19, 2, 1, "bottom"), (20, 2, 2, "bottom"),
    (36, 0, 0, "left"), (37, 1, 0, "left"), (38, 2, 0, "left"),
)


def _frame(rect):
    """The square the upper face occupies, one cell's width, and the tab depth."""
    size = min(rect.width, rect.height)
    tab = size * 0.11
    inner = pygame.Rect(0, 0, size - 2 * tab, size - 2 * tab)
    inner.center = rect.center
    return inner, inner.width / 3, tab


def face_grid(rect):
    """The nine upper-face cells, row by row from the back.

    Where a sticker is drawn is worked out here rather than inside the drawing
    loop, so a test can ask the diagram where it put something instead of
    redoing the arithmetic and silently disagreeing with it.
    """
    inner, cell, _ = _frame(rect)
    return [pygame.Rect(round(inner.left + column * cell),
                        round(inner.top + row * cell),
                        math.ceil(cell), math.ceil(cell))
            for row in range(3) for column in range(3)]


def draw_case(surface, cube, rect, arrows=True, hidden=False):
    """Draw the last layer of `cube` inside `rect`.

    With `hidden`, the shape is drawn blank. A drill that shows you the case has
    already answered the harder half of the question, so recognition is only
    trained when the picture stays covered until you ask for it.

    `arrows` asks for permutation arrows where they mean something; an
    orientation case never gets them.
    """
    two_tone = not is_last_layer_oriented(cube)

    def sticker(index):
        if hidden:
            return HIDDEN
        if two_tone:
            up = cube.facelets[CENTRE_U]
            return ORIENTED if cube.facelets[index] == up else UNORIENTED
        return FACE_COLOURS[cube.facelets[index]]

    inner, cell, tab = _frame(rect)
    cells = face_grid(rect)

    for position, base in enumerate(cells):
        pygame.draw.rect(surface, sticker(position), base)
        pygame.draw.rect(surface, GRID_LINE, base, 2)

    for index, row, column, side in SIDE_TABS:
        base = cells[row * 3 + column]
        thickness = max(4, round(tab * 0.72))
        gap = max(2, round(tab * 0.18))
        if side == "top":
            area = pygame.Rect(base.left, base.top - thickness - gap, base.width, thickness)
        elif side == "bottom":
            area = pygame.Rect(base.left, base.bottom + gap, base.width, thickness)
        elif side == "left":
            area = pygame.Rect(base.left - thickness - gap, base.top, thickness, base.height)
        else:
            area = pygame.Rect(base.right + gap, base.top, thickness, base.height)
        pygame.draw.rect(surface, sticker(index), area)
        pygame.draw.rect(surface, GRID_LINE, area, 1)

    if arrows and not hidden and not two_tone:
        _draw_permutation_arrows(surface, cube, inner, cell)


def _centre_of(grid_position, inner, cell):
    row, column = grid_position
    return (inner.left + (column + 0.5) * cell, inner.top + (row + 0.5) * cell)


def _draw_permutation_arrows(surface, cube, inner, cell):
    """One arrow per displaced piece, from where it is to where it belongs."""
    try:
        corners, edges = u_layer_permutation(cube)
    except ValueError:
        return  # not a last-layer case; nothing meaningful to point at
    for permutation, grid in ((corners, CORNER_GRID), (edges, EDGE_GRID)):
        for slot, home in enumerate(permutation):
            if slot == home:
                continue
            start = _centre_of(grid[slot], inner, cell)
            end = _centre_of(grid[home], inner, cell)
            _draw_arrow(surface, start, end, cell)


def arrow_shaft_width(cell):
    """How thick an arrow's shaft is drawn, for a face of `cell`-wide stickers.

    Deliberately thin. A case like the H perm crosses one small square with
    four arrows at once, and a heavy line turns that into a scribble nobody
    can trace a single piece through. The head carries the meaning; the shaft
    only has to be followable.
    """
    return max(1, round(cell * 0.045))


def _draw_arrow(surface, start, end, cell):
    """One arrow, from where a piece is to where it belongs.

    The shaft stops where the head begins rather than running under it, so the
    head stays a clean triangle instead of a blob with a line through it.
    """
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    inset = cell * 0.22
    span = length - 2 * inset
    if span <= 0:
        return
    # A hop to the next sticker leaves little room. The head gives way rather
    # than overrunning the tail, so that even the shortest arrow keeps a shaft
    # long enough to say which two stickers it joins.
    barb = min(cell * 0.28, span * 0.5)
    tail = (start[0] + ux * inset, start[1] + uy * inset)
    head = (end[0] - ux * inset, end[1] - uy * inset)
    neck = (head[0] - ux * barb, head[1] - uy * barb)
    pygame.draw.line(surface, GRID_LINE, tail, neck, arrow_shaft_width(cell))
    spread = barb * 0.42
    left = (neck[0] - uy * spread, neck[1] + ux * spread)
    right = (neck[0] + uy * spread, neck[1] - ux * spread)
    pygame.draw.polygon(surface, GRID_LINE, [head, left, right])


def draw_thumbnail(surface, cube, rect, label, cursor=False, chosen=False,
                   dim=False):
    """A small case picture with its name, for the picker and the library.

    Two separate facts share one tile: whether the cursor is on it, and whether
    it has been chosen to drill. They get different marks -- the tile's own
    border for chosen, a ring inside it for the cursor -- because a cuber
    reading the grid has to see both at once, including on the tile where they
    coincide.
    """
    pygame.draw.rect(surface, TILE_FOCUS if cursor else TILE, rect, border_radius=6)
    if chosen:
        pygame.draw.rect(surface, READY, rect, 2, border_radius=6)
    if cursor:
        pygame.draw.rect(surface, ACCENT, rect.inflate(-6, -6), 2, border_radius=4)
    picture = pygame.Rect(0, 0, rect.width - 16, rect.height - 30)
    picture.midtop = (rect.centerx, rect.top + 6)
    draw_case(surface, cube, picture, arrows=True)
    rendered = font(15, bold=cursor).render(label, True, TEXT_DIM if dim else TEXT)
    surface.blit(rendered, rendered.get_rect(midbottom=(rect.centerx, rect.bottom - 5)))
