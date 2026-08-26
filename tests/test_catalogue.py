"""The case catalogue.

A catalogue is what a screen is given instead of a case module: the phase's
name, the order its groups are shown in, and how to find a case by id. It
exists so that adding a phase is data rather than a change to every screen.
"""

import pytest

from cubetrainer.cases import CATALOGUES, Case, Catalogue


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
