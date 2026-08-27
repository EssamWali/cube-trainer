"""Case definitions for the last layer."""

from .catalogue import Case, Catalogue
from . import f2l, oll, pll

#: Every phase the trainer can drill, in the order the screens offer them:
#: the order a cuber meets them going backwards, which is the order they
#: learn them in.
CATALOGUES = (pll.CATALOGUE, oll.CATALOGUE, f2l.CATALOGUE)

__all__ = ["CATALOGUES", "Case", "Catalogue", "f2l", "oll", "pll"]
