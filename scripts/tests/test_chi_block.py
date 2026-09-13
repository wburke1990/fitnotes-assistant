"""Tests for the CHI (Chicago home gym) plan generator."""

from common.calculations import calculate_weekly_volume, check_volume_minimums
from common.io import load_exercise_mappings
from programs.chi_block import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()

BACK_DAYS = ("Monday", "Wednesday", "Friday")
LEG_DAYS = ("Tuesday", "Thursday")

# The three drivers the block is built around, plus the two supporting
# progressions that are also expected to clear the 12-set floor.
_PROGRESSION_TARGETS = [
    "Back (Lower)",
    "Adductors",
    "Quadriceps",
    "Hamstrings",
    "Tibialis",
]

_HYPER = "Hyperextension"
_SIDE_HYPER = "Side-Lying Hyperextension Adductor Raise"
_SPLIT = "Front Rack Split Squat"
_RDL = "Snatch-Grip Stiff-Legged RDL"


def _blocks(day):
    """Flatten a built day into its ordered list of supersets (one per block)."""
    workout = build_day(day, MAPPINGS)
    return [ss for block in workout["Data"][0]["Workouts"] for ss in block["SuperSets"]]


def _names(day):
    return [[ex["Definition"]["Name"] for ex in ss["Exercises"]] for ss in _blocks(day)]


def _by_suffix(suffix):
    return next(d for d in DAYS if d.suffix == suffix)


def _set_counts(suffix):
    return {
        ex["Definition"]["Name"]: len(ex["SetDetails"])
        for ss in _blocks(_by_suffix(suffix))
        for ex in ss["Exercises"]
    }


def _find(suffix, name):
    return next(
        ex
        for ss in _blocks(_by_suffix(suffix))
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == name
    )


def _days_with(name):
    return {d.suffix for d in DAYS if any(name in block for block in _names(d))}


def test_five_weekday_days():
    assert [d.suffix for d in DAYS] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def test_plan_names():
    assert set(build_all(MAPPINGS)) == {f"{PLAN_PREFIX} - {d.suffix}" for d in DAYS}


def test_each_superset_is_its_own_block():
    # FitNotes only renders the first SuperSet within a block, so each superset
    # must be its own Workouts[] entry.
    for day in DAYS:
        blocks = build_day(day, MAPPINGS)["Data"][0]["Workouts"]
        assert all(len(block["SuperSets"]) == 1 for block in blocks)


# ---------------------------------------------------------------------------
# Low back -- the first driver
# ---------------------------------------------------------------------------


def test_low_back_never_on_consecutive_days():
    # Hyperextension lands Mon/Wed/Fri only, so no two adjacent weekdays both
    # train the low back.
    trained = [any(_HYPER in block for block in _names(d)) for d in DAYS]  # Mon..Fri
    assert trained == [True, False, True, False, True]


def test_rdl_only_on_the_fresh_days_and_never_midweek():
    # The heavy hinge lands Mon + Fri. Wednesday carries no hinge at all -- it is
    # the back's mid-week rest.
    assert _days_with(_RDL) == {"Monday", "Friday"}


def test_hyper_is_three_sets_on_each_back_day():
    for suffix in BACK_DAYS:
        assert _set_counts(suffix)[_HYPER] == 3


def test_hyper_and_side_hyper_are_never_in_the_same_block():
    # Same bench, same trunk. Stacking them in one round-robin would leave the
    # low back no rest between them, so they get separate blocks.
    for day in DAYS:
        for block in _names(day):
            assert not (_HYPER in block and _SIDE_HYPER in block)


def test_hyper_starts_unloaded_for_the_rep_ramp():
    # Reps ramp to 35/side before any load goes on, so every hyper set is
    # bodyweight.
    for suffix in BACK_DAYS:
        hyper = _find(suffix, _HYPER)
        assert all(s["Secondary"] == 0 for s in hyper["SetDetails"])


# ---------------------------------------------------------------------------
# Adductors -- the second driver
# ---------------------------------------------------------------------------


def test_side_hyper_clears_its_floor_on_the_back_days():
    # 4 sets x 3 back days = 12/wk, the adductor progression floor on its own.
    assert _days_with(_SIDE_HYPER) == set(BACK_DAYS)
    for suffix in BACK_DAYS:
        assert _set_counts(suffix)[_SIDE_HYPER] == 4


def test_side_hyper_starts_unloaded_for_the_rep_ramp():
    for suffix in BACK_DAYS:
        side = _find(suffix, _SIDE_HYPER)
        assert all(s["Secondary"] == 0 for s in side["SetDetails"])


# ---------------------------------------------------------------------------
# Front rack split squat -- the third driver
# ---------------------------------------------------------------------------


def test_split_squat_runs_heavy_twice_and_paused_once():
    assert _days_with(_SPLIT) == {"Tuesday", "Wednesday", "Thursday"}
    for suffix in LEG_DAYS:
        split = _find(suffix, _SPLIT)
        assert [s["Secondary"] for s in split["SetDetails"]] == [70, 70, 70, 70]
    paused = _find("Wednesday", _SPLIT)
    assert [s["Secondary"] for s in paused["SetDetails"]] == [50, 50, 50]


def test_split_squat_warmups_are_uncounted():
    # Bodyweight -> empty bar on the heavy days; bodyweight only on the lighter
    # paused day. Warm-ups live in WarmupSetDetails so they never inflate volume.
    for suffix in LEG_DAYS:
        assert [s["Secondary"] for s in _find(suffix, _SPLIT)["WarmupSetDetails"]] == [0, 45]
    assert [s["Secondary"] for s in _find("Wednesday", _SPLIT)["WarmupSetDetails"]] == [0]


def test_leg_days_stretch_before_the_split_squat():
    # The lift is limited by strength in the deep position, so the hips are
    # warmed in the opening block, before the squats.
    for suffix in LEG_DAYS:
        blocks = _names(_by_suffix(suffix))
        assert "Couch Stretch" in blocks[0]
        squat_block = next(i for i, b in enumerate(blocks) if _SPLIT in b)
        assert squat_block > 0


# ---------------------------------------------------------------------------
# The hamstring tendon slot
# ---------------------------------------------------------------------------


def test_tendon_slot_is_five_sets_on_leg_days_only():
    # 5 x 5 at a 6RM, 3s down / 3s up. Tendon adaptation saturates at a low
    # volume, so this stays 5 sets and never grows into a hypertrophy block.
    # Every-other-day only: heavy loading leaves a tendon in net collagen
    # breakdown for about a day.
    assert _days_with("Cable Leg Curl") == set(LEG_DAYS)
    for suffix in LEG_DAYS:
        assert _set_counts(suffix)["Cable Leg Curl"] == 5


# ---------------------------------------------------------------------------
# Accessories and structure
# ---------------------------------------------------------------------------


def test_neck_is_last_and_only_on_the_leg_days():
    neck = ["Neck Flexion", "Neck Extension", "Neck Lateral Flexion"]
    for suffix in LEG_DAYS:
        assert _names(_by_suffix(suffix))[-1] == neck
    for suffix in BACK_DAYS:
        flat = [name for block in _names(_by_suffix(suffix)) for name in block]
        assert not any(name.startswith("Neck ") for name in flat)


def test_tibialis_holds_its_twelve_set_floor():
    # 4 sets x 3 back days = 12/wk on the tib bar (one-legged).
    assert _days_with("Tibialis Raise") == set(BACK_DAYS)
    for suffix in BACK_DAYS:
        assert _set_counts(suffix)["Tibialis Raise"] == 4


def test_abductors_are_a_maintenance_dose_at_load():
    # Deliberately below the floor (3 x 2 days = 6/wk) -- held, not progressed.
    assert _days_with("Cable Hip Abduction") == set(LEG_DAYS)
    for suffix in LEG_DAYS:
        assert _set_counts(suffix)["Cable Hip Abduction"] == 3
    assert all(s["Secondary"] > 0 for s in _find("Tuesday", "Cable Hip Abduction")["SetDetails"])


def test_upper_body_only_ever_rides_the_rest():
    # Upper body is not a priority: it fills the rest inside a block and never
    # leads one, so it can never displace a driving set.
    upper = {
        "Barbell Incline Bench Press",
        "Ring Dip",
        "Handstand Push-Up",
        "Lat Pulldown",
        "Low Row",
        "Face Pull",
    }
    for day in DAYS:
        for block in _names(day):
            assert block[0] not in upper


def test_timed_holds_use_time_focus():
    for name, suffix in (("L-Sit", "Tuesday"), ("Elephant Walk", "Friday")):
        assert _find(suffix, name)["Definition"]["PrimaryFocusId"] == 3


def test_couch_stretch_logs_per_side_time():
    # 2 sides x 120 s stored as one set: Primary = sides, Secondary = seconds.
    stretch = _find("Tuesday", "Couch Stretch")
    assert stretch["Definition"]["SecondaryFocusId"] == 3
    assert all(s["Primary"] == 2 and s["Secondary"] == 120 for s in stretch["SetDetails"])


def test_progression_targets_clear_the_floor():
    volume = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    results = check_volume_minimums(volume, default_minimum=12)
    below = {
        m: results[m]["current"] for m in _PROGRESSION_TARGETS if not results[m]["meets_minimum"]
    }
    assert not below, f"muscles below the 12-set floor: {below}"
