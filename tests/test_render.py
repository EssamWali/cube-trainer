"""Drawing a case.

A picture that disagrees with the scramble beside it is worse than no picture,
so everything drawn here is read out of the cube state the trainer built. These
tests read the pixels back and check what a cuber would actually be looking at.
"""

import math

import pygame
import pytest

from cubetrainer.cases import oll, pll
from cubetrainer.cube import Cube
from cubetrainer.ui import render
from cubetrainer.ui.theme import (ARROW, ARROW_CASING, DIAGRAM, FACE_COLOURS,
                                  HIDDEN, ORIENTED, UNORIENTED)

RECT = pygame.Rect(0, 0, 240, 240)
TWO_TONES = {ORIENTED, UNORIENTED}
#: What a diagram paints that is not a sticker: the card it is drawn on, its
#: grid lines, and the colour the test filled the surface with beforehand.
FURNITURE = {DIAGRAM, (1, 2, 3), (30, 33, 39)}


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def _state(case):
    return Cube.solved().apply(case.setup)


def _drawn(cube, **kwargs):
    """Every colour the diagram puts on screen, sampled from the picture."""
    surface = pygame.Surface((260, 260))
    surface.fill((1, 2, 3))
    render.draw_case(surface, cube, RECT, **kwargs)
    return {surface.get_at((x, y))[:3]
            for x in range(RECT.width) for y in range(RECT.height)}


def _top_face(cube, **kwargs):
    """The nine upper-face cells, sampled at their centres.

    The diagram is asked where it drew them rather than told, so changing the
    proportions cannot leave this quietly reading the wrong pixels.
    """
    surface = pygame.Surface((260, 260))
    render.draw_case(surface, cube, RECT, **kwargs)
    return [surface.get_at(cell.center)[:3] for cell in render.face_grid(RECT)]


# --- orientation cases ------------------------------------------------------

def test_an_orientation_case_is_drawn_in_two_tones():
    """An OLL diagram answers one question -- is this sticker facing up -- so
    it is drawn in the two colours that question has answers."""
    drawn = _drawn(_state(oll.get("OLL 27")))
    assert drawn <= TWO_TONES | FURNITURE | {render.GRID_LINE}
    assert TWO_TONES <= drawn


def test_a_sticker_showing_the_upper_face_colour_is_the_oriented_tone():
    sune = _top_face(_state(oll.get("OLL 27")))
    solved = _top_face(Cube.solved().apply("R U R' U R U2 R' U2"))
    assert sune[4] == ORIENTED, "the centre always shows the upper-face colour"
    assert UNORIENTED in sune, "sune has corners still to orient"
    assert set(solved) == {ORIENTED} or UNORIENTED in solved


def test_the_cross_group_shows_every_edge_oriented():
    """The plus sign a cuber looks for, drawn as such."""
    cells = _top_face(_state(oll.get("OLL 27")))
    for edge in (1, 3, 5, 7):
        assert cells[edge] == ORIENTED
    assert cells[4] == ORIENTED


def test_the_cases_with_no_edge_oriented_show_only_the_centre():
    for case in oll.by_group()[oll.NO_EDGES]:
        cells = _top_face(_state(case))
        for edge in (1, 3, 5, 7):
            assert cells[edge] == UNORIENTED, case.id


def test_side_stickers_tell_two_cases_with_the_same_top_apart():
    """Seen from directly above, several OLL cases are the same picture. The
    ring of side stickers is the only thing that separates them, so it has to
    be drawn and it has to be read from the state."""
    def picture(case):
        surface = pygame.Surface((260, 260))
        render.draw_case(surface, _state(case), RECT)
        return pygame.image.tostring(surface, "RGB")

    by_top = {}
    for case in oll.OLL_CASES:
        by_top.setdefault(tuple(_top_face(_state(case))), []).append(case)
    shared = [cases for cases in by_top.values() if len(cases) > 1]
    assert shared, "no two cases share a top face, so nothing is being tested"
    for cases in shared:
        pictures = {picture(case) for case in cases}
        assert len(pictures) == len(cases),             f"{[c.id for c in cases]} are drawn identically"


def test_no_permutation_arrows_are_drawn_for_an_orientation_case():
    """An arrow says where a piece has to travel. That is a true sentence about
    a permutation case and a wrong answer about an orientation one."""
    drawn = []
    original = render._draw_arrow
    render._draw_arrow = lambda *a, **k: drawn.append(a)
    try:
        for case in oll.OLL_CASES:
            render.draw_case(pygame.Surface((260, 260)), _state(case), RECT)
        assert drawn == []
    finally:
        render._draw_arrow = original


def test_hidden_blanks_an_orientation_case():
    assert _drawn(_state(oll.get("OLL 27")), hidden=True) <= (
        FURNITURE | {HIDDEN, render.GRID_LINE})


def test_every_orientation_case_draws_as_a_thumbnail():
    surface = pygame.Surface((1180, 780))
    for index, case in enumerate(oll.OLL_CASES):
        rect = pygame.Rect((index % 8) * 140, (index // 8) * 140, 132, 132)
        render.draw_thumbnail(surface, _state(case), rect, case.id)


# --- permutation cases are unchanged ----------------------------------------

def test_a_permutation_case_keeps_its_true_colours():
    drawn = _drawn(_state(pll.get("T")))
    assert FACE_COLOURS["F"] in drawn
    assert FACE_COLOURS["R"] in drawn
    assert len(drawn & set(FACE_COLOURS.values())) >= 4


def test_a_permutation_case_still_draws_its_arrows():
    drawn = []
    original = render._draw_arrow
    render._draw_arrow = lambda *a, **k: drawn.append(a)
    try:
        render.draw_case(pygame.Surface((260, 260)), _state(pll.get("T")), RECT)
        assert drawn, "the T perm moves pieces, so something has to point at them"
    finally:
        render._draw_arrow = original


def test_hidden_blanks_a_permutation_case():
    assert _drawn(_state(pll.get("T")), hidden=True) <= (
        FURNITURE | {HIDDEN, render.GRID_LINE})


# --- arrows stay readable when several cross --------------------------------

def _arrow_ink(cube, rect, arrows):
    """Pixels the arrows paint inside the upper face, and the face itself."""
    surface = pygame.Surface((rect.width + 40, rect.height + 40))
    surface.fill((1, 2, 3))
    render.draw_case(surface, cube, rect, arrows=arrows)
    cells = render.face_grid(rect)
    face = cells[0].union(cells[-1])
    ink = sum(1 for x in range(face.left, face.right)
              for y in range(face.top, face.bottom)
              if surface.get_at((x, y))[:3] in (ARROW, ARROW_CASING))
    return ink, face


def _arrows_drawn(case):
    """Every arrow drawn for `case`, as (start, end, head-polygon)."""
    arrows, heads = [], []
    draw_arrow, polygon = render._draw_arrow, pygame.draw.polygon

    def spy_arrow(surface, start, end, cell):
        arrows.append((start, end, len(heads)))
        return draw_arrow(surface, start, end, cell)

    def spy_polygon(surface, colour, points, *a, **k):
        if colour == ARROW:
            heads.append(points)
        return polygon(surface, colour, points, *a, **k)

    render._draw_arrow, pygame.draw.polygon = spy_arrow, spy_polygon
    try:
        render.draw_case(pygame.Surface((260, 260)), _state(case), RECT)
    finally:
        render._draw_arrow, pygame.draw.polygon = draw_arrow, polygon
    return [(start, end, heads[index]) for start, end, index in arrows]


def test_the_shaft_is_thin_at_the_size_a_thumbnail_draws_it():
    """A picker tile gives each sticker a few dozen pixels. Anything but a fine
    line there is a scribble."""
    assert render.arrow_shaft_width(20) == 1
    for cell in range(8, 120):
        # A twentieth of a sticker, give or take the whole pixel it rounds to.
        assert render.arrow_shaft_width(cell) <= max(1, cell * 0.05 + 0.5)
        assert render.arrow_shaft_width(cell) >= 1


def test_arrows_leave_the_face_readable_when_four_of_them_cross():
    """The H perm sends every edge across the middle at once. If the arrows are
    heavy the face turns into one dark smear, which is what a cuber means by
    jumbled -- so the ink they add is budgeted."""
    thumbnail = pygame.Rect(0, 0, 74, 74)
    state = _state(pll.get("H"))
    without, face = _arrow_ink(state, thumbnail, arrows=False)
    with_arrows, _ = _arrow_ink(state, thumbnail, arrows=True)
    assert without == 0, "the arrow colours belong to the arrows alone"
    assert with_arrows > 0, "no arrows were drawn at all"
    assert with_arrows < 0.2 * face.width * face.height,         f"arrows cover {with_arrows / (face.width * face.height):.0%} of the face"


def test_an_arrow_carries_its_own_contrast():
    """A line the same colour as the lines between stickers disappears into
    them, which is what made these hard to follow. The casing is what keeps an
    arrow legible wherever it crosses."""
    assert ARROW != render.GRID_LINE
    surface = pygame.Surface((260, 260))
    surface.fill((1, 2, 3))
    render.draw_case(surface, _state(pll.get("T")), RECT)
    painted = {surface.get_at((x, y))[:3]
               for x in range(RECT.width) for y in range(RECT.height)}
    assert ARROW in painted, "the arrows themselves were not drawn"
    assert ARROW_CASING in painted, "the arrows have nothing to stand out against"


def test_every_arrow_ends_in_an_arrow_head():
    """The line says two pieces are involved; only the head says which way."""
    drawn = _arrows_drawn(pll.get("T"))
    assert drawn, "the T perm moves pieces, so something has to point at them"
    assert all(len(head) == 3 for _, _, head in drawn)


def test_the_head_sits_at_the_end_the_piece_is_going_to():
    """A head on the wrong end is a wrong answer, not a blemish."""
    for case_id in ("Ua", "T", "Ga"):
        for start, end, head in _arrows_drawn(pll.get(case_id)):
            tip = head[0]
            assert math.dist(tip, end) < math.dist(tip, start),                 f"{case_id}: the head is nearer where the piece came from"
