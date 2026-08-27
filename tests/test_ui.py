"""The interface, driven headlessly.

These are the tests that would have caught the case-picture bug: they run the
real screens, with the real store, and check what actually gets recorded when
somebody presses the keys.
"""

import pygame
import pytest

from cubetrainer.cases import CATALOGUES, Case, Catalogue, pll
from cubetrainer.cube import Cube
from cubetrainer.store import Store
from cubetrainer.store.stats import case_report
from cubetrainer.trainer.scramble import scramble_for
from cubetrainer.trainer.timer import TimerState
from cubetrainer.ui import render
from cubetrainer.ui.app import (SOLVE_PHASES, WHOLE_SOLVE, App, DrillScreen,
                               HomeScreen,
                               algorithm_for,
                               PickerScreen, SolveScreen, SolveSetupScreen,
                               StatsScreen, solve_split_labels)
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
                   drill, SolveSetupScreen(app), SolveScreen(app),
                   StatsScreen(app)):
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


def test_discarding_a_finished_rep_amends_it_rather_than_recording_another(app):
    """The help line says "discard as DNF". Recording a second rep alongside the
    one being discarded is the opposite of that: it keeps the time and adds a
    DNF to the case's record."""
    drill = DrillScreen(app, ["T"])
    do_a_rep(drill, app, start=0.0, finish=2.5)
    assert len(app.store.reps()) == 1

    key_down(drill, app, pygame.K_d)
    rep, = app.store.reps()
    assert rep["penalty"] == "dnf"
    assert rep["duration_ms"] is None
    assert drill.stage == "reset"
    assert drill.times == [] and drill.dnfs == 1

    key_down(drill, app, pygame.K_d)
    assert len(app.store.reps()) == 1, "discarding twice discarded twice"
    assert drill.dnfs == 1


def test_a_discarded_rep_counts_as_one_attempt_in_the_statistics(app):
    """`attempts` and `dnf_rate` are counted over reps, and `dnf_rate` is one of
    the signals the ranking uses -- so a rep recorded twice tells a cuber they
    are unreliable at the very cases they discarded on."""
    drill = DrillScreen(app, ["T"])
    do_a_rep(drill, app, start=0.0, finish=2.5)
    key_down(drill, app, pygame.K_d)
    report = case_report("T", app.store.reps(case_id="T"))
    assert report.attempts == 1
    assert report.dnf_rate == 1.0
    assert report.counted == 0


def test_a_penalty_on_a_peeked_rep_leaves_the_running_mean_alone(app):
    """A peeked rep never entered `times`, because a time achieved while reading
    the answer is not a time. So neither penalty may reach in there for one:
    the entry it would correct belongs to some earlier rep."""
    drill = DrillScreen(app, ["T", "Ja"])
    do_a_rep(drill, app, start=0.0, finish=2.5)
    key_down(drill, app, pygame.K_SPACE)
    key_down(drill, app, pygame.K_p)
    assert drill.peeked
    do_a_rep(drill, app, start=10.0, finish=14.0)
    counted = list(drill.times)
    assert counted == [pytest.approx(1.8, abs=0.01)]

    key_down(drill, app, pygame.K_2)
    assert drill.times == counted, "the peeked rep's +2 reached a counted one"
    peeked_rep = app.store.reps()[-1]
    assert peeked_rep["penalty"] == "plus_two"
    assert peeked_rep["duration_ms"] == pytest.approx(5300, abs=1)

    key_down(drill, app, pygame.K_d)
    assert drill.times == counted, "the peeked rep's discard reached a counted one"


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
    assert [group for group, _, _ in picker.blocks] == list(catalogue.group_order)
    placed = [case.id for case, _ in picker.tiles()]
    assert sorted(placed) == sorted(c.id for c in catalogue)


def test_every_case_is_drawn_on_the_screen(app, catalogue):
    """Fifty-seven cases at the tile size twenty-one used would run off the
    bottom of the window, and a case you cannot see is a case you cannot pick."""
    picker = PickerScreen(app, mode="select", catalogue=catalogue)
    window = pygame.Rect(0, 0, *app.surface.get_size())
    for case, rect in picker.tiles():
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


def _lands_on(state, promised):
    """Whether two states are the same case, whichever phase the case is of.

    Each phase has its own answer to "same case", because each asks a different
    question of the cube: where the last layer's pieces belong, which way they
    face, or where one pair is. The reading is picked by what the state is, the
    way the picture is."""
    from cubetrainer.cases.pattern import (case_key, is_last_layer_oriented,
                                           is_oll_state, is_pll_state,
                                           orientation_key, pair_key,
                                           slot_in_progress)
    slot = slot_in_progress(promised)
    if slot is not None:
        return (slot_in_progress(state) == slot
                and pair_key(state, slot) == pair_key(promised, slot))
    if is_last_layer_oriented(promised):
        return is_pll_state(state) and case_key(state) == case_key(promised)
    return is_oll_state(state) and orientation_key(state) == orientation_key(promised)


def test_the_scramble_produces_the_case_being_drilled_in_any_phase(app, catalogue):
    """The trainer's central claim, for whichever phase is being drilled."""
    drill = DrillScreen(app, [c.id for c in catalogue], catalogue)
    for _ in range(25):
        assert _lands_on(Cube.solved().apply(drill.scramble),
                         Cube.solved().apply(drill.case.setup)), drill.case.id
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
        SolveSetupScreen(app),
        SolveScreen(app),
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
    one = app.catalogues[1]
    drill_a_few(app, one, first_ids(one)[0])
    stats = StatsScreen(app, catalogues=[one])
    assert stats.catalogue is one
    assert [r.case_id for r in stats.reports] == first_ids(one)
    key_down(stats, app, pygame.K_RIGHT)
    assert stats.catalogue is one


# --- choosing cases ---------------------------------------------------------

def tile_of(picker, case_id):
    for case, rect in picker.tiles():
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
    for _, rect in picker.tiles():
        assert READY not in border_colours(surface, rect)


def test_families_are_laid_out_side_by_side_rather_than_one_per_band(app):
    """Fifteen families each taking a full band would not fit on the screen at
    any tile size worth looking at, so they are packed along a band and
    wrapped."""
    picker = PickerScreen(app, mode="select", catalogue=app.catalogues[1])
    bands = {top for _, (_, top), _ in picker.blocks}
    assert len(picker.blocks) == 15
    assert len(bands) < len(picker.blocks), "every family is on its own band"


def test_a_bigger_phase_does_not_mean_a_smaller_picture_than_it_needs(app):
    """The tile size is the largest that fits, so an empty half-screen means
    the layout gave up early."""
    for catalogue in app.catalogues:
        picker = PickerScreen(app, mode="select", catalogue=catalogue)
        bigger = [t for t in picker.TILE_SIZES if t > picker.tile]
        available = picker.detail_top - picker.GRID_TOP - 12
        for tile in bigger:
            _, height = picker._flow(tile)
            assert height > available,                 f"{catalogue.phase} could have used {tile}px tiles"


def test_up_and_down_move_between_families(app):
    """The grid is not one rectangle any more, so moving down has to land on
    whatever is actually below rather than counting a fixed stride."""
    picker = PickerScreen(app, mode="select", catalogue=app.catalogues[1])
    start = picker.rect_for(picker.current)
    key_down(picker, app, pygame.K_DOWN)
    below = picker.rect_for(picker.current)
    assert below.centery > start.centery
    key_down(picker, app, pygame.K_UP)
    assert picker.rect_for(picker.current).centery == start.centery


# --- timing a solve ---------------------------------------------------------

def do_a_solve(solve, application, start=0.0, presses=()):
    """Arm, start, and press at each boundary the way a cuber would."""
    key_down(solve, application, pygame.K_SPACE, now=start)
    solve.update(start + 0.7)
    key_up(solve, application, pygame.K_SPACE, now=start + 0.7)
    assert solve.timer.state is TimerState.RUNNING
    for at in presses:
        key_down(solve, application, pygame.K_SPACE, now=at)


def test_the_home_screen_offers_timing_a_solve(app):
    home = HomeScreen(app)
    labels = [label for label, _ in home.items]
    assert "Time a solve" in labels
    result = key_down(app, app, pygame.K_1) if False else key_down(
        home, app, pygame.K_1 + labels.index("Time a solve"))
    assert isinstance(result, SolveSetupScreen)


def test_a_run_with_no_boundary_cannot_start(app):
    """A timer with nothing to stop at would never stop. Same rule as a drill
    with no cases chosen."""
    setup = SolveSetupScreen(app, phases=())
    assert key_down(setup, app, pygame.K_RETURN) is None
    key_down(setup, app, pygame.K_SPACE)  # tick whatever the cursor is on
    assert isinstance(key_down(setup, app, pygame.K_RETURN), SolveScreen)


def test_a_run_starts_out_timing_the_whole_solve_in_one_go(app):
    """What most people want most of the time is a timer: pick the cube up, put
    it down, read the number. Splitting a solve four ways is the thing you opt
    into, not the thing you have to opt out of."""
    setup = SolveSetupScreen(app)
    assert setup.ticked == WHOLE_SOLVE
    assert setup.in_one_go
    assert "one go" in setup.summary

    solve = key_down(setup, app, pygame.K_RETURN)
    assert isinstance(solve, SolveScreen)
    assert solve.in_one_go
    assert solve.whole, "a solve in one go is still a whole solve"


def test_one_press_stops_a_solve_timed_in_one_go(app):
    solve = SolveScreen(app, WHOLE_SOLVE)
    do_a_solve(solve, app, presses=(18.0,))
    assert solve.timer.is_finished
    assert solve.stage == "result", "a whole solve ends on a solved cube"
    recorded, = app.store.solves()
    assert recorded["duration_ms"] == pytest.approx(17300, abs=2)


def test_a_solve_timed_in_one_go_records_no_splits(app):
    """One split covering the whole solve is the solve's own time written down a
    second time, and it would put a phase in the phase means whose mean is just
    the solve mean."""
    solve = SolveScreen(app, WHOLE_SOLVE)
    do_a_solve(solve, app, presses=(18.0,))
    assert app.store.splits() == []
    assert len(app.store.solves(whole_only=True)) == 1, "it is still a solve"


def test_timing_in_one_go_and_splitting_share_the_solve_average(app):
    """Both are whole solves, however many times you pressed on the way, so they
    belong in the same average -- unlike a run that stops at the cross."""
    quick = SolveScreen(app, WHOLE_SOLVE)
    do_a_solve(quick, app, presses=(18.0,))
    key_down(quick, app, pygame.K_ESCAPE)

    split = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(split, app, start=30.0, presses=(32.0, 40.0, 44.0, 48.0))
    key_down(split, app, pygame.K_ESCAPE)

    assert len(app.store.solves(whole_only=True)) == 2
    assert len(app.store.splits()) == 4, "only the split run has splits"


def test_n_takes_the_boundaries_off_the_way_and_a_puts_them_back(app):
    setup = SolveSetupScreen(app, phases=SOLVE_PHASES)
    assert not setup.in_one_go
    key_down(setup, app, pygame.K_n)
    assert setup.ticked == WHOLE_SOLVE
    key_down(setup, app, pygame.K_a)
    assert setup.ticked == SOLVE_PHASES
    assert not setup.in_one_go


def test_a_run_that_stops_early_is_never_one_go(app):
    """Timing only the cross is one press too, and it is not a whole solve, so
    it keeps its split: that split is the only place the cross time is filed."""
    setup = SolveSetupScreen(app, phases=("Cross",))
    assert not setup.in_one_go
    solve = SolveScreen(app, ("Cross",))
    assert not solve.in_one_go
    do_a_solve(solve, app, presses=(3.0,))
    assert [split["phase"] for split in app.store.splits()] == ["Cross"]


def test_every_stage_of_a_solve_in_one_go_draws(app):
    surface = pygame.Surface((1180, 780))
    setup = SolveSetupScreen(app)
    setup.draw(surface)
    solve = SolveScreen(app, WHOLE_SOLVE)
    solve.draw(surface)
    do_a_solve(solve, app, presses=())
    solve.draw(surface)
    key_down(solve, app, pygame.K_SPACE, now=18.0)
    solve.draw(surface)


def test_the_boundaries_are_ticked_and_untickable(app):
    setup = SolveSetupScreen(app, phases=())
    key_down(setup, app, pygame.K_a)
    assert setup.ticked == SOLVE_PHASES
    key_down(setup, app, pygame.K_SPACE)
    assert SOLVE_PHASES[0] not in setup.ticked
    assert setup.inspection is True
    key_down(setup, app, pygame.K_i)
    assert setup.inspection is False


def test_a_phase_with_no_boundary_is_named_in_the_split_that_covers_it():
    """Calling the second press of a Cross-and-PLL run "PLL" would file three
    phases of work under the name of one, and the statistics read these
    labels."""
    assert solve_split_labels(SOLVE_PHASES) == SOLVE_PHASES
    assert solve_split_labels({"Cross", "PLL"}) == ("Cross", "F2L+OLL+PLL")
    assert solve_split_labels({"OLL"}) == ("Cross+F2L+OLL",)
    assert solve_split_labels({"Cross"}) == ("Cross",)


def test_each_press_closes_a_phase_and_the_last_one_stops_the_timer(app):
    solve = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(solve, app, presses=(2.0, 10.0))
    assert solve.timer.state is TimerState.RUNNING
    assert len(solve.timer.splits()) == 2
    key_down(solve, app, pygame.K_SPACE, now=14.0)
    key_down(solve, app, pygame.K_SPACE, now=18.0)
    assert solve.timer.is_finished


def test_timing_only_the_cross_stops_at_the_cross(app):
    """The same screen and the same timer, with one boundary instead of four."""
    solve = SolveScreen(app, ("Cross",))
    assert solve.labels == ("Cross",)
    do_a_solve(solve, app, presses=(3.0,))
    assert solve.timer.is_finished
    recorded, = app.store.solves()
    assert recorded["duration_ms"] == pytest.approx(2300, abs=2)


def test_a_solve_is_recorded_with_its_scramble_total_and_splits(app):
    solve = SolveScreen(app, SOLVE_PHASES)
    scramble = solve.scramble
    do_a_solve(solve, app, presses=(2.0, 10.0, 14.0, 18.0))
    recorded, = app.store.solves()
    assert recorded["scramble"] == scramble
    assert recorded["duration_ms"] == pytest.approx(17300, abs=2)
    splits = app.store.splits()
    assert [s["phase"] for s in splits] == list(SOLVE_PHASES)
    assert [s["duration_ms"] for s in splits] == [
        pytest.approx(1300, abs=2), pytest.approx(8000, abs=2),
        pytest.approx(4000, abs=2), pytest.approx(4000, abs=2)]


def test_the_scramble_never_asks_the_cuber_to_rotate_the_cube(app):
    solve = SolveScreen(app, SOLVE_PHASES)
    for _ in range(20):
        assert all(move[0] in "RULFDB" for move in solve.scramble.split())
        solve._next_scramble()


def test_a_session_of_solves_is_tagged_as_such(app):
    whole = SolveScreen(app, SOLVE_PHASES)
    cross = SolveScreen(app, ("Cross",))
    sessions = {s["id"]: s for s in app.store.sessions()}
    assert sessions[whole.session]["kind"] == "solve"
    assert sessions[whole.session]["phase"] is None, "a whole solve is not one phase"
    assert sessions[cross.session]["phase"] == "Cross"


def test_inspection_counts_down_and_its_overrun_reaches_the_record(app):
    solve = SolveScreen(app, ("Cross",), inspection=True)
    key_down(solve, app, pygame.K_i, now=0.0)
    assert solve.timer.state is TimerState.INSPECTING
    key_down(solve, app, pygame.K_SPACE, now=16.0)
    solve.update(16.7)
    key_up(solve, app, pygame.K_SPACE, now=16.7)
    assert solve.timer.state is TimerState.RUNNING
    key_down(solve, app, pygame.K_SPACE, now=20.0)
    recorded, = app.store.solves()
    assert recorded["penalty"] == "plus_two"
    assert recorded["duration_ms"] == pytest.approx(5300, abs=2)


def test_an_inspection_over_seventeen_seconds_is_a_dnf(app):
    solve = SolveScreen(app, ("Cross",), inspection=True)
    key_down(solve, app, pygame.K_i, now=0.0)
    key_down(solve, app, pygame.K_SPACE, now=18.0)
    solve.update(18.7)
    key_up(solve, app, pygame.K_SPACE, now=18.7)
    key_down(solve, app, pygame.K_SPACE, now=22.0)
    recorded, = app.store.solves()
    assert recorded["penalty"] == "dnf"
    assert recorded["duration_ms"] is None


def test_releasing_early_during_inspection_goes_back_to_inspecting(app):
    """The same guard the drill has, except that giving up an arm mid-inspection
    must not hand back the inspection time already spent."""
    solve = SolveScreen(app, ("Cross",), inspection=True)
    key_down(solve, app, pygame.K_i, now=0.0)
    key_down(solve, app, pygame.K_SPACE, now=3.0)
    key_up(solve, app, pygame.K_SPACE, now=3.2)
    assert solve.timer.state is TimerState.INSPECTING
    assert solve.timer.inspection_elapsed(3.2) == pytest.approx(3.2)


def test_a_whole_solve_goes_straight_on_but_a_part_solve_asks_for_a_reset(app):
    """Every scramble here assumes a solved cube. A whole solve ends on one; a
    run that stopped at the cross did not."""
    whole = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(whole, app, presses=(2.0, 10.0, 14.0, 18.0))
    assert whole.stage == "result"

    cross = SolveScreen(app, ("Cross",))
    do_a_solve(cross, app, start=30.0, presses=(33.0,))
    assert cross.stage == "reset"
    key_down(cross, app, pygame.K_SPACE)
    assert cross.stage == "scramble"


def test_a_plus_two_updates_the_recorded_total(app):
    solve = SolveScreen(app, ("Cross",))
    do_a_solve(solve, app, presses=(3.0,))
    before, = app.store.solves()
    key_down(solve, app, pygame.K_2)
    after, = app.store.solves()
    assert after["penalty"] == "plus_two"
    assert after["duration_ms"] == before["duration_ms"] + 2000


def test_a_fumble_is_recorded_as_a_dnf_with_no_time_and_no_splits(app):
    solve = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(solve, app, presses=(2.0, 10.0))
    key_down(solve, app, pygame.K_d)
    recorded, = app.store.solves()
    assert recorded["penalty"] == "dnf"
    assert recorded["duration_ms"] is None
    assert app.store.splits() == [], "a fumbled attempt has no times in it"
    assert solve.stage == "reset"


def test_leaving_a_run_of_solves_closes_its_session(app):
    solve = SolveScreen(app, SOLVE_PHASES)
    assert key_down(solve, app, pygame.K_ESCAPE) == "back"
    session, = [s for s in app.store.sessions() if s["id"] == solve.session]
    assert session["ended_at"] is not None


def test_only_whole_solves_reach_the_solve_average(app):
    """A cross time and a solve time are both times, and one average over both
    is a number about nothing. The phase splits keep every attempt, because
    there they are filed under what they actually measured."""
    whole = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(whole, app, presses=(2.0, 10.0, 14.0, 18.0))
    key_down(whole, app, pygame.K_ESCAPE)

    cross = SolveScreen(app, ("Cross",))
    do_a_solve(cross, app, start=30.0, presses=(33.0,))
    key_down(cross, app, pygame.K_ESCAPE)

    assert len(app.store.solves()) == 2
    assert len(app.store.solves(whole_only=True)) == 1
    assert len(app.store.splits()) == 5


def test_a_solve_contributes_no_reps_and_no_case(app):
    """Which OLL and which PLL came up depends on how the cuber built their
    F2L, which the application never sees. So a solve may not put anything
    into a per-case ranking."""
    solve = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(solve, app, presses=(2.0, 10.0, 14.0, 18.0))
    key_down(solve, app, pygame.K_ESCAPE)
    assert app.store.reps() == []
    assert app.store.practised_case_ids() == []
    for catalogue in app.catalogues:
        stats = show_phase(StatsScreen(app), app, catalogue)
        assert stats.reports == []
        stats.draw(pygame.Surface((1180, 780)))


def test_the_statistics_show_what_a_run_of_solves_recorded(app):
    """The solve summary and the phase-split line had nothing to draw before
    there was a screen that recorded a solve."""
    solve = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(solve, app, presses=(2.0, 10.0, 14.0, 18.0))
    key_down(solve, app, pygame.K_ESCAPE)

    surface = pygame.Surface((1180, 780))
    band = pygame.Rect(0, 80, 1180, 64)

    def summary_band(application):
        surface.fill((0, 0, 0))
        StatsScreen(application).draw(surface)
        return pygame.image.tostring(surface.subsurface(band), "RGB")

    with_solve = summary_band(app)
    empty = App(store=Store.in_memory(), seed=1)
    assert with_solve != summary_band(empty), "the solve reached nothing on screen"


def test_every_stage_of_a_run_of_solves_draws(app):
    surface = pygame.Surface((1180, 780))
    solve = SolveScreen(app, SOLVE_PHASES)
    solve.draw(surface)
    key_down(solve, app, pygame.K_i, now=0.0)
    solve.draw(surface)
    do_a_solve(solve, app, start=2.0, presses=(6.0, 10.0))
    solve.draw(surface)
    key_down(solve, app, pygame.K_SPACE, now=14.0)
    key_down(solve, app, pygame.K_SPACE, now=18.0)
    solve.draw(surface)
    key_down(solve, app, pygame.K_d)
    solve.draw(surface)


def test_discarding_a_finished_attempt_amends_it_rather_than_adding_one(app):
    """Pressing d on a time you have already stopped says that attempt was not
    a solve. It does not say there was a second attempt that was not one."""
    solve = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(solve, app, presses=(2.0, 10.0, 14.0, 18.0))
    assert len(app.store.solves()) == 1

    key_down(solve, app, pygame.K_d)
    recorded, = app.store.solves()
    assert recorded["penalty"] == "dnf"
    assert recorded["duration_ms"] is None
    assert app.store.splits() == [], "a DNF takes its splits with it"
    assert solve.dnfs == 1 and solve.times == []

    key_down(solve, app, pygame.K_d)
    assert len(app.store.solves()) == 1, "discarding twice discarded twice"
    assert solve.dnfs == 1


# --- your own algorithm -----------------------------------------------------

#: The M-slice Ua perm: a real algorithm for the case, nothing like the shipped
#: one, so a test cannot pass by accident on a string that merely looks right.
MINE = "M2 U M U2 M' U M2"


def a_library(application, case_id="Ua"):
    library = PickerScreen(application, mode="browse", catalogue=pll.CATALOGUE)
    library.cursor = library.order.index(pll.get(case_id))
    return library


def type_algorithm(library, application, text, submit=True):
    """Open the prompt, clear what it was filled with, and type."""
    key_down(library, application, pygame.K_e)
    for _ in range(len(library.prompt_text)):
        key_down(library, application, pygame.K_BACKSPACE)
    for character in text:
        key_down(library, application, pygame.K_a, unicode=character)
    if submit:
        key_down(library, application, pygame.K_RETURN)
    return library


def test_the_prompt_starts_from_the_algorithm_on_screen(app):
    """Most of the time a cuber is changing a move or two, not writing one out."""
    library = a_library(app)
    key_down(library, app, pygame.K_e)
    assert library.prompt == "algorithm"
    assert library.prompt_text == pll.get("Ua").algorithm


def test_the_library_keeps_your_own_algorithm(app):
    library = type_algorithm(a_library(app), app, MINE)
    assert library.prompt is None
    assert app.store.algorithm_overrides() == {"Ua": MINE}
    assert algorithm_for(pll.get("Ua"), app.overrides) == MINE, \
        "the panel still shows the shipped algorithm you just replaced"
    library.draw(pygame.Surface((1180, 780)))


def test_an_algorithm_that_does_not_solve_the_case_is_refused(app):
    library = type_algorithm(a_library(app), app, "R U R'")
    assert library.prompt == "algorithm", "the prompt closed on a refusal"
    assert library.prompt_text == "R U R'", "what was typed was thrown away"
    assert "Ua perm" in library.prompt_error
    assert app.store.algorithm_overrides() == {}
    library.draw(pygame.Surface((1180, 780)))


def test_an_algorithm_that_leaves_the_cube_turned_round_is_refused(app):
    library = type_algorithm(a_library(app), app, MINE + " y")
    assert library.prompt == "algorithm"
    assert "turned round" in library.prompt_error
    assert app.store.algorithm_overrides() == {}


def test_a_sequence_the_cube_does_not_understand_is_refused(app):
    library = type_algorithm(a_library(app), app, "R U Q")
    assert library.prompt == "algorithm"
    assert "Q" in library.prompt_error
    assert app.store.algorithm_overrides() == {}


def test_an_empty_algorithm_is_refused(app):
    library = type_algorithm(a_library(app), app, "")
    assert library.prompt == "algorithm"
    assert app.store.algorithm_overrides() == {}


def test_correcting_a_refusal_clears_what_it_said(app):
    library = type_algorithm(a_library(app), app, "R U R'")
    assert library.prompt_error
    key_down(library, app, pygame.K_BACKSPACE)
    assert library.prompt_error is None


def test_the_shipped_algorithm_comes_back(app):
    library = type_algorithm(a_library(app), app, MINE)
    key_down(library, app, pygame.K_r)
    assert app.store.algorithm_overrides() == {}
    assert algorithm_for(pll.get("Ua"), app.overrides) == pll.get("Ua").algorithm
    key_down(library, app, pygame.K_r)
    assert app.store.algorithm_overrides() == {}


def test_your_algorithm_is_what_the_drill_reveals(app):
    type_algorithm(a_library(app), app, MINE)
    drill = DrillScreen(app, ["Ua"])
    key_down(drill, app, pygame.K_p)
    assert drill.peeked
    assert algorithm_for(drill.case, app.overrides) == MINE
    drill.draw(pygame.Surface((1180, 780)))


def test_seconds_per_move_is_counted_off_your_algorithm(app):
    """Ranking by seconds per move is the default signal, and a cuber using a
    seven-move algorithm is not doing eleven moves' worth of work."""
    drill = DrillScreen(app, ["Ua"])
    do_a_rep(drill, app, start=0.0, finish=2.5)
    key_down(drill, app, pygame.K_ESCAPE)

    shipped = StatsScreen(app).reports[0].seconds_per_move
    type_algorithm(a_library(app), app, MINE)
    mine = StatsScreen(app).reports[0].seconds_per_move
    assert shipped != mine
    assert mine == pytest.approx(1.8 / 7, abs=1e-6)


def test_your_algorithm_does_not_change_the_scramble(app):
    """A scramble is the inverse of the case's setup, not of the algorithm on
    screen. An override changes what the trainer tells you to do; it must never
    change what it hands you, or the promise that a scramble lands on the case
    it names stops being checkable."""
    case = pll.get("Ua")
    before = scramble_for(case, randomise_angle=False)
    type_algorithm(a_library(app), app, MINE)
    assert scramble_for(case, randomise_angle=False) == before
    assert Cube.solved().apply(before).apply(case.algorithm).is_solved()


def test_your_algorithm_survives_a_restart(app):
    """Overrides live in their own table so that updating the application never
    overwrites what someone has learned."""
    type_algorithm(a_library(app), app, MINE)
    again = App(store=app.store, seed=1)
    assert algorithm_for(pll.get("Ua"), again.overrides) == MINE


def test_an_override_for_a_case_nobody_recognises_breaks_nothing(app):
    """History outlives the case list, and so does an algorithm someone chose
    for a case that is no longer in it."""
    app.store.set_algorithm("NotACase", "R U R'")
    app.overrides = app.store.algorithm_overrides()
    surface = pygame.Surface((1180, 780))
    a_library(app).draw(surface)
    StatsScreen(app).draw(surface)


# --- three phases, one set of screens ---------------------------------------

def test_every_phase_the_trainer_has_is_offered(app):
    """The home screen names no phase. It builds a drill and a library for each
    catalogue it is handed, so a phase arriving is data."""
    labels = [label for label, _ in HomeScreen(app).items]
    for catalogue in app.catalogues:
        assert f"Drill {catalogue.phase}" in labels
        assert f"{catalogue.phase} algorithm library" in labels
    assert {"PLL", "OLL", "F2L"} <= {c.phase for c in app.catalogues}


def test_a_phase_the_trainer_has_never_heard_of_is_offered_too(app):
    """The claim behind all of this, tested rather than asserted: hand the
    screens a catalogue nobody wrote them for and they offer it."""
    invented = Catalogue("XLL", (Case("XLL 1", "XLL 1", "Odd ones",
                                      "R U R' U'", "a made-up case"),), ("Odd ones",))
    app.catalogues = app.catalogues + (invented,)
    labels = [label for label, _ in HomeScreen(app).items]
    assert "Drill XLL" in labels
    assert "XLL algorithm library" in labels

    picker = PickerScreen(app, mode="select", catalogue=invented)
    assert [case.id for case in picker.order] == ["XLL 1"]
    picker.draw(pygame.Surface((1180, 780)))
    StatsScreen(app).draw(pygame.Surface((1180, 780)))


def test_the_picker_shows_all_forty_one_f2l_cases_by_family(app):
    f2l_catalogue = next(c for c in app.catalogues if c.phase == "F2L")
    picker = PickerScreen(app, mode="select", catalogue=f2l_catalogue)
    assert len(picker.order) == 41
    assert [group for group, _, _ in picker.blocks] == list(f2l_catalogue.group_order)
    picker.draw(pygame.Surface((1180, 780)))


def test_drilling_a_phase_and_pressing_at_its_boundary_stay_apart(app):
    """"F2L" names a phase you can drill and a boundary you can press at while
    timing a solve. A rep is a rep and a split is a split, and neither may show
    up in the other's figures."""
    f2l_catalogue = next(c for c in app.catalogues if c.phase == "F2L")
    case_id, = first_ids(f2l_catalogue)
    drill_a_few(app, f2l_catalogue, case_id, count=2)

    solve = SolveScreen(app, SOLVE_PHASES)
    do_a_solve(solve, app, start=100.0, presses=(102.0, 110.0, 114.0, 118.0))
    key_down(solve, app, pygame.K_ESCAPE)

    assert len(app.store.reps(phase="F2L")) == 2, "a split was counted as a rep"
    assert len(app.store.solves()) == 1
    assert [s["phase"] for s in app.store.splits()] == list(SOLVE_PHASES)
    assert app.store.practised_case_ids("F2L") == [case_id], \
        "a phase split reached the per-case ranking"

    stats = show_phase(StatsScreen(app), app, f2l_catalogue)
    assert [r.case_id for r in stats.reports] == [case_id]
    assert stats.reports[0].attempts == 2
    stats.draw(pygame.Surface((1180, 780)))


def test_an_f2l_rep_ends_on_a_solved_cube_like_any_other(app):
    """Worth checking rather than assuming. A real F2L insert leaves the last
    layer scrambled, so it would be fair to expect this drill to need a reset
    afterwards the way a run that stops at the cross does. It does not: the
    scramble is the inverse of the algorithm, so adjusting the upper face and
    executing takes the whole cube back to solved -- as true of an F2L case as
    of an OLL one, and the reason the drill needed no changes at all."""
    f2l_catalogue = next(c for c in app.catalogues if c.phase == "F2L")
    for case in f2l_catalogue:
        drill = DrillScreen(app, [case.id], f2l_catalogue)
        state = Cube.solved().apply(drill.scramble)
        assert any(state.apply(auf).apply(case.algorithm).is_solved()
                   for auf in ("", "U", "U2", "U'")), case.id
