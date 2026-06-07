"""Tests for the Back Rehab 1 plan generator."""

from common.io import load_exercise_mappings
from programs.back_rehab_one import PLAN_NAME, SETS_PER_EXERCISE, build_plan

MAPPINGS = load_exercise_mappings()


def _supersets():
    workout = build_plan(MAPPINGS)
    blocks = workout["Data"][0]["Workouts"]
    # One SuperSet per block; flatten across blocks in order.
    return workout, [ss for block in blocks for ss in block["SuperSets"]]


def test_plan_name():
    workout, _ = _supersets()
    assert workout["Data"][0]["Name"] == PLAN_NAME


def test_two_supersets():
    _, supersets = _supersets()
    assert len(supersets) == 2


def test_each_superset_is_its_own_block():
    # FitNotes only renders the first SuperSet within a block, so each superset
    # must be its own Workouts[] entry.
    workout = build_plan(MAPPINGS)
    blocks = workout["Data"][0]["Workouts"]
    assert len(blocks) == 2
    assert all(len(block["SuperSets"]) == 1 for block in blocks)


def test_supersets_are_named_for_import():
    # Each multi-exercise superset needs a Name or FitNotes collapses it.
    _, supersets = _supersets()
    assert [ss["Name"] for ss in supersets] == ["Set 1", "Set 2"]


def test_superset_exercise_order():
    _, supersets = _supersets()
    names = [[ex["Definition"]["Name"] for ex in ss["Exercises"]] for ss in supersets]
    assert names == [
        ["Nordic Hamstring Curl", "Snatch-Grip Stiff-Legged RDL"],
        ["ATG Split Squat", "Hyperextension", "Bird Dog Row"],
    ]


def test_every_exercise_has_four_sets():
    _, supersets = _supersets()
    for ss in supersets:
        for ex in ss["Exercises"]:
            assert len(ex["SetDetails"]) == SETS_PER_EXERCISE


def test_reps_match_definition():
    _, supersets = _supersets()
    reps = {
        ex["Definition"]["Name"]: ex["SetDetails"][0]["Primary"]
        for ss in supersets
        for ex in ss["Exercises"]
    }
    assert reps == {
        "Nordic Hamstring Curl": 12,
        "Snatch-Grip Stiff-Legged RDL": 8,
        "ATG Split Squat": 12,
        "Hyperextension": 35,
        "Bird Dog Row": 12,
    }


def test_weights_match_definition():
    _, supersets = _supersets()
    weights = {
        ex["Definition"]["Name"]: ex["SetDetails"][0]["Secondary"]
        for ss in supersets
        for ex in ss["Exercises"]
    }
    assert weights == {
        "Nordic Hamstring Curl": 0,
        "Snatch-Grip Stiff-Legged RDL": 135,
        "ATG Split Squat": 75,
        "Hyperextension": 0,
        "Bird Dog Row": 55,
    }
