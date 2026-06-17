"""Tests for the Back Rehab + JJ 3-day plan generator."""

from collections import Counter

from common import calculate_weekly_volume
from common.io import load_exercise_mappings
from programs.back_rehab_jj import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()


def _flatten(workout):
    blocks = workout["Data"][0]["Workouts"]
    return [ss for block in blocks for ss in block["SuperSets"]]


def _set_counts(workouts):
    counts: Counter[str] = Counter()
    for workout in workouts:
        for ss in _flatten(workout):
            for ex in ss["Exercises"]:
                counts[ex["Definition"]["Name"]] += len(ex["SetDetails"])
    return counts


def test_three_days_with_expected_names():
    workouts = build_all(MAPPINGS)
    assert list(workouts.keys()) == [
        f"{PLAN_PREFIX} - Sunday",
        f"{PLAN_PREFIX} - Tuesday",
        f"{PLAN_PREFIX} - Thursday",
    ]


def test_each_day_has_three_blocks():
    for day in DAYS:
        workout = build_day(day, MAPPINGS)
        blocks = workout["Data"][0]["Workouts"]
        assert len(blocks) == 3
        # FitNotes renders only the first SuperSet per block.
        assert all(len(block["SuperSets"]) == 1 for block in blocks)


def test_multi_exercise_blocks_are_named():
    for day in DAYS:
        for ss in _flatten(build_day(day, MAPPINGS)):
            if len(ss["Exercises"]) > 1:
                assert ss["Name"].startswith("Set ")


def test_workout_name_matches_day():
    for day in DAYS:
        workout = build_day(day, MAPPINGS)
        assert workout["Data"][0]["Name"] == day.plan_name


def test_weekly_set_counts():
    counts = _set_counts(build_all(MAPPINGS).values())
    assert counts["Snatch-Grip Stiff-Legged RDL"] == 9
    assert counts["Nordic Hamstring Curl"] == 9
    assert counts["Hyperextension"] == 9
    # 4 working sets + 2 warm-up sets (bodyweight + empty bar) = 6.
    assert counts["ATG Split Squat"] == 6
    assert counts["Side-Lying Hyperextension Adductor Raise"] == 8
    assert counts["Copenhagen Plank"] == 8
    assert counts["Standing Calf Raise"] == 12
    assert counts["Tibialis Raise"] == 8
    assert counts["Yoga"] == 1


def test_prehab_drills_one_set_each():
    counts = _set_counts(build_all(MAPPINGS).values())
    for drill in (
        "Hip Internal Rotation",
        "Hip Airplane",
        "Plank",
        "Side Hip Abduction",
        "Wall Back Extension",
        "QL Plank",
    ):
        assert counts[drill] == 1


def test_atg_split_squat_warmup_loads():
    sunday = build_day(DAYS[0], MAPPINGS)
    weights = sorted(
        ex["SetDetails"][0]["Secondary"]
        for ss in _flatten(sunday)
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == "ATG Split Squat"
    )
    # Bodyweight, empty bar, working sets.
    assert weights == [0, 45, 70]


def test_weighted_copenhagen_preserves_load():
    # The weighted Copenhagen keeps its added load (Secondary = lb) rather than
    # a timed hold, so its weight is non-zero and focus is reps/weight.
    tuesday = build_day(DAYS[1], MAPPINGS)
    copenhagen = next(
        ex
        for ss in _flatten(tuesday)
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == "Copenhagen Plank"
    )
    assert copenhagen["SetDetails"][0]["Secondary"] > 0
    assert copenhagen["Definition"]["PrimaryFocusId"] == 1
    assert copenhagen["Definition"]["SecondaryFocusId"] == 2
    # 2 sides logged as the rep count.
    assert copenhagen["SetDetails"][0]["Primary"] == 2


def test_couch_stretch_is_per_side_timed():
    sunday = build_day(DAYS[0], MAPPINGS)
    couch = next(
        ex
        for ss in _flatten(sunday)
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == "Couch Stretch"
    )
    # 2 sides x 120 seconds, time carried in the Secondary field (focus 3).
    assert couch["SetDetails"][0]["Primary"] == 2
    assert couch["SetDetails"][0]["Secondary"] == 120
    assert couch["Definition"]["SecondaryFocusId"] == 3


def test_yoga_is_timed_hold():
    sunday = build_day(DAYS[0], MAPPINGS)
    yoga = next(
        ex
        for ss in _flatten(sunday)
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == "Yoga"
    )
    assert yoga["Definition"]["PrimaryFocusId"] == 3
    assert yoga["SetDetails"][0]["Primary"] == 120


def test_yoga_resolves_in_mappings():
    assert "Yoga" in MAPPINGS.equipment
    assert MAPPINGS.equipment["Yoga"] == "None"
    assert MAPPINGS.primary_muscle["Yoga"] == "Hip Flexors"


def test_new_exercises_registered():
    for name in (
        "Standing Calf Raise",
        "Side-Lying Hyperextension Adductor Raise",
        "Copenhagen Plank",
        "Yoga",
    ):
        assert name in MAPPINGS.equipment
        assert name in MAPPINGS.primary_muscle


def test_key_muscle_volumes_in_range():
    vol = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    assert 20 <= vol["Hamstrings"] <= 25
    assert 18 <= vol["Calves"] <= 21
    assert 14 <= vol["Adductors"] <= 18
    assert 13 <= vol["Back (Lower)"] <= 16
    assert vol["Tibialis"] == 8
