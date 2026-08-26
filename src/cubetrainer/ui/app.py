"""The pygame application: menu, case picker, drill loop and statistics.

Screens are a stack. The picker and the algorithm library are the same screen
in two modes, because they show identical content and differ only in whether
choosing a case selects it or just looks at it.
"""

import random
import sys

import pygame

from ..cases import pll
from ..cube import Cube
from ..cube.notation import move_count
from ..store import Store
from ..store.stats import case_report, phase_summary, rank_by_weakness, solve_summary
from ..trainer.sampler import RoundRobinSampler
from ..trainer.scramble import scramble_for
from ..trainer.timer import Penalty, SolveTimer, TimerState
from . import render, theme
from .theme import ACCENT, ARMED, BACKGROUND, DANGER, PANEL, READY, TEXT, TEXT_DIM

WINDOW = (1180, 780)
FPS = 60
LAST_USED = "__last used__"


def algorithm_for(case, overrides):
    """A cuber's own algorithm for a case, or the shipped default."""
    return overrides.get(case.id, case.algorithm)


class Screen:
    """One page of the interface."""

    def handle(self, event):
        """Return a screen to push, "back" to pop, or None to stay."""
        return None

    def update(self, now):
        pass

    def draw(self, surface):
        raise NotImplementedError


# --------------------------------------------------------------------------
class HomeScreen(Screen):
    def __init__(self, app):
        self.app = app
        self.cursor = 0
        self.items = [
            ("Drill PLL", lambda: PickerScreen(self.app, mode="select")),
            ("Algorithm library", lambda: PickerScreen(self.app, mode="browse")),
            ("Statistics", lambda: StatsScreen(self.app)),
        ]

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_DOWN, pygame.K_j):
            self.cursor = (self.cursor + 1) % len(self.items)
        elif event.key in (pygame.K_UP, pygame.K_k):
            self.cursor = (self.cursor - 1) % len(self.items)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return self.items[self.cursor][1]()
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            index = event.key - pygame.K_1
            if index < len(self.items):
                self.cursor = index
                return self.items[index][1]()
        elif event.key == pygame.K_ESCAPE:
            self.app.quit()
        return None

    def draw(self, surface):
        surface.fill(BACKGROUND)
        theme.text(surface, "CUBE TRAINER", (WINDOW[0] // 2, 120), 52, TEXT, True, centre=True)
        theme.text(surface, "targeted scrambles for a physical 3x3",
                   (WINDOW[0] // 2, 182), 20, TEXT_DIM, centre=True)
        for index, (label, _) in enumerate(self.items):
            selected = index == self.cursor
            colour = ACCENT if selected else TEXT
            prefix = "> " if selected else "  "
            theme.text(surface, f"{prefix}{index + 1}. {label}",
                       (WINDOW[0] // 2, 280 + index * 46), 28, colour, selected, centre=True)
        theme.text(surface, "arrows to move, enter to choose, esc to quit",
                   (WINDOW[0] // 2, WINDOW[1] - 60), 17, TEXT_DIM, centre=True)


# --------------------------------------------------------------------------
class PickerScreen(Screen):
    """Choose cases to drill, or browse them with their algorithms.

    Cases are grouped the way cubers talk about them. "I am bad at the diagonal
    corner swaps" is a sentence someone says; "I am bad at V, Y, Na, Nb" is not.
    """

    COLUMNS = 7

    def __init__(self, app, mode="select"):
        self.app = app
        self.mode = mode
        self.groups = pll.by_group()
        self.order = [c for group in pll.GROUP_ORDER for c in self.groups[group]]
        self.cursor = 0
        self.prompt = None
        self.prompt_text = ""
        self.message = None
        restored = app.store.load_case_set(LAST_USED, "PLL") if mode == "select" else None
        self.selected = set(restored or [c.id for c in self.order])
        self.states = {
            c.id: Cube.solved().apply(c.setup) for c in self.order
        }

    @property
    def current(self):
        return self.order[self.cursor]

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if self.prompt is not None:
            return self._handle_prompt(event)
        key = event.key
        if key == pygame.K_ESCAPE:
            return "back"
        if key in (pygame.K_RIGHT, pygame.K_l):
            self.cursor = (self.cursor + 1) % len(self.order)
        elif key in (pygame.K_LEFT, pygame.K_h):
            self.cursor = (self.cursor - 1) % len(self.order)
        elif key in (pygame.K_DOWN, pygame.K_j):
            self.cursor = min(len(self.order) - 1, self.cursor + self.COLUMNS)
        elif key in (pygame.K_UP, pygame.K_k):
            self.cursor = max(0, self.cursor - self.COLUMNS)
        elif self.mode == "select":
            return self._handle_selection(key)
        return None

    def _handle_selection(self, key):
        if key == pygame.K_SPACE:
            case_id = self.current.id
            self.selected.symmetric_difference_update({case_id})
        elif key == pygame.K_a:
            self.selected = {c.id for c in self.order}
        elif key == pygame.K_n:
            self.selected.clear()
        elif key == pygame.K_g:
            group = {c.id for c in self.groups[self.current.group]}
            if group <= self.selected:
                self.selected -= group
            else:
                self.selected |= group
        elif key == pygame.K_s:
            self.prompt, self.prompt_text = "save", ""
        elif key == pygame.K_o:
            names = self.app.store.case_set_names("PLL")
            names = [n for n in names if n != LAST_USED]
            if names:
                self.prompt, self.prompt_text = "load", ""
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if not self.selected:
                self.message = "select at least one case"
                return None
            chosen = [c.id for c in self.order if c.id in self.selected]
            self.app.store.save_case_set(LAST_USED, "PLL", chosen)
            return DrillScreen(self.app, chosen)
        return None

    def _handle_prompt(self, event):
        if event.key == pygame.K_ESCAPE:
            self.prompt = None
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.prompt == "save" and self.prompt_text.strip():
                chosen = [c.id for c in self.order if c.id in self.selected]
                self.app.store.save_case_set(self.prompt_text.strip(), "PLL", chosen)
                self.message = f"saved as {self.prompt_text.strip()!r}"
            self.prompt = None
        elif event.key == pygame.K_BACKSPACE:
            self.prompt_text = self.prompt_text[:-1]
        elif self.prompt == "load" and event.unicode.isdigit():
            names = [n for n in self.app.store.case_set_names("PLL") if n != LAST_USED]
            index = int(event.unicode) - 1
            if 0 <= index < len(names):
                loaded = self.app.store.load_case_set(names[index], "PLL")
                self.selected = set(loaded or [])
                self.message = f"loaded {names[index]!r}"
                self.prompt = None
        elif self.prompt == "save" and event.unicode.isprintable():
            self.prompt_text += event.unicode
        return None

    def draw(self, surface):
        surface.fill(BACKGROUND)
        title = "Choose cases to drill" if self.mode == "select" else "Algorithm library"
        theme.text(surface, title, (40, 28), 30, TEXT, True)
        if self.mode == "select":
            theme.text(surface, f"{len(self.selected)} of {len(self.order)} selected",
                       (WINDOW[0] - 40, 36), 20, ACCENT, right=True)

        top = 86
        left = 40
        width, height = 132, 132
        for group in pll.GROUP_ORDER:
            cases = self.groups[group]
            theme.text(surface, group.upper(), (left, top), 16, TEXT_DIM, True)
            top += 24
            for index, case in enumerate(cases):
                rect = pygame.Rect(left + index * (width + 10), top, width, height)
                position = self.order.index(case)
                render.draw_thumbnail(
                    surface, self.states[case.id], rect, case.id,
                    selected=(position == self.cursor),
                    dim=(self.mode == "select" and case.id not in self.selected),
                )
                if self.mode == "select" and case.id in self.selected:
                    pygame.draw.circle(surface, READY, (rect.right - 12, rect.top + 12), 5)
            top += height + 18

        self._draw_detail(surface, top)
        self._draw_help(surface)
        if self.prompt is not None:
            self._draw_prompt(surface)

    def _draw_detail(self, surface, top):
        case = self.current
        panel = pygame.Rect(40, top, WINDOW[0] - 80, 84)
        pygame.draw.rect(surface, PANEL, panel, border_radius=8)
        theme.text(surface, case.name, (panel.left + 16, panel.top + 12), 24, TEXT, True)
        theme.text(surface, case.description, (panel.left + 16, panel.top + 44), 17, TEXT_DIM)
        algorithm = algorithm_for(case, self.app.overrides)
        theme.text(surface, algorithm, (panel.right - 16, panel.top + 14), 20, ACCENT, right=True)
        theme.text(surface, f"{move_count(algorithm)} moves",
                   (panel.right - 16, panel.top + 46), 16, TEXT_DIM, right=True)

    def _draw_help(self, surface):
        if self.mode == "select":
            hint = ("arrows move   space toggles   g whole group   a all   n none   "
                    "s save set   o open set   enter start   esc back")
        else:
            hint = "arrows move   esc back"
        theme.text(surface, self.message or hint,
                   (WINDOW[0] // 2, WINDOW[1] - 30), 16,
                   ACCENT if self.message else TEXT_DIM, centre=True)

    def _draw_prompt(self, surface):
        overlay = pygame.Surface(WINDOW, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))
        box = pygame.Rect(0, 0, 620, 200)
        box.center = (WINDOW[0] // 2, WINDOW[1] // 2)
        pygame.draw.rect(surface, PANEL, box, border_radius=10)
        if self.prompt == "save":
            theme.text(surface, "Name this case set", (box.centerx, box.top + 26), 24, TEXT, True, centre=True)
            theme.text(surface, self.prompt_text + "_", (box.centerx, box.top + 80), 26, ACCENT, centre=True)
            theme.text(surface, "enter to save, esc to cancel", (box.centerx, box.bottom - 40), 16, TEXT_DIM, centre=True)
        else:
            names = [n for n in self.app.store.case_set_names("PLL") if n != LAST_USED]
            theme.text(surface, "Open a case set", (box.centerx, box.top + 20), 24, TEXT, True, centre=True)
            for index, name in enumerate(names[:9]):
                theme.text(surface, f"{index + 1}. {name}", (box.centerx, box.top + 66 + index * 26),
                           19, TEXT, centre=True)
            theme.text(surface, "press a number, esc to cancel", (box.centerx, box.bottom - 34), 16, TEXT_DIM, centre=True)


# --------------------------------------------------------------------------
class DrillScreen(Screen):
    """One case at a time, timed, until you quit.

    The case is not shown while you solve it. Recognising which case you are
    looking at is most of the skill, and a trainer that puts the answer on
    screen trains only the half that was already easy.
    """

    def __init__(self, app, case_ids):
        self.app = app
        self.case_ids = list(case_ids)
        self.sampler = RoundRobinSampler(self.case_ids, app.rng)
        self.session = app.store.start_session("drill", "PLL")
        self.timer = SolveTimer()
        self.stage = "scramble"
        self.peeked = False
        self.case = None
        self.scramble = ""
        self.state = None
        self.last_time = None
        self.last_case = None
        self.times = []
        self.dnfs = 0
        self._next_case()

    def _next_case(self):
        self.case = pll.get(self.sampler.next())
        self.scramble = scramble_for(self.case, self.app.rng)
        self.state = Cube.solved().apply(self.scramble)
        self.timer.reset()
        self.peeked = False
        self.stage = "scramble"

    def _record(self, penalty="none"):
        seconds = self.timer.total()
        self.app.store.record_rep(
            self.session, self.case.id, self.scramble, seconds,
            peeked=self.peeked, penalty=penalty,
        )
        self.last_case = self.case
        if penalty == "dnf":
            self.last_time = None
            self.dnfs += 1
        else:
            self.last_time = seconds
            if not self.peeked:
                self.times.append(seconds)

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            return self._key_down(event)
        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            if self.stage == "scramble":
                self.timer.release(self.app.now)
        return None

    def _key_down(self, event):
        key = event.key
        if key == pygame.K_ESCAPE:
            self.app.store.end_session(self.session)
            return "back"
        if key == pygame.K_p and self.stage == "scramble" and \
                self.timer.state is TimerState.IDLE:
            self.peeked = True
            return None
        if key == pygame.K_d:
            # A fumbled algorithm leaves the cube somewhere the trainer cannot
            # follow, so the only honest recovery is to solve it and start over.
            if self.stage in ("scramble", "result"):
                if self.stage == "scramble" and self.timer.state is TimerState.RUNNING:
                    self.timer.press(self.app.now)
                self._record(penalty="dnf")
                self.stage = "reset"
            return None
        if key == pygame.K_2 and self.stage == "result" and self.last_time is not None:
            self._apply_plus_two()
            return None
        if key == pygame.K_SPACE:
            if self.stage == "result":
                self._next_case()
            elif self.stage == "reset":
                self._next_case()
            else:
                self.timer.press(self.app.now)
                if self.timer.is_finished:
                    self._record()
                    self.stage = "result"
            return None
        return None

    def _apply_plus_two(self):
        rows = self.app.store.reps(session_id=self.session)
        if not rows:
            return
        last = rows[-1]
        self.app.store.connection.execute(
            "UPDATE rep SET penalty = 'plus_two', duration_ms = duration_ms + 2000"
            " WHERE id = ?", (last["id"],)
        )
        self.app.store.connection.commit()
        self.last_time = (last["duration_ms"] + 2000) / 1000.0
        if self.times:
            self.times[-1] = self.last_time

    def update(self, now):
        if self.stage == "scramble":
            self.timer.tick(now)

    def draw(self, surface):
        surface.fill(BACKGROUND)
        running = self.timer.state is TimerState.RUNNING
        theme.text(surface, f"PLL drill   {len(self.case_ids)} cases", (40, 28), 20, TEXT_DIM)
        self._draw_session_line(surface)

        if not running:
            theme.text(surface, self.scramble, (WINDOW[0] // 2, 110), 34, TEXT, True, centre=True)
            theme.text(surface, "apply this to a solved cube",
                       (WINDOW[0] // 2, 156), 17, TEXT_DIM, centre=True)

        self._draw_timer(surface)
        self._draw_picture(surface)
        self._draw_help(surface)

    def _draw_session_line(self, surface):
        done = len(self.times) + self.dnfs
        summary = f"{done} reps"
        if self.times:
            summary += f"   best {theme.format_time(min(self.times))}"
            summary += f"   mean {theme.format_time(sum(self.times) / len(self.times))}"
        if self.dnfs:
            summary += f"   {self.dnfs} DNF"
        theme.text(surface, summary, (WINDOW[0] - 40, 30), 19, TEXT_DIM, right=True)

    def _draw_timer(self, surface):
        state = self.timer.state
        colour, label = TEXT, None
        if self.stage == "reset":
            colour, label = DANGER, "solve your cube, then press space"
            reading = "DNF"
        elif self.stage == "result":
            reading = theme.format_time(self.last_time)
            colour = DANGER if self.last_time is None else READY
            label = f"{self.last_case.name}"
        elif state is TimerState.ARMING:
            colour, reading, label = ARMED, "0.00", "keep holding"
        elif state is TimerState.READY:
            colour, reading, label = READY, "0.00", "release to start"
        elif state is TimerState.RUNNING:
            colour, reading = TEXT, theme.format_time(self.timer.elapsed(self.app.now))
        else:
            colour, reading, label = TEXT_DIM, "0.00", "hold space to arm"
        theme.text(surface, reading, (WINDOW[0] // 2, 210), 96, colour, True, centre=True)
        if label:
            theme.text(surface, label, (WINDOW[0] // 2, 320), 20, colour, centre=True)

    def _draw_picture(self, surface):
        if self.timer.state is TimerState.RUNNING:
            return
        rect = pygame.Rect(0, 0, 230, 230)
        rect.center = (WINDOW[0] // 2, 470)
        revealed = self.peeked or self.stage in ("result", "reset")
        render.draw_case(surface, self.state, rect, hidden=not revealed)
        if revealed:
            algorithm = algorithm_for(self.case, self.app.overrides)
            theme.text(surface, self.case.name, (WINDOW[0] // 2, rect.bottom + 14),
                       24, TEXT, True, centre=True)
            theme.text(surface, algorithm, (WINDOW[0] // 2, rect.bottom + 48),
                       22, ACCENT, centre=True)
            if self.peeked and self.stage != "reset":
                theme.text(surface, "peeked, so this rep is left out of your average",
                           (WINDOW[0] // 2, rect.bottom + 80), 16, TEXT_DIM, centre=True)
        else:
            theme.text(surface, "recognise it yourself, or press p to reveal",
                       (WINDOW[0] // 2, rect.bottom + 14), 17, TEXT_DIM, centre=True)

    def _draw_help(self, surface):
        if self.stage == "reset":
            hint = "space when your cube is solved again"
        elif self.stage == "result":
            hint = "space next case   2 penalty   d discard as DNF   esc end session"
        else:
            hint = "hold space to start   p reveal   d fumbled   esc end session"
        theme.text(surface, hint, (WINDOW[0] // 2, WINDOW[1] - 30), 16, TEXT_DIM, centre=True)


# --------------------------------------------------------------------------
class StatsScreen(Screen):
    """Weak spots as several signals, never as one score.

    A case can be slow, erratic, still being looked up, or dropped often, and
    those call for different practice. A combined score would hide which.
    """

    SIGNALS = (
        ("seconds_per_move", "s/move"),
        ("mean", "mean"),
        ("spread", "spread"),
        ("peek_rate", "peeks"),
        ("dnf_rate", "DNFs"),
    )

    def __init__(self, app):
        self.app = app
        self.signal = 0
        self.reports = self._build()

    def _build(self):
        reports = []
        for case_id in self.app.store.practised_case_ids():
            try:
                case = pll.get(case_id)
            except KeyError:
                continue
            rows = self.app.store.reps(case_id=case_id)
            moves = move_count(algorithm_for(case, self.app.overrides))
            report = case_report(case_id, rows, moves)
            if report:
                reports.append(report)
        return reports

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            return "back"
        if event.key == pygame.K_TAB:
            self.signal = (self.signal + 1) % len(self.SIGNALS)
        return None

    def draw(self, surface):
        surface.fill(BACKGROUND)
        theme.text(surface, "Statistics", (40, 28), 30, TEXT, True)
        signal, label = self.SIGNALS[self.signal]
        theme.text(surface, f"sorted by {label}  (tab to change)",
                   (WINDOW[0] - 40, 36), 19, ACCENT, right=True)

        solves = self.app.store.solves()
        splits = self.app.store.splits()
        top = 84
        if solves:
            summary = solve_summary(solves)
            line = (f"{summary['count']} solves    mean {theme.format_time(summary['mean'])}"
                    f"    ao5 {theme.format_time(summary['ao5'])}"
                    f"    ao12 {theme.format_time(summary['ao12'])}")
            theme.text(surface, line, (40, top), 20, TEXT)
            top += 30
        if splits:
            phases = phase_summary(splits)
            line = "   ".join(
                f"{phase} {theme.format_time(data['mean'])} ({data['count']})"
                for phase, data in phases.items()
            )
            theme.text(surface, line, (40, top), 19, TEXT_DIM)
            top += 30

        top += 14
        if not self.reports:
            theme.text(surface, "No drill reps recorded yet.", (40, top), 22, TEXT_DIM)
            theme.text(surface, "esc back", (WINDOW[0] // 2, WINDOW[1] - 30), 16, TEXT_DIM, centre=True)
            return

        headers = ("case", "reps", "mean", "trimmed", "s/move", "spread", "peeks", "DNFs")
        columns = (40, 150, 250, 370, 500, 620, 740, 860)
        for header, x in zip(headers, columns):
            theme.text(surface, header, (x, top), 17, TEXT_DIM, True)
        top += 28
        pygame.draw.line(surface, PANEL, (40, top), (WINDOW[0] - 40, top), 2)
        top += 10

        for report in rank_by_weakness(self.reports, signal)[:18]:
            thin = not report.has_enough_data
            colour = TEXT_DIM if thin else TEXT
            values = (
                pll.get(report.case_id).name,
                str(report.attempts),
                theme.format_time(report.mean),
                theme.format_time(report.trimmed_mean),
                f"{report.seconds_per_move:.3f}" if report.seconds_per_move else "-",
                f"{report.spread:.2f}",
                f"{report.peek_rate:.0%}",
                f"{report.dnf_rate:.0%}",
            )
            for value, x in zip(values, columns):
                theme.text(surface, value, (x, top), 19, colour)
            if thin:
                theme.text(surface, "few reps", (960, top), 15, TEXT_DIM)
            top += 28

        theme.text(surface, "tab changes the ranking signal   esc back",
                   (WINDOW[0] // 2, WINDOW[1] - 30), 16, TEXT_DIM, centre=True)


# --------------------------------------------------------------------------
class App:
    def __init__(self, store=None, seed=None):
        pygame.init()
        theme.reset_fonts()
        pygame.display.set_caption("Cube Trainer")
        self.surface = pygame.display.set_mode(WINDOW)
        self.clock = pygame.time.Clock()
        self.store = store or Store()
        self.overrides = self.store.algorithm_overrides()
        self.rng = random.Random(seed)
        self.now = 0.0
        self.running = True
        self.stack = [HomeScreen(self)]

    @property
    def screen(self):
        return self.stack[-1]

    def quit(self):
        self.running = False

    def run(self):
        while self.running:
            self.now = pygame.time.get_ticks() / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                result = self.screen.handle(event)
                if result == "back":
                    self.stack.pop()
                    if not self.stack:
                        self.running = False
                    else:
                        self.overrides = self.store.algorithm_overrides()
                elif isinstance(result, Screen):
                    self.stack.append(result)
            if not self.running:
                break
            self.screen.update(self.now)
            self.screen.draw(self.surface)
            pygame.display.flip()
            self.clock.tick(FPS)
        self.store.close()
        pygame.quit()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    store = Store(argv[0]) if argv else Store()
    App(store=store).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
