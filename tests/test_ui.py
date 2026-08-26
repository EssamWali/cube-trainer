"""The interface, driven headlessly.

These are the tests that would have caught the case-picture bug: they run the
real screens, with the real store, and check what actually gets recorded when
somebody presses the keys.
"""

import pygame
import pytest

from cubetrainer.cases import pll
from cubetrainer.cube import Cube
from cubetrainer.store import Store
from cubetrainer.trainer.timer import TimerState
from cubetrainer.ui import render
from cubetrainer.ui.app import App, DrillScreen, HomeScreen, PickerScreen, StatsScreen


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


def test_the_library_is_the_picker_in_browse_mode(app):
    home = HomeScreen(app)
    result = key_down(home, app, pygame.K_2)
    assert isinstance(result, PickerScreen)
    assert result.mode == "browse"


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
