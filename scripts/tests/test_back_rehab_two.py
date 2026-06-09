"""Tests for the Back Rehab 2 plan generator."""

from common.io import load_exercise_mappings
from programs.back_rehab_two import EXERCISES, PLAN_NAME, build_plan

MAPPINGS = load_exercise_mappings()


def _exercises():
    workout = build_plan(MAPPINGS)
    blocks = workout["Data"][0]["Workouts"]
    # One SuperSet per block, one exercise per superset; flatten in order.
    return workout, [ex for block in blocks for ss in block["SuperSets"] for ex in ss["Exercises"]]


def test_plan_name():
    workout, _ = _exercises()
    assert workout["Data"][0]["Name"] == PLAN_NAME


def test_one_block_per_exercise():
    # A circuit: each exercise is its own block, one SuperSet each.
    workout = build_plan(MAPPINGS)
    blocks = workout["Data"][0]["Workouts"]
    assert len(blocks) == len(EXERCISES)
    assert all(len(block["SuperSets"]) == 1 for block in blocks)
    assert all(len(block["SuperSets"][0]["Exercises"]) == 1 for block in blocks)


def test_single_exercise_blocks_have_no_name():
    # Single-exercise blocks carry no Name key (matches a known-good export).
    workout = build_plan(MAPPINGS)
    for block in workout["Data"][0]["Workouts"]:
        assert "Name" not in block["SuperSets"][0]


def test_exercise_order():
    _, exercises = _exercises()
    names = [ex["Definition"]["Name"] for ex in exercises]
    assert names == [name for name, _, _ in EXERCISES]


def test_every_exercise_is_time_focused():
    # Whole routine is timed holds: Primary measure is time, no weight.
    _, exercises = _exercises()
    for ex in exercises:
        assert ex["Definition"]["PrimaryFocusId"] == 3
        assert ex["Definition"]["SecondaryFocusId"] == 0


def test_set_counts_match_sides():
    # Per-side moves are two sets (L/R); whole-body holds are one.
    _, exercises = _exercises()
    counts = {ex["Definition"]["Name"]: len(ex["SetDetails"]) for ex in exercises}
    assert counts == {name: sets for name, _, sets in EXERCISES}


def test_durations_in_seconds():
    # Primary holds the per-set duration in seconds.
    _, exercises = _exercises()
    for ex, (_, seconds, _) in zip(exercises, EXERCISES, strict=True):
        assert all(sd["Primary"] == seconds for sd in ex["SetDetails"])
        assert all(sd["Secondary"] == 0 for sd in ex["SetDetails"])
