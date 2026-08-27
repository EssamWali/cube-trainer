"""The case catalogue.

A catalogue is what a screen is given instead of a case module: the phase's
name, the order its groups are shown in, and how to find a case by id. It
exists so that adding a phase is data rather than a change to every screen.
"""

import pytest

from cubetrainer.cases import CATALOGUES, Case, Catalogue, pll
from cubetrainer.cube.notation import NotationError


def _case(case_id, group="Group A"):
    return Case(case_id, f"{case_id} case", group, "R U R'", "a description", case_id)


ONE = _case("one")
TWO = _case("two")
THREE = _case("three", group="Group B")
SAMPLE = Catalogue("SAMPLE", (ONE, TWO, THREE), ("Group B", "Group A"))


def test_a_catalogue_knows_its_phase():
    assert SAMPLE.phase == "SAMPLE"


def test_a_catalogue_looks_a_case_up_by_id():
    assert SAMPLE.get("two") is TWO


def test_looking_up_an_unknown_id_names_the_phase():
    """The message has to say which phase was asked, or a stale id in old
    history sends you looking in the wrong case list."""
    with pytest.raises(KeyError, match="SAMPLE"):
        SAMPLE.get("nope")


def test_cases_are_grouped_in_the_order_the_picker_shows_them():
    grouped = SAMPLE.by_group()
    assert list(grouped) == ["Group B", "Group A"]
    assert grouped["Group B"] == (THREE,)
    assert grouped["Group A"] == (ONE, TWO)


def test_the_picker_order_follows_the_groups():
    """The grid reads group by group, so the flat order has to as well."""
    assert [c.id for c in SAMPLE.order] == ["three", "one", "two"]


def test_a_catalogue_is_a_sequence_of_its_cases():
    assert len(SAMPLE) == 3
    assert list(SAMPLE) == [ONE, TWO, THREE]


def test_every_shipped_catalogue_has_a_distinct_phase():
    phases = [c.phase for c in CATALOGUES]
    assert len(set(phases)) == len(phases)


def test_case_ids_are_unique_across_every_phase():
    """History records a case id and nothing else, so an id that means one
    thing in one phase and something else in another is a lie waiting to be
    read back."""
    ids = [case.id for catalogue in CATALOGUES for case in catalogue]
    assert len(set(ids)) == len(ids)


# --- what a sequence does to a case -----------------------------------------

def test_a_case_knows_its_own_algorithm_solves_it():
    for catalogue in CATALOGUES:
        for case in catalogue:
            assert case.outcome_of(case.algorithm) == "solved", case.id


def test_another_algorithm_for_the_same_case_solves_it_too():
    """The M-slice Ua, which is nothing like the shipped R-move one and is the
    same algorithm as far as the cube is concerned."""
    assert pll.get("Ua").outcome_of("M2 U M U2 M' U M2") == "solved"
    assert pll.get("H").outcome_of("M2 U' M2 U2 M2 U' M2") == "solved"


def test_an_algorithm_for_the_wrong_case_does_not_solve_this_one():
    assert pll.get("Ub").outcome_of("M2 U M U2 M' U M2") == "unsolved"
    assert pll.get("T").outcome_of("R U R'") == "unsolved"


def test_solving_the_case_but_leaving_the_cube_turned_round_is_its_own_answer():
    """The mistake worth naming separately. Judged face by face against its own
    centres the cube is solved, which is the right answer to "is this cube
    solved" and the wrong bar for an algorithm: one ending on a regrip it never
    takes back solves a different case depending on how you were holding it."""
    case = pll.get("T")
    assert case.outcome_of(case.algorithm + " y") == "rotated"
    # What is refused is the regrip nobody takes back. The shipped V perm turns
    # the cube in the middle of itself and turns it back, and is fine.
    assert pll.get("V").outcome_of(pll.get("V").algorithm) == "solved"
    assert "y" in pll.get("V").algorithm, "the V perm stopped being the example"


def test_a_sequence_the_cube_does_not_understand_is_refused():
    with pytest.raises(NotationError):
        pll.get("T").outcome_of("R U Q")
