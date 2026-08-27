"""Drawing a case.

A picture that disagrees with the scramble beside it is worse than no picture,
so everything drawn here is read out of the cube state the trainer built. These
tests read the pixels back and check what a cuber would actually be looking at.
"""

import math

import pygame
import pytest

from cubetrainer.cases import f2l, oll, pll
from cubetrainer.cube import Cube
from cubetrainer.ui import render, theme
from cubetrainer.ui.theme import (ARROW, ARROW_CASING, ASIDE, DIAGRAM,
                                  FACE_COLOURS, HIDDEN, ORIENTED, UNORIENTED)

RECT = pygame.Rect(0, 0, 240, 240)
TWO_TONES = {ORIENTED, UNORIENTED}
#: What a diagram paints that is not a sticker: the card it is drawn on, its
#: grid lines, and the colour the test filled the surface with beforehand.
FURNITURE = {DIAGRAM, (1, 2, 3), (30, 33, 39)}


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    # A Font outlives the pygame session that made it and draws nothing at all
    # afterwards, so the cache goes when the session does.
    theme.reset_fonts()
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


def _picture(cube, **kwargs):
    """The diagram as bytes, for asking whether two of them differ at all."""
    surface = pygame.Surface((260, 260))
    surface.fill((1, 2, 3))
    render.draw_case(surface, cube, RECT, **kwargs)
    return pygame.image.tostring(surface, "RGB")


def test_no_permutation_arrows_are_drawn_for_an_orientation_case():
    """An arrow says where a piece has to travel. That is a true sentence about
    a permutation case and a wrong answer about an orientation one."""
    for case in oll.OLL_CASES:
        state = _state(case)
        assert render.arrow_paths(state, RECT) == [], case.id
        assert _picture(state, arrows=True) == _picture(state, arrows=False), \
            f"{case.id} was drawn something an orientation case has no use for"


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
    state = _state(pll.get("T"))
    assert render.arrow_paths(state, RECT), \
        "the T perm moves pieces, so something has to point at them"
    assert _picture(state, arrows=True) != _picture(state, arrows=False)


def test_hidden_blanks_a_permutation_case():
    assert _drawn(_state(pll.get("T")), hidden=True) <= (
        FURNITURE | {HIDDEN, render.GRID_LINE})


# --- arrows stay readable when several cross --------------------------------

def _changed_by_arrows(cube, rect):
    """Pixels inside the upper face that the arrows alter, and the face itself.

    Counted as a difference rather than by looking for the arrow's own colours,
    because a smoothed edge is a blend of the arrow and what it lies on and is
    no particular colour at all.
    """
    def painted(arrows):
        surface = pygame.Surface((rect.width + 40, rect.height + 40))
        surface.fill((1, 2, 3))
        render.draw_case(surface, cube, rect, arrows=arrows)
        return surface

    bare, marked = painted(False), painted(True)
    cells = render.face_grid(rect)
    face = cells[0].union(cells[-1])
    ink = sum(1 for x in range(face.left, face.right)
              for y in range(face.top, face.bottom)
              if bare.get_at((x, y)) != marked.get_at((x, y)))
    return ink, face


def _heads(cube):
    """How many arrowheads the diagram draws: a trade shows one at each end."""
    return sum(2 if both_ways else 1
               for _, _, both_ways in render.arrow_paths(cube, RECT))


def _nearer(colour, target, than):
    return math.dist(colour[:3], target) < math.dist(colour[:3], than)


def test_the_shaft_is_thin_at_the_size_a_thumbnail_draws_it():
    """A picker tile gives each sticker a few dozen pixels. Anything but a fine
    line there is a scribble."""
    assert render.arrow_shaft_width(20) == 1
    for cell in range(8, 120):
        # A sixteenth of a sticker, give or take the whole pixel it rounds
        # to, against a head about four times that across.
        assert render.arrow_shaft_width(cell) <= max(1, cell * 0.065 + 0.5)
        assert render.arrow_shaft_width(cell) >= 1


def test_arrows_leave_the_face_readable_when_they_cross_the_middle():
    """The H perm sends every edge across the middle at once. If the arrows are
    heavy the face turns into one dark smear, which is what a cuber means by
    jumbled -- so the ink they add is budgeted."""
    thumbnail = pygame.Rect(0, 0, 74, 74)
    ink, face = _changed_by_arrows(_state(pll.get("H")), thumbnail)
    assert ink > 0, "no arrows were drawn at all"
    assert ink < 0.2 * face.width * face.height, \
        f"arrows cover {ink / (face.width * face.height):.0%} of the face"


def test_an_arrow_carries_its_own_contrast():
    """A line the same colour as the lines between stickers disappears into
    them, which is what made these hard to follow. The casing is what keeps an
    arrow legible wherever it crosses."""
    assert ARROW != render.GRID_LINE
    surface = pygame.Surface((260, 260))
    surface.fill((1, 2, 3))
    render.draw_case(surface, _state(pll.get("T")), RECT)
    painted = [surface.get_at((x, y))[:3]
               for x in range(RECT.width) for y in range(RECT.height)]
    assert any(math.dist(c, ARROW) < 12 for c in painted), \
        "the arrows themselves were not drawn"
    assert any(math.dist(c, ARROW_CASING) < 12 for c in painted), \
        "the arrows have nothing to stand out against"


def test_the_edges_of_an_arrow_are_smoothed():
    """A hard-edged diagonal a couple of pixels wide is a staircase, and it is
    the one thing in the diagram that is not straight lines and flat colour. An
    arrow has to arrive at the sticker colour through something, or those steps
    are what a cuber sees."""
    surface = pygame.Surface((260, 260))
    render.draw_case(surface, _state(pll.get("Y")), RECT)
    yellow = FACE_COLOURS["U"]
    span = math.dist(ARROW, yellow)
    blends = {surface.get_at((x, y))[:3]
              for x in range(RECT.width) for y in range(RECT.height)}
    between = [c for c in blends
               if math.dist(c, ARROW) > 20 and math.dist(c, yellow) > 20
               and math.dist(c, ARROW) + math.dist(c, yellow) < 1.15 * span]
    assert len(between) > 8, \
        "the arrow meets the sticker in one step, so its edges are stepped"


# --- one arrow per pair of pieces, not two lying on each other --------------

def test_two_pieces_that_trade_places_share_a_single_arrow():
    """Drawn as two arrows, each one's head is buried under the other one's
    shaft and its casing, and the pair reads as a line with a smudge on it. A
    trade is one arrow with a head at each end."""
    paths = render.arrow_paths(_state(pll.get("T")), RECT)
    assert len(paths) == 2, "the T perm trades two pairs, so it draws two arrows"
    assert all(both_ways for _, _, both_ways in paths)
    assert _heads(_state(pll.get("T"))) == 4


def test_no_two_arrows_are_drawn_along_the_same_line():
    """Whatever the case, nothing is drawn twice in the same place: that is what
    puts one arrow's casing over another arrow's ink."""
    for case in pll.PLL_CASES:
        for auf in ("", "U", "U2", "U'"):
            state = _state(case)
            paths = render.arrow_paths(state.apply(auf) if auf else state, RECT)
            lines = [frozenset((tuple(map(round, a)), tuple(map(round, b))))
                     for a, b, _ in paths]
            assert len(set(lines)) == len(lines), f"{case.id} at {auf!r}"


def test_a_trade_is_unbroken_ink_from_one_head_to_the_other():
    """The bug this replaces, stated as a picture: walk the line between two
    pieces that swap and you must not meet the casing, because the only way the
    casing gets in there is one arrow being drawn over another."""
    state = _state(pll.get("T"))
    surface = pygame.Surface((260, 260))
    render.draw_case(surface, state, RECT)
    for start, end, both_ways in render.arrow_paths(state, RECT):
        assert both_ways
        # Inside the arrow: it starts a fifth of a sticker short of the
        # centre it points from, and stops the same short of the one it
        # points at.
        for step in range(15, 86):
            along = step / 100
            point = (round(start[0] + (end[0] - start[0]) * along),
                     round(start[1] + (end[1] - start[1]) * along))
            assert _nearer(surface.get_at(point), ARROW, ARROW_CASING), \
                f"the casing shows at {along:.0%} along a trade"


# --- heads point where the piece is going -----------------------------------

def test_every_arrow_ends_in_a_head_at_the_end_it_points_at():
    """The line says two pieces are involved; only the head says which way."""
    for case_id in ("Ua", "T", "Ga", "V"):
        for start, end, both_ways in render.arrow_paths(_state(pll.get(case_id)), RECT):
            outline = render._arrow_outline(start, end, both_ways, 80)
            tip = outline[0]
            assert math.dist(tip, end) < math.dist(tip, start), \
                f"{case_id}: the head is nearer where the piece came from"
            if both_ways:
                assert any(math.dist(p, start) < math.dist(p, end)
                           for p in outline), f"{case_id}: a trade has one head"


def test_a_case_met_at_an_angle_is_drawn_with_the_arrows_of_its_case():
    """A drill hands out the case at one of its four angles, so the cuber has an
    upper-face adjustment to make before the algorithm applies. Drawn as "where
    does each piece belong", that adjustment puts an arrow on nearly every
    piece and a T perm stops looking like a T perm -- which leaves the picture
    unusable for the one thing it is there for."""
    for case in pll.PLL_CASES:
        square = _heads(_state(case))
        for auf in ("U", "U2", "U'"):
            angled = _state(case).apply(auf)
            assert _heads(angled) == square, \
                f"{case.id} after {auf} points at {_heads(angled)}, not {square}"


def test_the_t_perm_swaps_two_pairs_from_every_angle():
    """The case a cuber is likeliest to meet, spelled out: two corners and two
    edges, two arrows, four heads, whichever way round the layer is turned."""
    for auf in ("", "U", "U2", "U'"):
        state = _state(pll.get("T"))
        state = state.apply(auf) if auf else state
        paths = render.arrow_paths(state, RECT)
        assert len(paths) == 2, f"after {auf!r}: {len(paths)} arrows"
        assert all(both_ways for _, _, both_ways in paths), f"after {auf!r}"


def test_every_case_draws_as_a_thumbnail_at_every_angle():
    """The picker draws all 21 at once, and a drill any of them at any angle."""
    surface = pygame.Surface((1180, 780))
    for index, case in enumerate(pll.PLL_CASES):
        for auf in ("", "U", "U2", "U'"):
            state = _state(case)
            rect = pygame.Rect((index % 8) * 140, (index // 8) * 140, 132, 132)
            render.draw_thumbnail(surface, state.apply(auf) if auf else state,
                                  rect, case.id)


# --- an F2L case is a different picture, chosen from the state --------------

def _f2l(case_id="F2L 3", auf=""):
    state = Cube.solved().apply(f2l.get(case_id).setup)
    return state.apply(auf) if auf else state


def test_an_f2l_case_is_drawn_as_a_cube_seen_from_a_corner():
    """Half of an F2L case is in the slot, underneath the layer the last-layer
    diagram draws, so it gets the picture that can show a slot: the upper, front
    and right faces at once.

    Told apart from the other picture by the card: the view from above sits on
    one, and a cube seen from a corner is a cube rather than a diagram."""
    drawn = _drawn(_f2l())
    assert DIAGRAM not in drawn, "an F2L case was drawn as a flat diagram"
    assert ASIDE in drawn, "nothing was set aside, so the last layer is in colour"
    assert len(drawn & set(FACE_COLOURS.values())) >= 3


def test_the_last_layer_phases_are_still_drawn_from_above():
    """Adding a third picture must not have moved the other two."""
    for state in (_state(pll.get("T")), _state(oll.get("OLL 27"))):
        assert DIAGRAM in _drawn(state)
        assert ASIDE not in _drawn(state)


def test_a_screen_never_says_which_picture_it_wants():
    """Three phases, one call. Adding a phase stays data rather than a change to
    every screen, which is only true while the state decides."""
    surface = pygame.Surface((260, 260))
    pictures = set()
    for state in (_f2l(), _state(oll.get("OLL 27")), _state(pll.get("T"))):
        surface.fill((1, 2, 3))
        render.draw_case(surface, state, RECT)
        pictures.add(pygame.image.tostring(surface, "RGB"))
    assert len(pictures) == 3


def test_the_last_layer_is_set_aside_but_the_pair_is_not():
    """An F2L case says nothing about the last layer -- it can be anything up
    there, and usually is -- so drawing it in colour would invite reading
    something that is not the question. The pair keeps its colours wherever it
    is, which is the only thing up there worth looking at."""
    up = _drawn(_f2l("F2L 3"))       # pair in the upper face
    assert ASIDE in up
    assert len(up & set(FACE_COLOURS.values())) >= 3, "the pair lost its colours"

    down = _drawn(_f2l("F2L 41"))    # pair already in the slot
    assert ASIDE in down
    assert FACE_COLOURS["F"] in down and FACE_COLOURS["R"] in down


def test_no_two_f2l_cases_are_drawn_alike_from_any_angle():
    """A drill hands the case out at one of its four angles, so two cases that
    share a picture at any of them is a case a cuber cannot be asked to
    recognise."""
    seen = {}
    for case in f2l.F2L_CASES:
        for auf in ("", "U", "U2", "U'"):
            surface = pygame.Surface((160, 160))
            surface.fill((1, 2, 3))
            render.draw_case(surface, _f2l(case.id, auf), pygame.Rect(0, 0, 160, 160))
            seen.setdefault(pygame.image.tostring(surface, "RGB"), set()).add(case.id)
    shared = [sorted(ids) for ids in seen.values() if len(ids) > 1]
    assert shared == [], f"drawn identically: {shared[:3]}"


def test_no_arrows_are_drawn_for_an_f2l_case():
    """An arrow says where a piece travels. An F2L case is about where two
    pieces are, and the answer to that is the picture."""
    for case in f2l.F2L_CASES:
        assert render.arrow_paths(_f2l(case.id), RECT) == [], case.id


def test_hidden_blanks_an_f2l_case():
    """The drill covers the case until the cuber asks for it, whichever picture
    it would have got."""
    assert _drawn(_f2l(), hidden=True) <= {HIDDEN, render.GRID_LINE, (1, 2, 3)}


def test_every_f2l_case_draws_as_a_thumbnail():
    surface = pygame.Surface((1180, 780))
    for index, case in enumerate(f2l.F2L_CASES):
        rect = pygame.Rect((index % 8) * 140, (index // 8) * 140, 132, 132)
        render.draw_thumbnail(surface, _f2l(case.id), rect, case.id)


def test_an_f2l_case_fits_the_rectangle_it_is_given():
    """The picker gives every phase the same tile, so a cube drawn from a corner
    has to sit inside one rather than spill over its neighbours."""
    rect = pygame.Rect(40, 40, 120, 120)
    surface = pygame.Surface((200, 200))
    surface.fill((1, 2, 3))
    render.draw_case(surface, _f2l(), rect)
    for x in range(200):
        for y in range(200):
            if not rect.collidepoint(x, y):
                assert surface.get_at((x, y))[:3] == (1, 2, 3), f"spilled at {x},{y}"
