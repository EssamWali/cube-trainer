"""The interface, driven headlessly.

These are the tests that would have caught the case-picture bug: they run the
real screens, with the real store, and check what actually gets recorded when
somebody presses the keys.
"""

import pygame
import pytest

from cubetrainer.cases import CATALOGUES, pll
from cubetrainer.cube import Cube
from cubetrainer.store import Store
from cubetrainer.trainer.timer import TimerState
from cubetrainer.ui import render
from cubetrainer.ui.app import App, DrillScreen, HomeScreen, PickerScreen, StatsScreen
from cubetrainer.ui.theme import ACCENT, READY


@pytest.fixture()
def app():
    store = Store.in_memory()
    application = App(store=store, seed=1234)
    yield application
    pygame.quit()


def key_down(screen, application, key, now=None, unicode=""):
    if now is not None:
        application.now = now
    return screen.handle(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode))


def key_up(screen, application, key, now=None):
    if now is not None:
        application.now = now
    return screen.handle(pygame.event.Event(pygame.KEYUP, key=key))


def do_a_rep(drill, application, start=0.0, finish=2.5):
    """Arm, start and stop the timer the way a cuber would."""
    key_down(drill, application, pygame.K_SPACE, now=start)
    drill.update(start + 0.7)
    key_up(drill, application, pygame.K_SPACE, now=start + 0.7)
    assert drill.timer.state is TimerState.RUNNING
    key_down(drill, application, pygame.K_SPACE, now=finish)


# --- navigation -------------------------------------------------------------

def test_the_home_screen_opens_the_picker(app):
    home = HomeScreen(app)
    result = key_down(home, app, pygame.K_1)
    assert isinstance(result, PickerScreen)
    assert result.mode == "select"


def test_the_home_screen_offers_a_drill_for_every_phase(app):
    home = HomeScreen(app)
    for index, catalogue in enumerate(app.catalogues):
        result = key_down(home, app, pygame.K_1 + index)
        assert isinstance(result, PickerScreen)
        assert result.mode == "select"
        assert result.catalogue is catalogue


def test_the_library_is_the_picker_in_browse_mode(app):
    """One library entry per phase, after the drills."""
    home = HomeScreen(app)
    first = pygame.K_1 + len(app.catalogues)
    for index, catalogue in enumerate(app.catalogues):
        result = key_down(home, app, first + index)
        assert isinstance(result, PickerScreen)
        assert result.mode == "browse"
        assert result.catalogue is catalogue


def test_every_screen_draws_without_error(app):
    surface = pygame.Surface((1180, 780))
    picker = PickerScreen(app, mode="select")
    drill = DrillScreen(app, ["T", "Ja"])
    for screen in (HomeScreen(app), picker, PickerScreen(app, mode="browse"),
                   drill, StatsScreen(app)):
        screen.draw(surface)


# --- picking ----------------------------------------------------------------

def test_space_toggles_a_case_and_g_toggles_its_whole_group(app):
    picker = PickerScreen(app, mode="select")
    first = picker.current.id
    key_down(picker, app, pygame.K_n)
    assert picker.selected == set()
    key_down(picker, app, pygame.K_SPACE)
    assert picker.selected == {first}
    key_down(picker, app, pygame.K_g)
    group = {c.id for c in pll.by_group()[picker.current.group]}
    assert group <= picker.selected


def test_starting_a_drill_needs_at_least_one_case(app):
    picker = PickerScreen(app, mode="select")
    key_down(picker, app, pygame.K_n)
    assert key_down(picker, app, pygame.K_RETURN) is None
    assert picker.message


def test_enter_starts_a_drill_with_the_selected_cases(app):
    picker = PickerScreen(app, mode="select")
    key_down(picker, app, pygame.K_n)
    key_down(picker, app, pygame.K_SPACE)
    drill = key_down(picker, app, pygame.K_RETURN)
    assert isinstance(drill, DrillScreen)
    assert drill.case_ids == [picker.current.id]


def test_the_last_selection_comes_back_next_time(app):
    """Re-picking eight cases every session is the friction that stops people
    drilling, so the selection has to survive."""
    picker = PickerScreen(app, mode="select")
    key_down(picker, app, pygame.K_n)
    key_down(picker, app, pygame.K_SPACE)
    chosen = set(picker.selected)
    key_down(picker, app, pygame.K_RETURN)
    assert PickerScreen(app, mode="select").selected == chosen


def test_a_named_case_set_round_trips(app):
    picker = PickerScreen(app, mode="select")
    key_down(picker, app, pygame.K_n)
    key_down(picker, app, pygame.K_SPACE)
    expected = set(picker.selected)
    key_down(picker, app, pygame.K_s)
    for letter in "bad":
        key_down(picker, app, pygame.K_a, unicode=letter)
    key_down(picker, app, pygame.K_RETURN)
    assert app.store.load_case_set("bad", "PLL") == sorted(expected)


def test_browse_mode_does_not_change_the_selection(app):
    picker = PickerScreen(app, mode="browse")
    before = set(picker.selected)
    key_down(picker, app, pygame.K_n)
    key_down(picker, app, pygame.K_SPACE)
    assert picker.selected == before


# --- drilling ---------------------------------------------------------------

def test_a_rep_is_recorded_with_its_case_scramble_and_time(app):
    drill = DrillScreen(app, ["T"])
    scramble = drill.scramble
    do_a_rep(drill, app, start=0.0, finish=2.5)
    assert drill.stage == "result"
    rep, = app.store.reps()
    assert rep["case_id"] == "T"
    assert rep["scramble"] == scramble
    assert rep["duration_ms"] == pytest.approx(1800, abs=1)


def test_the_scramble_actually_produces_the_case_being_drilled(app):
    """End to end: what the screen shows is what the cuber will be holding."""
    from cubetrainer.cases.pattern import case_key, is_pll_state
    drill = DrillScreen(app, [c.id for c in pll.PLL_CASES])
    for _ in range(25):
        state = Cube.solved().apply(drill.scramble)
        assert is_pll_state(state)
        assert case_key(state) == case_key(Cube.solved().apply(drill.case.setup))
        do_a_rep(drill, app)
        key_down(drill, app, pygame.K_SPACE)


def test_releasing_early_does_not_start_the_timer(app):
    drill = DrillScreen(app, ["T"])
    key_down(drill, app, pygame.K_SPACE, now=0.0)
    drill.update(0.2)
    key_up(drill, app, pygame.K_SPACE, now=0.2)
    assert drill.timer.state is TimerState.IDLE
    assert app.store.reps() == []


def test_peeking_is_recorded_and_keeps_the_rep_out_of_the_average(app):
    drill = DrillScreen(app, ["T"])
    key_down(drill, app, pygame.K_p)
    assert drill.peeked
    do_a_rep(drill, app)
    rep, = app.store.reps()
    assert rep["peeked"] == 1
    assert drill.times == []


def test_the_case_is_hidden_until_it_is_revealed(app):
    """The point of the drill: recognising the case is half the skill."""
    drill = DrillScreen(app, ["T"])
    drawn = []
    original = render.draw_case

    def spy(surface, cube, rect, arrows=True, hidden=False):
        drawn.append(hidden)
        return original(surface, cube, rect, arrows=arrows, hidden=hidden)

    render.draw_case = spy
    try:
        surface = pygame.Surface((1180, 780))
        drill.draw(surface)
        assert drawn[-1] is True
        key_down(drill, app, pygame.K_p)
        drill.draw(surface)
        assert drawn[-1] is False
    finally:
        render.draw_case = original


def test_a_fumble_is_recorded_as_a_dnf_and_asks_for_a_reset(app):
    """A misexecuted algorithm leaves the cube where the trainer cannot follow,
    so the next scramble is only valid once the cube is solved again."""
    drill = DrillScreen(app, ["T"])
    key_down(drill, app, pygame.K_d)
    assert drill.stage == "reset"
    rep, = app.store.reps()
    assert rep["penalty"] == "dnf"
    assert rep["duration_ms"] is None
    key_down(drill, app, pygame.K_SPACE)
    assert drill.stage == "scramble"


def test_a_plus_two_penalty_updates_the_recorded_time(app):
    drill = DrillScreen(app, ["T"])
    do_a_rep(drill, app, start=0.0, finish=2.5)
    key_down(drill, app, pygame.K_2)
    rep, = app.store.reps()
    assert rep["penalty"] == "plus_two"
    assert rep["duration_ms"] == pytest.approx(3800, abs=1)


def test_the_drill_deals_every_selected_case_before_repeating(app):
    drill = DrillScreen(app, ["T", "Ja", "H"])
    seen = []
    for _ in range(6):
        seen.append(drill.case.id)
        do_a_rep(drill, app)
        key_down(drill, app, pygame.K_SPACE)
    assert sorted(seen[:3]) == ["H", "Ja", "T"]
    assert sorted(seen[3:]) == ["H", "Ja", "T"]


def test_leaving_a_drill_closes_its_session(app):
    drill = DrillScreen(app, ["T"])
    do_a_rep(drill, app)
    assert key_down(drill, app, pygame.K_ESCAPE) == "back"
    session, = app.store.sessions()
    assert session["ended_at"] is not None
    assert session["kind"] == "drill"


# --- statistics -------------------------------------------------------------

def test_the_stats_screen_reports_the_cases_that_were_drilled(app):
    drill = DrillScreen(app, ["T"])
    for index in range(3):
        do_a_rep(drill, app, start=index * 10.0, finish=index * 10.0 + 3.0)
        key_down(drill, app, pygame.K_SPACE)
    stats = StatsScreen(app)
    assert [r.case_id for r in stats.reports] == ["T"]
    assert stats.reports[0].attempts == 3


def test_tab_changes_the_ranking_signal(app):
    stats = StatsScreen(app)
    first = stats.signal
    key_down(stats, app, pygame.K_TAB)
    assert stats.signal != first


def test_stats_survive_a_case_id_that_is_no_longer_known(app):
    """History outlives the case list; an unknown id must not crash the screen."""
    session = app.store.start_session("drill", "PLL")
    app.store.record_rep(session, "NotACase", "R U", 2.0)
    assert StatsScreen(app).reports == []


# --- every phase ------------------------------------------------------------
# The drill is the same drill whichever phase it is drilling, so these run over
# each catalogue the application ships rather than being written out twice.

@pytest.fixture(params=[c.phase for c in CATALOGUES])
def catalogue(request):
    return next(c for c in CATALOGUES if c.phase == request.param)


def first_ids(catalogue, count=1):
    return [c.id for c in catalogue.order[:count]]


def test_the_picker_shows_every_case_of_its_phase_grouped_by_shape(app, catalogue):
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    assert len(picker.order) == len(catalogue)
    assert [group for group, _, _ in picker.rows()] == list(catalogue.group_order)
    placed = [case.id for _, _, cases in picker.rows() for case, _ in cases]
    assert sorted(placed) == sorted(c.id for c in catalogue)


def test_every_case_is_drawn_on_the_screen(app, catalogue):
    """Fifty-seven cases at the tile size twenty-one used would run off the
    bottom of the window, and a case you cannot see is a case you cannot pick."""
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    window = pygame.Rect(0, 0, *app.surface.get_size())
    for _, _, cases in picker.rows():
        for case, rect in cases:
            assert window.contains(rect), f"{case.id} is off the screen"
            assert rect.bottom <= picker.detail_top, f"{case.id} covers the detail"


def test_a_named_case_set_belongs_to_one_phase_only(app):
    """Both phases have a set called "hard", and they are not the same cases."""
    for catalogue in app.catalogues:
        picker = PickerScreen(app, mode="select", catalogue=catalogue)
        key_down(picker, app, pygame.K_n)
        key_down(picker, app, pygame.K_SPACE)
        app.store.save_case_set("hard", catalogue.phase, sorted(picker.selected))
    saved = {c.phase: app.store.load_case_set("hard", c.phase) for c in app.catalogues}
    assert all(saved.values())
    assert len({tuple(v) for v in saved.values()}) == len(saved)


def test_the_last_selection_comes_back_for_each_phase(app, catalogue):
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    key_down(picker, app, pygame.K_n)
    key_down(picker, app, pygame.K_SPACE)
    chosen = set(picker.selected)
    key_down(picker, app, pygame.K_RETURN)
    assert PickerScreen(app, mode="select", catalogue=catalogue).selected == chosen


def test_starting_a_drill_needs_at_least_one_case_in_any_phase(app, catalogue):
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    key_down(picker, app, pygame.K_n)
    assert key_down(picker, app, pygame.K_RETURN) is None
    assert picker.message


def test_a_rep_is_recorded_against_a_session_tagged_with_its_phase(app, catalogue):
    case_id, = first_ids(catalogue)
    drill = DrillScreen(app, [case_id], catalogue)
    do_a_rep(drill, app, start=0.0, finish=2.5)
    rep, = app.store.reps()
    assert rep["case_id"] == case_id
    session, = app.store.sessions()
    assert session["phase"] == catalogue.phase
    assert session["kind"] == "drill"


def test_the_scramble_produces_the_case_being_drilled_in_any_phase(app, catalogue):
    """The trainer's central claim, for whichever phase is being drilled."""
    from cubetrainer.cases.pattern import (
        case_key,
        is_last_layer_oriented,
        is_oll_state,
        is_pll_state,
        orientation_key,
    )
    drill = DrillScreen(app, [c.id for c in catalogue], catalogue)
    for _ in range(25):
        state = Cube.solved().apply(drill.scramble)
        promised = Cube.solved().apply(drill.case.setup)
        if is_last_layer_oriented(promised):
            assert is_pll_state(state)
            assert case_key(state) == case_key(promised)
        else:
            assert is_oll_state(state)
            assert orientation_key(state) == orientation_key(promised)
        do_a_rep(drill, app)
        key_down(drill, app, pygame.K_SPACE)


def test_the_case_stays_hidden_until_it_is_revealed_in_any_phase(app, catalogue):
    drill = DrillScreen(app, first_ids(catalogue), catalogue)
    drawn = []
    original = render.draw_case

    def spy(surface, cube, rect, arrows=True, hidden=False):
        drawn.append(hidden)
        return original(surface, cube, rect, arrows=arrows, hidden=hidden)

    render.draw_case = spy
    try:
        surface = pygame.Surface((1180, 780))
        drill.draw(surface)
        assert drawn[-1] is True
        key_down(drill, app, pygame.K_p)
        drill.draw(surface)
        assert drawn[-1] is False
    finally:
        render.draw_case = original


def test_peeking_keeps_the_rep_out_of_the_average_in_any_phase(app, catalogue):
    drill = DrillScreen(app, first_ids(catalogue), catalogue)
    key_down(drill, app, pygame.K_p)
    do_a_rep(drill, app)
    rep, = app.store.reps()
    assert rep["peeked"] == 1
    assert drill.times == []


def test_a_fumble_and_a_penalty_behave_the_same_in_any_phase(app, catalogue):
    drill = DrillScreen(app, first_ids(catalogue), catalogue)
    key_down(drill, app, pygame.K_d)
    assert drill.stage == "reset"
    key_down(drill, app, pygame.K_SPACE)
    assert drill.stage == "scramble"
    do_a_rep(drill, app, start=10.0, finish=12.5)
    key_down(drill, app, pygame.K_2)
    dnf, timed = app.store.reps()
    assert dnf["penalty"] == "dnf" and dnf["duration_ms"] is None
    assert timed["penalty"] == "plus_two"
    assert timed["duration_ms"] == pytest.approx(3800, abs=1)


def test_leaving_a_drill_closes_its_session_in_any_phase(app, catalogue):
    drill = DrillScreen(app, first_ids(catalogue), catalogue)
    do_a_rep(drill, app)
    assert key_down(drill, app, pygame.K_ESCAPE) == "back"
    session, = app.store.sessions()
    assert session["ended_at"] is not None


def test_every_screen_of_every_phase_draws_without_error(app, catalogue):
    surface = pygame.Surface((1180, 780))
    screens = [
        HomeScreen(app),
        PickerScreen(app, mode="select", catalogue=catalogue),
        PickerScreen(app, mode="browse", catalogue=catalogue),
        DrillScreen(app, first_ids(catalogue, 2), catalogue),
        StatsScreen(app),
    ]
    for screen in screens:
        screen.draw(surface)


# --- statistics, one phase at a time ----------------------------------------

def show_phase(stats, app, catalogue):
    """Press the phase key until the phase we want is the one being ranked."""
    for _ in range(len(app.catalogues)):
        if stats.catalogue is catalogue:
            return stats
        key_down(stats, app, pygame.K_RIGHT)
    raise AssertionError(f"{catalogue.phase} never came up")


def drill_a_few(app, catalogue, case_id, count=3):
    drill = DrillScreen(app, [case_id], catalogue)
    for index in range(count):
        do_a_rep(drill, app, start=index * 10.0, finish=index * 10.0 + 3.0)
        key_down(drill, app, pygame.K_SPACE)
    key_down(drill, app, pygame.K_ESCAPE)


def test_drilled_cases_of_any_phase_reach_the_statistics(app, catalogue):
    case_id, = first_ids(catalogue)
    drill_a_few(app, catalogue, case_id)
    stats = show_phase(StatsScreen(app), app, catalogue)
    assert [r.case_id for r in stats.reports] == [case_id]
    assert stats.reports[0].attempts == 3
    assert stats.reports[0].seconds_per_move is not None
    assert stats.catalogue.get(case_id).name


def test_a_key_switches_which_phase_is_ranked(app):
    stats = StatsScreen(app)
    seen = [stats.catalogue.phase]
    for _ in range(len(app.catalogues) - 1):
        key_down(stats, app, pygame.K_RIGHT)
        seen.append(stats.catalogue.phase)
    assert seen == [c.phase for c in app.catalogues]
    key_down(stats, app, pygame.K_RIGHT)
    assert stats.catalogue.phase == seen[0], "the phases should cycle"
    key_down(stats, app, pygame.K_LEFT)
    assert stats.catalogue.phase == seen[-1]


def test_the_two_phases_are_never_mixed_into_one_ranking(app):
    """Ranking an OLL case against a PLL case compares two things that are not
    comparable, so each phase gets its own list."""
    for catalogue in app.catalogues:
        drill_a_few(app, catalogue, first_ids(catalogue)[0])
    stats = StatsScreen(app)
    for catalogue in app.catalogues:
        show_phase(stats, app, catalogue)
        drilled = {c.id for c in catalogue}
        assert [r.case_id for r in stats.reports] == first_ids(catalogue)
        assert all(r.case_id in drilled for r in stats.reports)


def test_tab_still_changes_the_ranking_signal_in_every_phase(app):
    stats = StatsScreen(app)
    for _ in app.catalogues:
        first = stats.signal
        key_down(stats, app, pygame.K_TAB)
        assert stats.signal != first
        key_down(stats, app, pygame.K_RIGHT)


def test_statistics_survive_a_case_id_that_is_no_longer_known(app, catalogue):
    """History outlives the case list, in every phase."""
    session = app.store.start_session("drill", catalogue.phase)
    app.store.record_rep(session, "NotACase", "R U", 2.0)
    stats = show_phase(StatsScreen(app), app, catalogue)
    assert stats.reports == []
    stats.draw(pygame.Surface((1180, 780)))


def test_solve_summaries_are_not_affected_by_the_phase_on_show(app):
    """Full solves have no case and belong to no phase of the picker, so
    switching which phase is ranked must leave that band of the screen alone."""
    session = app.store.start_session("solve")
    app.store.record_solve(session, "R U", 20.0, splits=(("Cross", 2.0), ("F2L", 8.0)))
    surface = pygame.Surface((1180, 780))
    band = pygame.Rect(0, 80, 1180, 64)

    def summary_band():
        surface.fill((0, 0, 0))
        stats.draw(surface)
        return pygame.image.tostring(surface.subsurface(band), "RGB")

    stats = StatsScreen(app)
    drawn = summary_band()
    assert len(set(drawn)) > 1, "the band is blank, so it is testing nothing"
    for _ in app.catalogues:
        key_down(stats, app, pygame.K_RIGHT)
        assert summary_band() == drawn


def test_the_statistics_can_be_given_the_phases_to_rank(app):
    """Handed one phase, it ranks that phase and offers no other."""
    pll, oll = app.catalogues
    drill_a_few(app, oll, first_ids(oll)[0])
    stats = StatsScreen(app, catalogues=[oll])
    assert stats.catalogue is oll
    assert [r.case_id for r in stats.reports] == first_ids(oll)
    key_down(stats, app, pygame.K_RIGHT)
    assert stats.catalogue is oll


# --- choosing cases ---------------------------------------------------------

def tile_of(picker, case_id):
    for _, _, cases in picker.rows():
        for case, rect in cases:
            if case.id == case_id:
                return rect
    raise AssertionError(f"{case_id} is not on the grid")


def border_colours(surface, rect):
    """The colours painted along a tile's own edge, corners excluded."""
    inset = 8
    edge = [(x, rect.top) for x in range(rect.left + inset, rect.right - inset)]
    edge += [(x, rect.bottom - 1) for x in range(rect.left + inset, rect.right - inset)]
    edge += [(rect.left, y) for y in range(rect.top + inset, rect.bottom - inset)]
    edge += [(rect.right - 1, y) for y in range(rect.top + inset, rect.bottom - inset)]
    return {surface.get_at(point)[:3] for point in edge}


def test_nothing_is_chosen_until_the_cuber_chooses_it(app, catalogue):
    """Arriving with all fifty-seven selected means "drill these three" starts
    with deselecting fifty-four."""
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    assert picker.selected == set()


def test_a_all_chooses_every_case_and_n_clears_them(app, catalogue):
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    key_down(picker, app, pygame.K_a)
    assert picker.selected == {c.id for c in catalogue}
    key_down(picker, app, pygame.K_n)
    assert picker.selected == set()


def test_a_chosen_case_is_ringed_in_green(app, catalogue):
    """The mark has to survive being glanced at across a grid, which a dot in
    one corner does not."""
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    surface = pygame.Surface((1180, 780))
    chosen_id = picker.current.id
    rect = tile_of(picker, chosen_id)

    picker.draw(surface)
    assert READY not in border_colours(surface, rect)

    key_down(picker, app, pygame.K_SPACE)
    assert picker.selected == {chosen_id}
    picker.draw(surface)
    assert READY in border_colours(surface, rect)

    key_down(picker, app, pygame.K_SPACE)
    picker.draw(surface)
    assert READY not in border_colours(surface, rect)


def test_the_cursor_and_the_choice_are_both_visible_on_one_tile(app, catalogue):
    """They are different facts, and the tile the cursor is on is exactly the
    tile you are about to choose."""
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    surface = pygame.Surface((1180, 780))
    key_down(picker, app, pygame.K_a)
    picker.draw(surface)
    rect = tile_of(picker, picker.current.id)
    painted = {surface.get_at((x, y))[:3]
               for x in range(rect.left, rect.right)
               for y in range(rect.top, rect.bottom)}
    assert READY in painted, "chosen is not marked"
    assert ACCENT in painted, "the cursor is not marked"


def test_the_library_marks_nothing_as_chosen(app, catalogue):
    """Browsing is not choosing; a green border there would promise a drill
    that is not about to happen."""
    picker = PickerScreen(app, mode="browse", catalogue=catalogue)
    surface = pygame.Surface((1180, 780))
    picker.draw(surface)
    for _, _, cases in picker.rows():
        for _, rect in cases:
            assert READY not in border_colours(surface, rect)
