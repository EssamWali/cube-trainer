"""Regenerate the pictures used in the README.

The images come from the application's own drawing code, rendered offscreen with
SDL's dummy video driver, so a change to how a case is drawn shows up in the
README the next time this is run rather than drifting away from it.

    python tools/make_docs_images.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cubetrainer.cases import f2l, oll, pll  # noqa: E402
from cubetrainer.cube.state import Cube  # noqa: E402
from cubetrainer.ui import render, theme  # noqa: E402

OUT = ROOT / "docs" / "images"


def cube_for(case):
    return Cube.solved().apply(case.setup)


def gallery(cases, columns, cell, path, chosen=(), cursor=None):
    """A grid of thumbnails, drawn the way the case picker draws it."""
    rows = (len(cases) + columns - 1) // columns
    pad = 14
    width = columns * cell + pad * (columns + 1)
    height = rows * cell + pad * (rows + 1)

    surface = pygame.Surface((width, height))
    surface.fill(theme.BACKGROUND)

    for index, case in enumerate(cases):
        row, column = divmod(index, columns)
        rect = pygame.Rect(
            pad + column * (cell + pad),
            pad + row * (cell + pad),
            cell,
            cell,
        )
        render.draw_thumbnail(
            surface,
            cube_for(case),
            rect,
            case.name,
            cursor=(case.id == cursor),
            chosen=(case.id in chosen),
        )

    pygame.image.save(surface, str(path))
    print(f"wrote {path.relative_to(ROOT)}  ({width}x{height})")


def single(case, size, path, arrows=True, hidden=False):
    """One large case diagram, the way the drill screen draws it."""
    surface = pygame.Surface((size, size))
    surface.fill(theme.BACKGROUND)
    inset = size // 12
    rect = pygame.Rect(inset, inset, size - inset * 2, size - inset * 2)
    render.draw_case(surface, cube_for(case), rect, arrows=arrows, hidden=hidden)
    pygame.image.save(surface, str(path))
    print(f"wrote {path.relative_to(ROOT)}  ({size}x{size})")


def main():
    pygame.init()
    pygame.font.init()
    OUT.mkdir(parents=True, exist_ok=True)

    pll_cases = [pll.get(i) for i in ("Ua", "H", "Z", "T", "Y", "Ra", "Ga", "Na")]
    gallery(pll_cases, 4, 150, OUT / "pll-picker.png", chosen={"T", "Y", "H"}, cursor="Z")

    first_oll = list(oll.CATALOGUE)[0]

    single(pll.get("T"), 420, OUT / "case-t-perm.png")
    single(pll.get("T"), 420, OUT / "case-t-perm-hidden.png", hidden=True)
    single(first_oll, 420, OUT / "case-oll.png")
    single(list(f2l.CATALOGUE)[0], 420, OUT / "case-f2l.png")

    pygame.quit()


if __name__ == "__main__":
    main()
