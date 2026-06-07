"""Tests for common.builders."""

import pytest

from common.builders import (
    SetConfig,
    build_exercise,
    build_superset,
    build_workout,
    build_workout_from_supersets,
)
from common.io import load_exercise_mappings

MAPPINGS = load_exercise_mappings()


def _supersets(workout):
    return workout["Data"][0]["Workouts"][0]["SuperSets"]


# ---------------------------------------------------------------------------
# build_exercise
# ---------------------------------------------------------------------------


def test_build_exercise_unknown_name_raises():
    with pytest.raises(KeyError):
        build_exercise("Not A Real Exercise", [SetConfig(reps=5)], MAPPINGS)


def test_build_exercise_one_set_detail_per_set():
    ex = build_exercise("ATG Split Squat", [SetConfig(reps=8) for _ in range(4)], MAPPINGS)
    assert len(ex["SetDetails"]) == 4
    assert all(sd["Primary"] == 8 for sd in ex["SetDetails"])


def test_build_exercise_accepts_dict_sets():
    ex = build_exercise("Hyperextension", [{"reps": 12}], MAPPINGS)
    assert ex["SetDetails"][0]["Primary"] == 12
    assert ex["SetDetails"][0]["Secondary"] == 0


def test_build_exercise_secondary_focus_zero_when_bodyweight():
    ex = build_exercise("Bird Dog Row", [SetConfig(reps=10, weight=0)], MAPPINGS)
    assert ex["Definition"]["SecondaryFocusId"] == 0


def test_build_exercise_secondary_focus_weight_when_loaded():
    ex = build_exercise("ATG Split Squat", [SetConfig(reps=8, weight=50)], MAPPINGS)
    assert ex["Definition"]["SecondaryFocusId"] == 2
    assert ex["Definition"]["MaxSecondary"] == 50


def test_build_exercise_categories_primary_then_secondary():
    ex = build_exercise("ATG Split Squat", [SetConfig(reps=8)], MAPPINGS)
    names = [c["Name"] for c in ex["Definition"]["Categories"]]
    assert names[0] == "Quadriceps"
    assert "Adductors" in names


# ---------------------------------------------------------------------------
# build_superset / build_workout
# ---------------------------------------------------------------------------


def test_build_superset_wraps_exercises():
    a = build_exercise("Hyperextension", [SetConfig(reps=12)], MAPPINGS)
    b = build_exercise("Bird Dog Row", [SetConfig(reps=10)], MAPPINGS)
    ss = build_superset([a, b])
    assert ss["Exercises"] == [a, b]
    assert ss["Name"]  # FitNotes requires a non-empty superset name


def test_build_workout_default_one_superset_per_exercise():
    a = build_exercise("Hyperextension", [SetConfig(reps=12)], MAPPINGS)
    b = build_exercise("Bird Dog Row", [SetConfig(reps=10)], MAPPINGS)
    workout = build_workout("Test", [a, b])
    supersets = _supersets(workout)
    assert len(supersets) == 2
    assert all(len(ss["Exercises"]) == 1 for ss in supersets)


def test_build_workout_supersets_true_groups_all():
    a = build_exercise("Hyperextension", [SetConfig(reps=12)], MAPPINGS)
    b = build_exercise("Bird Dog Row", [SetConfig(reps=10)], MAPPINGS)
    workout = build_workout("Test", [a, b], supersets=True)
    supersets = _supersets(workout)
    assert len(supersets) == 1
    assert len(supersets[0]["Exercises"]) == 2


# ---------------------------------------------------------------------------
# build_workout_from_supersets
# ---------------------------------------------------------------------------


def test_build_workout_from_supersets_preserves_groups_and_order():
    ss1 = build_superset([build_exercise("Hyperextension", [SetConfig(reps=12)], MAPPINGS)])
    ss2 = build_superset(
        [
            build_exercise("ATG Split Squat", [SetConfig(reps=8)], MAPPINGS),
            build_exercise("Bird Dog Row", [SetConfig(reps=10)], MAPPINGS),
        ],
    )
    workout = build_workout_from_supersets("My Plan", [ss1, ss2])

    assert workout["Data"][0]["Name"] == "My Plan"
    supersets = _supersets(workout)
    # Exercises and order preserved; supersets renumbered sequentially.
    assert [ss["Exercises"] for ss in supersets] == [ss1["Exercises"], ss2["Exercises"]]
    assert [ss["Name"] for ss in supersets] == ["Set 1", "Set 2"]
    assert [len(ss["Exercises"]) for ss in supersets] == [1, 2]


def test_build_workout_from_supersets_uses_fitnotes_import_format():
    # Regression guard: without these markers FitNotes collapses every exercise
    # in a superset onto the first one's Definition on import.
    ss = build_superset([build_exercise("Hyperextension", [SetConfig(reps=12)], MAPPINGS)])
    workout = build_workout_from_supersets("Plan", [ss])
    assert workout["Version"] == "3.4.2"
    assert workout["Type"] == "FNWorkoutDefinitionDTO"
    assert workout["Data"][0]["SortIndex"] == 0
    assert all(s["Name"] for s in _supersets(workout))
