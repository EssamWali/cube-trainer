"""Drawing a last-layer case.

The picture is drawn from the cube state the trainer built, never from a stored
image. A case picture and the scramble that produces it therefore cannot
disagree: there is only one source for both.

The layout is the one every last-layer diagram uses: the upper face seen from
above, ringed by the side stickers of the pieces in it.

How it is coloured follows from what the state is. A last layer already
oriented is a permutation case, so it is drawn in true colours with arrows
showing where each piece has to go once the upper face is adjusted. A last
layer not yet oriented is an orientation case, so it is drawn in two tones --
facing up, or not -- and no arrows, because an arrow says where a piece has to
travel and an orientation case is not about where anything travels. Both
readings come from the same state, which is why the picture and the scramble
cannot disagree.
"""

import math

import pygame

from ..cases.pattern import CENTRE_U, is_last_layer_oriented, u_layer_cycles
from .theme import (ACCENT, ARROW, ARROW_CASING, CASING_WIDTH, DIAGRAM,
                    FACE_COLOURS, GRID_LINE, HIDDEN, ORIENTED, READY, TEXT,
                    TEXT_DIM, TILE, TILE_FOCUS, UNORIENTED, font)

#: Height a thumbnail keeps below the picture for the case's name.
LABEL_STRIP = 18

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
    card = inner.inflate(2 * tab + cell * 0.1, 2 * tab + cell * 0.1)
    pygame.draw.rect(surface, DIAGRAM, card, border_radius=max(2, round(cell * 0.12)))

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
        _draw_permutation_arrows(surface, cube, rect)


def _centre_of(grid_position, inner, cell):
    row, column = grid_position
    return (inner.left + (column + 0.5) * cell, inner.top + (row + 0.5) * cell)


def arrow_paths(cube, rect):
    """The arrows a case calls for, as (from, to, points-both-ways) triples.

    Read with the AUF divided out, so the picture shows the case rather than
    how far round the layer happens to be turned: a cuber met by a T perm at an
    angle has to see a T perm, and an arrow off every piece is true and
    useless.

    Two pieces that trade places get one arrow with a head at each end, not two
    arrows lying on top of each other. Drawn as two, each one's head sits under
    the other one's shaft, and a swap -- which is most of PLL -- comes out
    looking like a smudge with a point on it.
    """
    inner, cell, _ = _frame(rect)
    if not is_last_layer_oriented(cube):
        return []  # an orientation case is not about where anything travels
    try:
        corners, edges = u_layer_cycles(cube)
    except ValueError:
        return []  # not a last-layer case; nothing meaningful to point at
    paths = []
    for permutation, grid in ((corners, CORNER_GRID), (edges, EDGE_GRID)):
        drawn = set()
        for slot, destination in enumerate(permutation):
            if slot == destination or slot in drawn:
                continue
            trade = permutation[destination] == slot
            drawn.add(slot)
            if trade:
                drawn.add(destination)
            paths.append((_centre_of(grid[slot], inner, cell),
                          _centre_of(grid[destination], inner, cell), trade))
    return paths


def arrow_shaft_width(cell):
    """How thick an arrow's shaft is drawn, for a face of `cell`-wide stickers.

    Deliberately thin. A case like the H perm sends arrows across one small
    square at once, and a heavy line turns that into a scribble nobody can
    trace a single piece through. The head carries the meaning; the shaft only
    has to be followable.
    """
    return max(1, round(cell * 0.06))


def _arrow_outline(start, end, both_ways, cell):
    """One arrow as a single closed shape: shaft and head drawn as one.

    A line with a triangle laid over its end is two shapes pretending to be
    one, and every seam between them shows -- a notch where the head meets the
    shaft, and a shaft that has to stop short and leave a gap when it does not.
    Traced as one outline there is nothing to line up, and the whole arrow can
    be filled, and grown into its casing, in one piece.
    """
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return None
    ux, uy = dx / length, dy / length
    inset = cell * 0.22
    span = length - 2 * inset
    if span <= 0:
        return None
    # A hop to the next sticker leaves little room, and a swap wants room for
    # two heads. The heads give way rather than overrunning each other, so that
    # even the shortest arrow keeps a shaft long enough to say which two
    # stickers it joins.
    heads = 2 if both_ways else 1
    barb = min(cell * 0.3, span / (heads + 1))
    spread = barb * 0.44
    half = arrow_shaft_width(cell) / 2
    tip = (end[0] - ux * inset, end[1] - uy * inset)
    tail = (start[0] + ux * inset, start[1] + uy * inset)

    def offset(point, along, across):
        return (point[0] + ux * along - uy * across,
                point[1] + uy * along + ux * across)

    neck = offset(tip, -barb, 0)
    points = [tip, offset(neck, 0, spread), offset(neck, 0, half)]
    if both_ways:
        back = offset(tail, barb, 0)
        points += [offset(back, 0, half), offset(back, 0, spread), tail,
                   offset(back, 0, -spread), offset(back, 0, -half)]
    else:
        points += [offset(tail, 0, half), offset(tail, 0, -half)]
    return points + [offset(neck, 0, -half), offset(neck, 0, -spread)]


#: Directions the ink is stamped in to grow an arrow into its casing. A ring
#: rather than an outward push from the middle: an arrow is long and thin, and
#: pushing its corners away from its centre stretches it lengthwise instead of
#: thickening it evenly.
_RING = tuple((math.cos(math.tau * i / 12), math.sin(math.tau * i / 12))
              for i in range(12))

#: How many times over the arrows are drawn before being scaled back down.
#: pygame draws hard-edged shapes, and a hard-edged diagonal a pixel or two
#: wide is a staircase. Drawing it large and shrinking it is what turns those
#: steps into the smooth edge the rest of the diagram already has.
OVERSAMPLE = 4


def _draw_permutation_arrows(surface, cube, rect):
    """Every arrow the case calls for, drawn together rather than one by one.

    Together, because the order matters: one arrow's casing laid over another
    arrow's ink rubs it out, and with several arrows crossing -- an H perm, a G
    perm -- there is always a pair where that happens. So every casing goes
    down first and every arrow on top of the lot of them.
    """
    inner, cell, _ = _frame(rect)
    outlines = [outline for start, end, both_ways in arrow_paths(cube, rect)
                if (outline := _arrow_outline(start, end, both_ways, cell))]
    if not outlines:
        return
    scale = OVERSAMPLE if inner.width <= 320 else 2
    layer = pygame.Surface((inner.width * scale, inner.height * scale),
                           pygame.SRCALPHA)
    # Transparent, but transparent *in the casing's colour*: scaling down
    # averages the colour of every pixel it merges, including the ones nothing
    # was drawn on, and averaging towards an unset black leaves a dirty rim
    # around everything.
    layer.fill(ARROW_CASING + (0,))

    def placed(outline, shift=(0, 0)):
        return [((x - inner.left) * scale + shift[0],
                 (y - inner.top) * scale + shift[1]) for x, y in outline]

    grown = max(1.0, cell * CASING_WIDTH) * scale
    for outline in outlines:
        for dx, dy in _RING:
            pygame.draw.polygon(layer, ARROW_CASING,
                                placed(outline, (dx * grown, dy * grown)))
    for outline in outlines:
        pygame.draw.polygon(layer, ARROW, placed(outline))
    surface.blit(pygame.transform.smoothscale(layer, inner.size), inner.topleft)


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
    picture = pygame.Rect(0, 0, rect.width - 4, rect.height - LABEL_STRIP)
    picture.midtop = (rect.centerx, rect.top + 2)
    draw_case(surface, cube, picture, arrows=True)
    size = 15 if rect.width >= 80 else 13
    rendered = font(size, bold=cursor).render(label, True, TEXT_DIM if dim else TEXT)
    surface.blit(rendered, rendered.get_rect(midbottom=(rect.centerx, rect.bottom - 2)))
