"""Case definitions for the last layer."""

from .catalogue import Case, Catalogue
from . import oll, pll

#: Every phase the trainer can drill, in the order the screens offer them.
CATALOGUES = (pll.CATALOGUE, oll.CATALOGUE)

__all__ = ["CATALOGUES", "Case", "Catalogue", "oll", "pll"]
