"""The pygame application: menu, case picker, drill loop, solves and statistics.

Screens are a stack. The picker and the algorithm library are the same screen
in two modes, because they show identical content and differ only in whether
choosing a case selects it or just looks at it.
"""

import random
import sys

import pygame

from ..cases import CATALOGUES
from ..cube import Cube
from ..cube.notation import NotationError, format_sequence, move_count, parse
from ..store import Store
from ..store.stats import case_report, phase_summary, rank_by_weakness, solve_summary
from ..trainer.sampler import RoundRobinSampler
from ..trainer.scramble import random_scramble, scramble_for
from ..trainer.timer import Penalty, SolveTimer, TimerState
from . import render, theme
from .theme import ACCENT, ARMED, BACKGROUND, DANGER, PANEL, READY, TEXT, TEXT_DIM

WINDOW = (1180, 780)
FPS = 60
LAST_USED = "__last used__"

MARGIN = 40
HELP_LINE = WINDOW[1] - 30


#: The phases of a solve, in the order they happen. A cuber ticks whichever of
#: these they want the timer to stop at; CONTEXT.md calls that multi-phase
#: timing, and calls timing only the cross the same thing with one boundary.
SOLVE_PHASES = ("Cross", "F2L", "OLL", "PLL")


#: Ticking nothing but the last boundary: one press, at the end. A whole solve
#: timed the way a timer times it, which is what most people want most of the
#: time, so it is what the screen starts on.
WHOLE_SOLVE = (SOLVE_PHASES[-1],)


def solve_split_labels(chosen):
    """What each press of the timer closes, given the boundaries ticked.

    A phase nobody asked for a boundary at does not disappear: it is still
    being solved, so it is folded into the next split and named there. Tick
    Cross and PLL and the second press closes "F2L+OLL+PLL", because that is
    honestly what it covers -- calling it "PLL" would file three phases of work
    under the name of one, and the statistics read these labels.

    Anything after the last boundary is dropped, because that is where the
    attempt ends.
    """
    labels, run = [], []
    for phase in SOLVE_PHASES:
        run.append(phase)
        if phase in chosen:
            labels.append("+".join(run))
            run = []
    return tuple(labels)


def algorithm_for(case, overrides):
    """A cuber's own algorithm for a case, or the shipped default."""
    return overrides.get(case.id, case.algorithm)


def _rows_for(count, columns):
    """How many rows `count` tiles take at `columns` across."""
    return -(-count // columns)


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

        def picker(catalogue, mode):
            return lambda: PickerScreen(self.app, mode=mode, catalogue=catalogue)

        # Every phase has a library; only the phases that are drilled have a
        # drill. Which those are is the catalogue's to say, not this screen's.
        self.items = [(f"Drill {c.phase}", picker(c, "select"))
                      for c in app.catalogues if c.drilled]
        self.items += [(f"{c.phase} algorithm library", picker(c, "browse"))
                       for c in app.catalogues]
        self.items.append(("Time a solve", lambda: SolveSetupScreen(self.app)))
        self.items.append(("Statistics", lambda: StatsScreen(self.app)))

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_DOWN, pygame.K_j):
            self.cursor = (self.cursor + 1) % len(self.items)
        elif event.key in (pygame.K_UP, pygame.K_k):
            self.cursor = (self.cursor - 1) % len(self.items)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return self.items[self.cursor][1]()
        elif pygame.K_1 <= event.key <= pygame.K_9:
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

    Every case of the phase is on screen at once. Scrolling a grid of case
    pictures means hunting for the one you want, so the tiles shrink to fit the
    window instead -- twenty-one of them or fifty-seven.
    """

    #: Tile widths to try, largest first.
    TILE_SIZES = (150, 132, 118, 104, 92, 82, 74, 66, 58, 50, 44)
    TILE_GAP = 8
    #: Space between one family and the next along a band. Tight on purpose:
    #: every pixel spent separating families is a pixel the pictures do not get,
    #: and the group headings already separate them.
    BLOCK_GAP = 18
    GRID_TOP = 86
    GROUP_LABEL = 22
    DETAIL_HEIGHT = 84

    def __init__(self, app, mode="select", catalogue=None):
        self.app = app
        self.mode = mode
        # No catalogue means the first phase the application offers, which is
        # what a screen opened without one has always meant.
        self.catalogue = catalogue or app.catalogues[0]
        self.groups = self.catalogue.by_group()
        self.order = list(self.catalogue.order)
        self.cursor = 0
        self.prompt = None
        self.prompt_text = ""
        self.prompt_error = None
        self.message = None
        restored = (app.store.load_case_set(LAST_USED, self.phase)
                    if mode == "select" else None)
        self.selected = set(restored or [])
        self.states = {
            c.id: Cube.solved().apply(c.setup) for c in self.order
        }
        self.tile, self.blocks = self._layout()

    def _layout(self):
        """The largest tile size at which every family still fits on screen."""
        available = self.detail_top - self.GRID_TOP - 12
        for tile in self.TILE_SIZES:
            blocks, height = self._flow(tile)
            if height <= available:
                return tile, blocks
        return self.TILE_SIZES[-1], self._flow(self.TILE_SIZES[-1])[0]

    def _flow(self, tile):
        """Place every family at this tile size, and say how tall it comes to.

        Families are packed along a band and wrapped to the next, the way words
        are. A family of two cases does not deserve a whole band of the window,
        and at fifteen families there is not room to give it one anyway.
        """
        step_x = tile + self.TILE_GAP
        step_y = tile + render.LABEL_STRIP + self.TILE_GAP
        right = WINDOW[0] - MARGIN
        columns = max(1, (WINDOW[0] - 2 * MARGIN + self.TILE_GAP) // step_x)
        x, y, band = MARGIN, self.GRID_TOP, 0
        blocks = []
        for group in self.catalogue.group_order:
            cases = self.groups[group]
            across = min(len(cases), columns)
            width = across * step_x - self.TILE_GAP
            if x > MARGIN and x + width > right:
                x, y, band = MARGIN, y + band + self.BLOCK_GAP, 0
            placed = [
                (case, pygame.Rect(x + column * step_x,
                                   y + self.GROUP_LABEL + row * step_y,
                                   tile, tile + render.LABEL_STRIP))
                for index, case in enumerate(cases)
                for row, column in [divmod(index, across)]
            ]
            blocks.append((group, (x, y), placed))
            rows = _rows_for(len(cases), across)
            band = max(band, self.GROUP_LABEL + rows * step_y - self.TILE_GAP)
            x += width + self.BLOCK_GAP
        return blocks, y + band - self.GRID_TOP

    def tiles(self):
        """Every case with the rectangle it is drawn in."""
        for _, _, placed in self.blocks:
            yield from placed

    def rect_for(self, case):
        for other, rect in self.tiles():
            if other is case:
                return rect
        raise KeyError(case.id)

    @property
    def detail_top(self):
        """The detail panel is pinned above the help line rather than floating
        below the grid, so it cannot be pushed off the bottom by a long phase."""
        return HELP_LINE - 18 - self.DETAIL_HEIGHT

    @property
    def phase(self):
        return self.catalogue.phase

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
            self._step_vertically(1)
        elif key in (pygame.K_UP, pygame.K_k):
            self._step_vertically(-1)
        elif self.mode == "select":
            return self._handle_selection(key)
        else:
            return self._handle_browse(key)
        return None

    def _handle_browse(self, key):
        """The library is where a cuber's own algorithm belongs.

        It is already the screen that shows the algorithm, so it is the screen
        that changes it. Nothing here touches the scramble: that is the inverse
        of the case's setup and stays so, or the promise that a scramble lands
        on the case it names stops being checkable.
        """
        if key == pygame.K_e:
            self.prompt = "algorithm"
            self.prompt_text = algorithm_for(self.current, self.app.overrides)
            self.prompt_error = None
        elif key == pygame.K_r:
            case = self.current
            if case.id in self.app.overrides:
                self.app.store.clear_algorithm(case.id)
                self._reread_overrides()
                self.message = f"{case.name}: back to the shipped algorithm"
            else:
                self.message = f"{case.name} is already the shipped algorithm"
        return None

    def _reread_overrides(self):
        """The application re-reads these when a screen is popped, which is too
        late to see your own algorithm in the panel you just typed it into."""
        self.app.overrides = self.app.store.algorithm_overrides()

    def _keep_algorithm(self):
        """Store what was typed, if it actually solves the case.

        Returns whether it was kept. A refusal leaves the prompt open with the
        text in it, because something nearly right is worth correcting rather
        than retyping.
        """
        case, typed = self.current, self.prompt_text.strip()
        if not typed:
            self.prompt_error = "type an algorithm, or esc to leave it alone"
            return False
        try:
            outcome = case.outcome_of(typed)
        except NotationError as unknown:
            self.prompt_error = str(unknown)
            return False
        if outcome == "unsolved":
            self.prompt_error = f"that does not solve {case.name}"
            return False
        if outcome == "rotated":
            self.prompt_error = "that solves it but leaves the cube turned round"
            return False
        self.app.store.set_algorithm(case.id, format_sequence(parse(typed)))
        self._reread_overrides()
        self.message = f"{case.name}: your algorithm"
        return True

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
            names = self.app.store.case_set_names(self.phase)
            names = [n for n in names if n != LAST_USED]
            if names:
                self.prompt, self.prompt_text = "load", ""
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if not self.selected:
                self.message = "select at least one case"
                return None
            chosen = [c.id for c in self.order if c.id in self.selected]
            self.app.store.save_case_set(LAST_USED, self.phase, chosen)
            return DrillScreen(self.app, chosen, self.catalogue)
        return None

    def _handle_prompt(self, event):
        if event.key == pygame.K_ESCAPE:
            self.prompt = None
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.prompt == "algorithm":
                if not self._keep_algorithm():
                    return None
            elif self.prompt == "save" and self.prompt_text.strip():
                chosen = [c.id for c in self.order if c.id in self.selected]
                self.app.store.save_case_set(
                    self.prompt_text.strip(), self.phase, chosen)
                self.message = f"saved as {self.prompt_text.strip()!r}"
            self.prompt = None
        elif event.key == pygame.K_BACKSPACE:
            self.prompt_text = self.prompt_text[:-1]
            self.prompt_error = None
        elif self.prompt == "load" and event.unicode.isdigit():
            names = [n for n in self.app.store.case_set_names(self.phase)
                     if n != LAST_USED]
            index = int(event.unicode) - 1
            if 0 <= index < len(names):
                loaded = self.app.store.load_case_set(names[index], self.phase)
                self.selected = set(loaded or [])
                self.message = f"loaded {names[index]!r}"
                self.prompt = None
        elif self.prompt in ("save", "algorithm") and event.unicode.isprintable():
            self.prompt_text += event.unicode
            self.prompt_error = None
        return None

    def draw(self, surface):
        surface.fill(BACKGROUND)
        title = (f"Choose {self.phase} cases to drill" if self.mode == "select"
                 else f"{self.phase} algorithm library")
        theme.text(surface, title, (40, 28), 30, TEXT, True)
        if self.mode == "select":
            theme.text(surface, f"{len(self.selected)} of {len(self.order)} selected",
                       (WINDOW[0] - 40, 36), 20, ACCENT, right=True)

        for group, (left, top), placed in self.blocks:
            theme.text(surface, group.upper(), (left, top), 15, TEXT_DIM, True)
            for case, rect in placed:
                position = self.order.index(case)
                chosen = self.mode == "select" and case.id in self.selected
                render.draw_thumbnail(
                    surface, self.states[case.id], rect, self.label_for(case),
                    cursor=(position == self.cursor),
                    chosen=chosen,
                    dim=(self.mode == "select" and not chosen),
                )

        self._draw_detail(surface, self.detail_top)
        self._draw_help(surface)
        if self.prompt is not None:
            self._draw_prompt(surface)

    def _step_vertically(self, direction):
        """Move to the nearest case above or below the cursor.

        The grid is not one rectangle -- families sit side by side and wrap --
        so up and down are answered from where the tiles actually are rather
        than by counting a fixed number of columns.
        """
        here = self.rect_for(self.current)
        best = None
        for case, rect in self.tiles():
            offset = rect.centery - here.centery
            if offset * direction <= 0:
                continue
            score = (abs(offset), abs(rect.centerx - here.centerx))
            if best is None or score < best[0]:
                best = (score, case)
        if best is not None:
            self.cursor = self.order.index(best[1])

    def label_for(self, case):
        """What goes under a thumbnail.

        The id already names the phase, and the phase is in the title, so
        repeating it under every one of fifty-seven tiles only costs room the
        picture needs.
        """
        prefix = self.phase + " "
        return case.id[len(prefix):] if case.id.startswith(prefix) else case.id

    def _draw_detail(self, surface, top):
        case = self.current
        panel = pygame.Rect(MARGIN, top, WINDOW[0] - 2 * MARGIN, self.DETAIL_HEIGHT)
        pygame.draw.rect(surface, PANEL, panel, border_radius=8)
        theme.text(surface, case.name, (panel.left + 16, panel.top + 12), 24, TEXT, True)
        theme.text(surface, case.description, (panel.left + 16, panel.top + 44), 17, TEXT_DIM)
        algorithm = algorithm_for(case, self.app.overrides)
        theme.text(surface, algorithm, (panel.right - 16, panel.top + 14), 20, ACCENT, right=True)
        moves = f"{move_count(algorithm)} moves"
        if case.id in self.app.overrides:
            moves = "yours   " + moves
        theme.text(surface, moves, (panel.right - 16, panel.top + 46), 16,
                   TEXT_DIM, right=True)

    def _draw_help(self, surface):
        if self.mode == "select":
            hint = ("arrows move   space toggles   g whole group   a all   n none   "
                    "s save set   o open set   enter start   esc back")
        else:
            hint = "arrows move   e your algorithm   r shipped one   esc back"
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
        if self.prompt == "algorithm":
            case = self.current
            theme.text(surface, f"Your algorithm for {case.name}",
                       (box.centerx, box.top + 22), 24, TEXT, True, centre=True)
            theme.text(surface, self.prompt_text + "_", (box.centerx, box.top + 74),
                       22, ACCENT, centre=True)
            if self.prompt_error:
                theme.text(surface, self.prompt_error, (box.centerx, box.top + 118),
                           17, DANGER, centre=True)
            else:
                theme.text(surface, "it has to solve the case and give the cube back"
                           " as you picked it up", (box.centerx, box.top + 118), 16,
                           TEXT_DIM, centre=True)
            theme.text(surface, "enter to keep, esc to cancel",
                       (box.centerx, box.bottom - 34), 16, TEXT_DIM, centre=True)
        elif self.prompt == "save":
            theme.text(surface, "Name this case set", (box.centerx, box.top + 26), 24, TEXT, True, centre=True)
            theme.text(surface, self.prompt_text + "_", (box.centerx, box.top + 80), 26, ACCENT, centre=True)
            theme.text(surface, "enter to save, esc to cancel", (box.centerx, box.bottom - 40), 16, TEXT_DIM, centre=True)
        else:
            names = [n for n in self.app.store.case_set_names(self.phase)
                     if n != LAST_USED]
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

    def __init__(self, app, case_ids, catalogue=None):
        self.app = app
        self.catalogue = catalogue or app.catalogues[0]
        self.case_ids = list(case_ids)
        self.sampler = RoundRobinSampler(self.case_ids, app.rng)
        self.session = app.store.start_session("drill", self.catalogue.phase)
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
        self.case = self.catalogue.get(self.sampler.next())
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
            if self.stage == "scramble":
                if self.timer.state is TimerState.RUNNING:
                    self.timer.press(self.app.now)
                self._record(penalty="dnf")
                self.stage = "reset"
            elif self.stage == "result":
                # The rep is already in the store. Discarding it means that
                # attempt was not one, not that there was a second attempt that
                # was not one.
                self._penalise("dnf")
                self.stage = "reset"
            return None
        if key == pygame.K_2 and self.stage == "result" and self.last_time is not None:
            self._penalise("plus_two")
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

    def _penalise(self, penalty):
        """Amend the rep just recorded, rather than adding another one.

        A peeked rep is never in `times` -- a time achieved while reading the
        answer is not a time -- so neither penalty may reach in there for one,
        or it corrects a figure belonging to some earlier rep.
        """
        rows = self.app.store.reps(session_id=self.session)
        if not rows or rows[-1]["penalty"] == "dnf":
            return
        last = rows[-1]
        counted = self.last_time is not None and not self.peeked
        self.app.store.penalise_rep(last["id"], penalty)
        if penalty == "dnf":
            if counted and self.times:
                self.times.pop()
            self.last_time = None
            self.dnfs += 1
        elif last["duration_ms"] is not None:
            self.last_time = (last["duration_ms"] + 2000) / 1000.0
            if counted and self.times:
                self.times[-1] = self.last_time

    def update(self, now):
        if self.stage == "scramble":
            self.timer.tick(now)

    def draw(self, surface):
        surface.fill(BACKGROUND)
        running = self.timer.state is TimerState.RUNNING
        theme.text(surface, f"{self.catalogue.phase} drill   {len(self.case_ids)} cases",
                   (40, 28), 20, TEXT_DIM)
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
class SolveSetupScreen(Screen):
    """Which boundaries a run of solves will tick, and whether to inspect.

    A cuber timing a whole solve and a cuber timing only their cross are doing
    the same thing with a different number of boundaries, so they get the same
    screen and the same timer rather than two that drift apart.
    """

    def __init__(self, app, phases=None, inspection=True):
        self.app = app
        self.chosen = set(WHOLE_SOLVE if phases is None else phases)
        self.inspection = inspection
        self.cursor = 0

    @property
    def ticked(self):
        """The boundaries in the order they happen, whatever order they were
        ticked in."""
        return tuple(phase for phase in SOLVE_PHASES if phase in self.chosen)

    @property
    def labels(self):
        return solve_split_labels(self.chosen)

    @property
    def in_one_go(self):
        """Whether this is a whole solve with nothing to press at on the way."""
        return len(self.labels) == 1 and SOLVE_PHASES[-1] in self.chosen

    @property
    def summary(self):
        """What the run will actually ask of the cuber, in plain words.

        The ticks say what will be timed; this says what your hands will do,
        which is the thing you want to know before you pick up the cube.
        """
        if not self.ticked:
            return "tick at least one boundary to start"
        if self.in_one_go:
            return "one press at the end: the whole solve, timed in one go"
        presses = len(self.labels)
        if SOLVE_PHASES[-1] in self.chosen:
            return f"{presses} presses: a whole solve, split {presses} ways"
        return (f"{presses} press{'es' if presses > 1 else ''}: stops after "
                f"{self.ticked[-1]}, so your cube is left part solved")

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        key = event.key
        if key == pygame.K_ESCAPE:
            return "back"
        if key in (pygame.K_DOWN, pygame.K_j):
            self.cursor = (self.cursor + 1) % len(SOLVE_PHASES)
        elif key in (pygame.K_UP, pygame.K_k):
            self.cursor = (self.cursor - 1) % len(SOLVE_PHASES)
        elif key == pygame.K_SPACE:
            self.chosen.symmetric_difference_update({SOLVE_PHASES[self.cursor]})
        elif key == pygame.K_a:
            self.chosen = set(SOLVE_PHASES)
        elif key == pygame.K_n:
            # Not "nothing ticked" -- a run with no boundary would never stop.
            # No boundary on the way, which is the plain timer.
            self.chosen = set(WHOLE_SOLVE)
        elif key == pygame.K_i:
            self.inspection = not self.inspection
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            # A run with no boundary would never stop, so there is nothing to
            # start. Same rule as a drill with no cases.
            if self.ticked:
                return SolveScreen(self.app, self.ticked, self.inspection)
        return None

    def draw(self, surface):
        surface.fill(BACKGROUND)
        theme.text(surface, "Time a solve", (MARGIN, 28), 30, TEXT, True)
        theme.text(surface, "tick the boundaries you want to press at, or "
                   "leave it as it is to time the whole solve in one go",
                   (MARGIN, 74), 19, TEXT_DIM)

        labels = list(self.labels)
        top = 130
        for index, phase in enumerate(SOLVE_PHASES):
            here = index == self.cursor
            on = phase in self.chosen
            colour = ACCENT if here else (TEXT if on else TEXT_DIM)
            mark = "x" if on else " "
            theme.text(surface, f"{'>' if here else ' '} [{mark}] {phase}",
                       (MARGIN + 20, top), 26, colour, here)
            if on and labels:
                closes = labels.pop(0)
                said = ("the whole solve, in one press" if self.in_one_go else
                        f"press {len(SOLVE_PHASES) - len(labels)} closes {closes}")
                theme.text(surface, said, (MARGIN + 260, top + 4), 18, TEXT_DIM)
            top += 44

        top += 20
        state = "on" if self.inspection else "off"
        theme.text(surface, f"inspection: {state}   (i)", (MARGIN + 20, top), 22,
                   TEXT if self.inspection else TEXT_DIM)
        top += 40
        theme.text(surface, self.summary, (MARGIN + 20, top), 19,
                   TEXT_DIM if self.ticked else DANGER)

        theme.text(surface, "space ticks   a every phase   n none on the way"
                   "   i inspection   enter starts   esc back",
                   (WINDOW[0] // 2, HELP_LINE), 16, TEXT_DIM, centre=True)


# --------------------------------------------------------------------------
class SolveScreen(Screen):
    """A run of solves, split at whichever boundaries were chosen.

    A solve has no case. Which OLL and which PLL come up depends on how the
    cuber chose to build their F2L, which this application never sees, so
    nothing here claims to know what was solved -- only how long each stretch
    of it took.
    """

    def __init__(self, app, phases=SOLVE_PHASES, inspection=True):
        self.app = app
        self.phases = tuple(phases)
        self.labels = solve_split_labels(self.phases)
        self.whole = SOLVE_PHASES[-1] in self.phases
        # A whole solve is a solve of the cube and its session says so by
        # naming no phase. One that stops early is a phase being drilled, and
        # the statistics need to be able to tell them apart before averaging.
        self.session = app.store.start_session(
            "solve", None if self.whole else self.phases[-1])
        # A single split covering the whole solve is the solve's own time
        # written down a second time, and it would put a phase in the phase
        # means whose mean is just the solve mean.
        self.in_one_go = self.whole and len(self.labels) == 1
        self.inspection = inspection
        self.timer = SolveTimer(phases=self.labels, inspection=inspection)
        self.scramble = ""
        self.stage = "scramble"
        self.last_time = None
        self.last_splits = ()
        self.times = []
        self.dnfs = 0
        self._next_scramble()

    def _next_scramble(self):
        self.scramble = random_scramble(self.app.rng)
        self.timer.reset()
        self.stage = "scramble"

    def _record(self, penalty=None):
        penalty = penalty or self.timer.penalty.value
        seconds = self.timer.total()
        # A fumbled attempt has splits for the phases it got through, and they
        # are not times: the attempt they belong to did not happen.
        splits = (() if penalty == "dnf" or self.in_one_go
                  else tuple(zip(self.labels, self.timer.splits())))
        self.app.store.record_solve(self.session, self.scramble, seconds,
                                    splits, penalty=penalty)
        self.last_splits = splits
        if penalty == "dnf":
            self.last_time = None
            self.dnfs += 1
        else:
            self.last_time = seconds
            self.times.append(seconds)

    def _penalise(self, penalty):
        """Amend the attempt just recorded, rather than adding another one.

        The cuber has stopped the timer and is looking at the time. Saying it
        was a +2, or was not a solve at all, is a fact about that attempt.
        """
        rows = self.app.store.solves(session_id=self.session)
        if not rows or rows[-1]["penalty"] == "dnf":
            return
        last = rows[-1]
        self.app.store.penalise_solve(last["id"], penalty)
        if penalty == "dnf":
            if self.last_time is not None and self.times:
                self.times.pop()
            self.last_time = None
            self.last_splits = ()
            self.dnfs += 1
        elif last["duration_ms"] is not None:
            self.last_time = (last["duration_ms"] + 2000) / 1000.0
            if self.times:
                self.times[-1] = self.last_time

    def handle(self, event):
        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            if self.stage == "scramble":
                # Read the penalty before the release, because releasing is
                # what ends inspection and the clock it is measured against.
                overrun = self.timer.inspection_penalty(self.app.now)
                self.timer.release(self.app.now)
                if self.timer.state is TimerState.RUNNING:
                    self.timer.penalty = overrun
            return None
        if event.type != pygame.KEYDOWN:
            return None
        return self._key_down(event)

    def _key_down(self, event):
        key = event.key
        if key == pygame.K_ESCAPE:
            self.app.store.end_session(self.session)
            return "back"
        if key == pygame.K_i and self.stage == "scramble":
            self.timer.begin_inspection(self.app.now)
            return None
        if key == pygame.K_d:
            if self.stage == "scramble":
                # Abandoned part way: there is nothing recorded yet to amend.
                self._record(penalty="dnf")
            else:
                self._penalise("dnf")
            self.stage = "reset"
            return None
        if key == pygame.K_2 and self.last_time is not None and \
                self.stage in ("result", "reset"):
            # "reset" is where a run that stops before the cube is solved ends
            # up, and a cross time can be a +2 like any other.
            self._penalise("plus_two")
            return None
        if key == pygame.K_SPACE:
            if self.stage in ("result", "reset"):
                self._next_scramble()
            else:
                self.timer.press(self.app.now)
                if self.timer.is_finished:
                    self._record()
                    # A whole solve ends on a solved cube and the next scramble
                    # can go straight on. A run that stopped early did not, so
                    # the cuber has to finish it first -- every scramble here
                    # assumes a solved cube.
                    self.stage = "result" if self.whole else "reset"
            return None
        return None

    def update(self, now):
        if self.stage == "scramble":
            self.timer.tick(now)

    def draw(self, surface):
        surface.fill(BACKGROUND)
        running = self.timer.state is TimerState.RUNNING
        heading = "solve" if self.whole else f"{self.phases[-1]} drill"
        if not self.in_one_go:
            heading += "   " + "  ".join(self.labels)
        theme.text(surface, heading, (MARGIN, 28), 20, TEXT_DIM)
        self._draw_session_line(surface)

        if not running:
            theme.text(surface, self.scramble, (WINDOW[0] // 2, 104), 24, TEXT,
                       True, centre=True)
            theme.text(surface, "apply this to a solved cube",
                       (WINDOW[0] // 2, 142), 17, TEXT_DIM, centre=True)

        self._draw_timer(surface)
        self._draw_splits(surface)
        self._draw_help(surface)

    def _draw_session_line(self, surface):
        done = len(self.times) + self.dnfs
        noun = "solve" if self.whole else "attempt"
        summary = f"{done} {noun}" + ("" if done == 1 else "s")
        if self.times:
            summary += f"   best {theme.format_time(min(self.times))}"
            summary += f"   mean {theme.format_time(sum(self.times) / len(self.times))}"
        if self.dnfs:
            summary += f"   {self.dnfs} DNF"
        theme.text(surface, summary, (WINDOW[0] - MARGIN, 30), 19, TEXT_DIM,
                   right=True)

    def _draw_timer(self, surface):
        state = self.timer.state
        colour, label = TEXT, None
        if self.stage == "reset":
            colour = DANGER if self.last_time is None else TEXT
            reading = theme.format_time(self.last_time)
            label = "solve your cube, then press space"
        elif self.stage == "result":
            reading = theme.format_time(self.last_time)
            colour = DANGER if self.last_time is None else READY
            label = "space for the next scramble"
        elif state is TimerState.INSPECTING:
            used = self.timer.inspection_elapsed(self.app.now)
            left = self.timer.inspection_seconds - used
            over = self.timer.inspection_penalty(self.app.now)
            colour = TEXT if over is Penalty.NONE else DANGER
            reading = f"{max(0.0, left):.0f}"
            label = ("inspecting" if over is Penalty.NONE
                     else f"inspection {over.value.replace('_', ' ')}")
        elif state is TimerState.ARMING:
            colour, reading, label = ARMED, "0.00", "keep holding"
        elif state is TimerState.READY:
            colour, reading, label = READY, "0.00", "release to start"
        elif state is TimerState.RUNNING:
            colour = TEXT
            reading = theme.format_time(self.timer.elapsed(self.app.now))
            done = len(self.timer.splits())
            label = ("press when your cube is solved" if self.in_one_go
                     else f"next press closes {self.labels[done]}")
        else:
            colour, reading = TEXT_DIM, "0.00"
            label = ("i to inspect, or hold space to arm" if self.inspection
                     else "hold space to arm")
        theme.text(surface, reading, (WINDOW[0] // 2, 200), 96, colour, True,
                   centre=True)
        if label:
            theme.text(surface, label, (WINDOW[0] // 2, 310), 20, colour,
                       centre=True)

    def _draw_splits(self, surface):
        """The splits of the attempt on screen, or the one just finished."""
        if self.timer.state is TimerState.RUNNING:
            shown = list(zip(self.labels, self.timer.splits()))
        elif self.stage in ("result", "reset"):
            shown = list(self.last_splits)
        else:
            return
        top = 380
        for label, seconds in shown:
            theme.text(surface, label, (WINDOW[0] // 2 - 150, top), 22, TEXT_DIM)
            theme.text(surface, theme.format_time(seconds),
                       (WINDOW[0] // 2 + 150, top), 22, TEXT, right=True)
            top += 32

    def _draw_help(self, surface):
        if self.stage == "reset":
            hint = ("space when your cube is solved again   2 penalty"
                    "   d discard as DNF   esc end session")
        elif self.stage == "result":
            hint = "space next scramble   2 penalty   d discard as DNF   esc end session"
        elif self.timer.state is TimerState.RUNNING:
            hint = ("space stops   d fumbled   esc end session" if self.in_one_go
                    else "space closes each phase   d fumbled   esc end session")
        elif self.inspection:
            hint = "i inspect   hold space to start   d fumbled   esc end session"
        else:
            hint = "hold space to start   d fumbled   esc end session"
        theme.text(surface, hint, (WINDOW[0] // 2, HELP_LINE), 16, TEXT_DIM,
                   centre=True)


# --------------------------------------------------------------------------
class StatsScreen(Screen):
    """Weak spots as several signals, never as one score.

    A case can be slow, erratic, still being looked up, or dropped often, and
    those call for different practice. A combined score would hide which.

    One phase at a time, too. Ranking an OLL case against a PLL case puts two
    incomparable things in one list: the numbers are the same numbers, but "my
    worst case" then means whichever phase happens to be slower overall.
    """

    SIGNALS = (
        ("seconds_per_move", "s/move"),
        ("mean", "mean"),
        ("spread", "spread"),
        ("peek_rate", "peeks"),
        ("dnf_rate", "DNFs"),
    )

    def __init__(self, app, catalogues=None):
        self.app = app
        # Only the phases that are drilled: a ranking of a phase that cannot
        # be drilled is a page that is empty for a reason nobody can see.
        self.catalogues = tuple(
            catalogues or [c for c in app.catalogues if c.drilled])
        self.phase_index = 0
        self.signal = 0
        self.reports = self._build()

    @property
    def catalogue(self):
        return self.catalogues[self.phase_index]

    def _build(self):
        phase = self.catalogue.phase
        reports = []
        for case_id in self.app.store.practised_case_ids(phase):
            try:
                case = self.catalogue.get(case_id)
            except KeyError:
                # History outlives the case list. An id nobody recognises any
                # more is a row we cannot name, not a reason to lose the rest.
                continue
            rows = self.app.store.reps(case_id=case_id, phase=phase)
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
        elif event.key in (pygame.K_RIGHT, pygame.K_l):
            self._show_phase(self.phase_index + 1)
        elif event.key in (pygame.K_LEFT, pygame.K_h):
            self._show_phase(self.phase_index - 1)
        return None

    def _show_phase(self, index):
        self.phase_index = index % len(self.catalogues)
        self.reports = self._build()

    def draw(self, surface):
        surface.fill(BACKGROUND)
        theme.text(surface, f"{self.catalogue.phase} statistics", (40, 28), 30, TEXT, True)
        signal, label = self.SIGNALS[self.signal]
        theme.text(surface, f"sorted by {label}  (tab to change)",
                   (WINDOW[0] - 40, 36), 19, ACCENT, right=True)

        solves = self.app.store.solves(whole_only=True)
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
            theme.text(surface, f"No {self.catalogue.phase} reps recorded yet.",
                       (40, top), 22, TEXT_DIM)
            self._draw_help(surface)
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
                self.catalogue.get(report.case_id).name,
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

        self._draw_help(surface)

    def _draw_help(self, surface):
        phases = "   ".join(
            (f"[{c.phase}]" if c is self.catalogue else c.phase)
            for c in self.catalogues
        )
        theme.text(surface, f"arrows change phase: {phases}",
                   (WINDOW[0] // 2, HELP_LINE - 24), 16, TEXT_DIM, centre=True)
        theme.text(surface, "tab changes the ranking signal   esc back",
                   (WINDOW[0] // 2, HELP_LINE), 16, TEXT_DIM, centre=True)


# --------------------------------------------------------------------------
class App:
    def __init__(self, store=None, seed=None):
        pygame.init()
        theme.reset_fonts()
        pygame.display.set_caption("Cube Trainer")
        self.surface = pygame.display.set_mode(WINDOW)
        self.clock = pygame.time.Clock()
        self.store = store or Store()
        self.catalogues = CATALOGUES
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
