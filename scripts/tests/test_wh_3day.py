"""Tests for the WH 3-Day plan generator."""

from common.calculations import calculate_weekly_volume, check_volume_minimums
from common.io import load_exercise_mappings
from programs.wh_3day import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()

# Progression targets the plan is designed to keep at or above the 12-set floor.
_PROGRESSION_TARGETS = [
    "Gluteals",
    "Hamstrings",
    "Back (Lower)",
    "Adductors",
    "Abductors",
    "Tibialis",
]


def _blocks(day):
    """Flatten a built day into its ordered list of supersets (one per block)."""
    workout = build_day(day, MAPPINGS)
    return [ss for block in workout["Data"][0]["Workouts"] for ss in block["SuperSets"]]


def _names(day):
    return [[ex["Definition"]["Name"] for ex in ss["Exercises"]] for ss in _blocks(day)]


def _by_suffix(suffix):
    return next(d for d in DAYS if d.suffix == suffix)


def test_three_days():
    assert [d.suffix for d in DAYS] == ["Sunday", "Tuesday", "Thursday"]


def test_plan_names():
    workouts = build_all(MAPPINGS)
    assert set(workouts) == {
        f"{PLAN_PREFIX} - Sunday",
        f"{PLAN_PREFIX} - Tuesday",
        f"{PLAN_PREFIX} - Thursday",
    }


def test_each_superset_is_its_own_block():
    # FitNotes only renders the first SuperSet within a block, so each superset
    # must be its own Workouts[] entry.
    for day in DAYS:
        blocks = build_day(day, MAPPINGS)["Data"][0]["Workouts"]
        assert all(len(block["SuperSets"]) == 1 for block in blocks)


def test_tuesday_and_thursday_are_identical():
    assert _names(_by_suffix("Tuesday")) == _names(_by_suffix("Thursday"))


def test_sunday_structure():
    # SS1 is the RDL block; SS2 is the leg superset; SS3 is the finisher.
    assert _names(_by_suffix("Sunday")) == [
        ["Snatch-Grip Stiff-Legged RDL", "Tibialis Raise", "Couch Stretch"],
        ["Leg Press", "Hamstring Curl", "ATG Split Squat", "Hyperextension"],
        ["Elephant Walk"],
    ]


def test_short_day_structure():
    # Hip machine circuit, then the leg-press / curl / hyper circuit.
    assert _names(_by_suffix("Tuesday")) == [
        ["Hip Adduction", "Hip Abduction", "Tibialis Raise"],
        ["Leg Press", "Hamstring Curl", "Hyperextension"],
    ]


def test_rdl_is_fresh_day_only():
    # The heavy hinge must never land on a post-JJ (Tue/Thu) back.
    for suffix in ("Tuesday", "Thursday"):
        flat = [name for block in _names(_by_suffix(suffix)) for name in block]
        assert "Snatch-Grip Stiff-Legged RDL" not in flat


def test_rdl_has_warmup_ramp_without_working_volume():
    ss1 = _blocks(_by_suffix("Sunday"))[0]
    rdl = next(ex for ex in ss1["Exercises"] if ex["Definition"]["Name"].endswith("RDL"))
    assert len(rdl["SetDetails"]) == 4
    assert len(rdl["WarmupSetDetails"]) == 4


def test_hip_machine_runs_six_rounds_each_short_day():
    ss1 = _blocks(_by_suffix("Tuesday"))[0]
    counts = {ex["Definition"]["Name"]: len(ex["SetDetails"]) for ex in ss1["Exercises"]}
    assert counts["Hip Adduction"] == 6
    assert counts["Hip Abduction"] == 6


def test_progression_targets_clear_the_floor():
    volume = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    results = check_volume_minimums(volume, default_minimum=12)
    below = {
        m: results[m]["current"] for m in _PROGRESSION_TARGETS if not results[m]["meets_minimum"]
    }
    assert not below, f"muscles below the 12-set floor: {below}"
