"""Drawing a last-layer case.

The picture is drawn from the cube state the trainer built, never from a stored
image. A case picture and the scramble that produces it therefore cannot
disagree: there is only one source for both.

The layout is the one every last-layer diagram uses -- the upper face seen from
above, ringed by the side stickers of the pieces in it, with arrows showing
where each piece has to go.
"""

import math

import pygame

from ..cases.pattern import u_layer_permutation
from .theme import FACE_COLOURS, GRID_LINE, HIDDEN, TEXT_DIM, font

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


def draw_case(surface, cube, rect, arrows=True, hidden=False):
    """Draw the last layer of `cube` inside `rect`.

    With `hidden`, the shape is drawn blank. A drill that shows you the case has
    already answered the harder half of the question, so recognition is only
    trained when the picture stays covered until you ask for it.
    """
    size = min(rect.width, rect.height)
    tab = size * 0.11
    inner = pygame.Rect(0, 0, size - 2 * tab, size - 2 * tab)
    inner.center = rect.center
    cell = inner.width / 3

    def cell_rect(row, column):
        return pygame.Rect(
            round(inner.left + column * cell), round(inner.top + row * cell),
            math.ceil(cell), math.ceil(cell),
        )

    for row in range(3):
        for column in range(3):
            colour = HIDDEN if hidden else FACE_COLOURS[cube.facelets[row * 3 + column]]
            pygame.draw.rect(surface, colour, cell_rect(row, column))
            pygame.draw.rect(surface, GRID_LINE, cell_rect(row, column), 2)

    for index, row, column, side in SIDE_TABS:
        base = cell_rect(row, column)
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
        colour = HIDDEN if hidden else FACE_COLOURS[cube.facelets[index]]
        pygame.draw.rect(surface, colour, area)
        pygame.draw.rect(surface, GRID_LINE, area, 1)

    if arrows and not hidden:
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


def _draw_arrow(surface, start, end, cell):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    inset = cell * 0.26
    tail = (start[0] + ux * inset, start[1] + uy * inset)
    head = (end[0] - ux * inset, end[1] - uy * inset)
    width = max(3, round(cell * 0.07))
    pygame.draw.line(surface, GRID_LINE, tail, head, width + 2)
    barb = cell * 0.2
    left = (head[0] - ux * barb - uy * barb * 0.55, head[1] - uy * barb + ux * barb * 0.55)
    right = (head[0] - ux * barb + uy * barb * 0.55, head[1] - uy * barb - ux * barb * 0.55)
    pygame.draw.polygon(surface, GRID_LINE, [head, left, right])


def draw_thumbnail(surface, cube, rect, label, selected=False, dim=False):
    """A small case picture with its name, for the picker and the library."""
    background = (44, 52, 66) if selected else (30, 33, 39)
    pygame.draw.rect(surface, background, rect, border_radius=6)
    if selected:
        pygame.draw.rect(surface, (94, 168, 255), rect, 2, border_radius=6)
    picture = pygame.Rect(0, 0, rect.width - 16, rect.height - 30)
    picture.midtop = (rect.centerx, rect.top + 6)
    draw_case(surface, cube, picture, arrows=True)
    rendered = font(15, bold=selected).render(label, True, TEXT_DIM if dim else (236, 238, 242))
    surface.blit(rendered, rendered.get_rect(midbottom=(rect.centerx, rect.bottom - 5)))
