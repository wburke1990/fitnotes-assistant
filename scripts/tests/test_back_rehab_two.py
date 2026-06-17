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


def test_every_move_is_one_set():
    # Each move is a single set: per-side moves fold L/R into one set of 2 reps
    # so they count as one group-set, not two; whole-body holds are one hold.
    _, exercises = _exercises()
    assert all(len(ex["SetDetails"]) == 1 for ex in exercises)


def test_per_side_and_whole_body_encoding():
    # Per-side: reps focus (Primary=2 sides) + time secondary (seconds held).
    # Whole-body: time focus (Primary=seconds), no secondary.
    _, exercises = _exercises()
    by_name = {ex["Definition"]["Name"]: ex for ex in exercises}
    for name, seconds, per_side in EXERCISES:
        ex = by_name[name]
        sd = ex["SetDetails"][0]
        if per_side:
            assert ex["Definition"]["PrimaryFocusId"] == 1
            assert ex["Definition"]["SecondaryFocusId"] == 3
            assert sd["Primary"] == 2
            assert sd["Secondary"] == seconds
        else:
            assert ex["Definition"]["PrimaryFocusId"] == 3
            assert ex["Definition"]["SecondaryFocusId"] == 0
            assert sd["Primary"] == seconds
            assert sd["Secondary"] == 0
