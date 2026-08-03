"""Tests for the WH + JJ 5-day plan generator."""

from collections import Counter

from common import calculate_weekly_volume
from common.io import load_exercise_mappings
from programs.wh_jj import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()

# Movements sharing hamstrings/low-back with the RDL -- it must never superset
# with these.
_HAMSTRING_PARTNERS = {"Hamstring Curl", "Hyperextension"}
# Grip-free, non-competing fillers the RDL may pair with.
_RDL_ALLOWED_PARTNERS = {"Tibialis Raise", "Seated Calf Raise", "Couch Stretch"}
_LEG_SUPERSET_NAMES = {"Leg Press", "Hamstring Curl", "ATG Split Squat", "Hyperextension"}


def _flatten(workout):
    blocks = workout["Data"][0]["Workouts"]
    return [ss for block in blocks for ss in block["SuperSets"]]


def _superset_blocks(workout):
    """The blocks that contain more than one exercise."""
    return [ss for ss in _flatten(workout) if len(ss["Exercises"]) > 1]


def _set_counts(workouts):
    counts: Counter[str] = Counter()
    for workout in workouts:
        for ss in _flatten(workout):
            for ex in ss["Exercises"]:
                counts[ex["Definition"]["Name"]] += len(ex["SetDetails"])
    return counts


def _day(suffix):
    return next(d for d in DAYS if d.suffix == suffix)


def test_five_days_with_expected_names():
    workouts = build_all(MAPPINGS)
    assert list(workouts.keys()) == [
        f"{PLAN_PREFIX} - Monday",
        f"{PLAN_PREFIX} - Tuesday",
        f"{PLAN_PREFIX} - Wednesday",
        f"{PLAN_PREFIX} - Thursday",
        f"{PLAN_PREFIX} - Friday",
    ]


def test_workout_name_matches_day():
    for day in DAYS:
        assert build_day(day, MAPPINGS)["Data"][0]["Name"] == day.plan_name


def test_one_superset_per_block():
    # FitNotes renders only the first SuperSet per block, so each holds one.
    for day in DAYS:
        blocks = build_day(day, MAPPINGS)["Data"][0]["Workouts"]
        assert all(len(block["SuperSets"]) == 1 for block in blocks)


def test_block_counts_per_day():
    # Mon: [RDL+tib+couch], [leg superset]                      = 2
    # Tue: [hips+wrist], [calf+tib+ext-rot]                     = 2
    # Wed: [leg superset]                                       = 1
    # Thu: [hips+wrist], [calf+tib+ext-rot]                     = 2
    # Fri: [RDL+calf+tib+couch], [leg superset], elephant walk  = 3
    expected = {"Monday": 2, "Tuesday": 2, "Wednesday": 1, "Thursday": 2, "Friday": 3}
    for day in DAYS:
        assert len(build_day(day, MAPPINGS)["Data"][0]["Workouts"]) == expected[day.suffix]


def test_multi_exercise_blocks_are_named():
    for day in DAYS:
        for ss in _flatten(build_day(day, MAPPINGS)):
            if len(ss["Exercises"]) > 1:
                assert ss["Name"].startswith("Set ")


def test_weekly_set_counts():
    counts = _set_counts(build_all(MAPPINGS).values())
    assert counts["Leg Press"] == 9
    assert counts["Hamstring Curl"] == 9
    # 3 rounds x 3 days: each day is 1 bodyweight on-ramp + 2 working.
    assert counts["ATG Split Squat"] == 9
    assert counts["Hyperextension"] == 9
    # Working sets only; the warm-up ramp lives in WarmupSetDetails.
    assert counts["Snatch-Grip Stiff-Legged RDL"] == 8
    assert counts["Tibialis Raise"] == 12
    assert counts["Seated Calf Raise"] == 6
    assert counts["Cable External Rotation"] == 6
    assert counts["Couch Stretch"] == 4
    assert counts["Hip Adduction"] == 12
    assert counts["Hip Abduction"] == 12
    assert counts["Wrist Rotation"] == 12
    assert counts["Wrist Extension"] == 12
    assert counts["Elephant Walk"] == 1
    assert counts["Band Neck Flexion"] == 4
    assert counts["Band Neck Extension"] == 4


def test_progression_targets_clear_twelve_sets():
    vol = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    for muscle in ("Gluteals", "Hamstrings", "Adductors", "Abductors", "Tibialis", "Back (Lower)"):
        assert vol[muscle] >= 12, f"{muscle} under the 12-set floor: {vol[muscle]}"


def test_key_muscle_volumes():
    vol = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    assert vol["Hamstrings"] == 27.0
    assert vol["Gluteals"] == 22.0
    assert vol["Back (Lower)"] == 13.0
    assert vol["Adductors"] == 12.0
    assert vol["Abductors"] == 12.0
    assert vol["Tibialis"] == 12.0
    # Wrist prehab (12 each) + the RDL's forearms = deliberate wrist-health volume.
    assert vol["Forearms"] == 28.0
    # Rotator-cuff maintenance.
    assert vol["Rotator Cuff"] == 6.0
    # Band neck prehab -- conservative start (2 sets each x Tue/Thu).
    assert vol["Neck"] == 8.0


def test_rdl_warmups_excluded_from_volume():
    # The RDL warm-up ramp is stored in WarmupSetDetails, so it never inflates
    # working volume.
    for suffix in ("Monday", "Friday"):
        rdl = next(
            ex
            for ss in _flatten(build_day(_day(suffix), MAPPINGS))
            for ex in ss["Exercises"]
            if ex["Definition"]["Name"] == "Snatch-Grip Stiff-Legged RDL"
        )
        assert len(rdl["SetDetails"]) == 4
        assert len(rdl["WarmupSetDetails"]) == 4


def test_leg_superset_on_mwf():
    # Leg press + curl + split squat + hyper ride one superset on Mon/Wed/Fri.
    for suffix in ("Monday", "Wednesday", "Friday"):
        blocks = _superset_blocks(build_day(_day(suffix), MAPPINGS))
        assert any(
            {ex["Definition"]["Name"] for ex in ss["Exercises"]} >= _LEG_SUPERSET_NAMES
            for ss in blocks
        ), f"{suffix}: leg superset missing an exercise"


def test_rdl_only_on_monday_and_friday():
    # Low back is clustered on Mon/Wed/Fri and rested Tue/Thu; the RDL lands only
    # on the two freshest back days.
    expected = {"Monday": 4, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 4}
    for suffix, count in expected.items():
        counts = _set_counts([build_day(_day(suffix), MAPPINGS)])
        assert counts["Snatch-Grip Stiff-Legged RDL"] == count


def test_hyperextension_only_on_lifting_days():
    for suffix in ("Tuesday", "Thursday"):
        counts = _set_counts([build_day(_day(suffix), MAPPINGS)])
        assert counts["Hyperextension"] == 0


def test_rdl_never_supersets_with_a_hamstring_movement():
    for day in DAYS:
        for ss in _superset_blocks(build_day(day, MAPPINGS)):
            names = {ex["Definition"]["Name"] for ex in ss["Exercises"]}
            if "Snatch-Grip Stiff-Legged RDL" in names:
                partners = names - {"Snatch-Grip Stiff-Legged RDL"}
                assert not (partners & _HAMSTRING_PARTNERS), (
                    f"{day.suffix}: RDL superset with a hamstring movement"
                )
                assert partners <= _RDL_ALLOWED_PARTNERS, (
                    f"{day.suffix}: RDL paired with a non-approved partner {partners}"
                )


def test_rdl_held_steady_at_155():
    for suffix in ("Monday", "Friday"):
        rdl = next(
            ex
            for ss in _flatten(build_day(_day(suffix), MAPPINGS))
            for ex in ss["Exercises"]
            if ex["Definition"]["Name"] == "Snatch-Grip Stiff-Legged RDL"
        )
        assert {sd["Secondary"] for sd in rdl["SetDetails"]} == {155}


def test_hip_abduction_capped_at_machine_max():
    for day in DAYS:
        for ss in _flatten(build_day(day, MAPPINGS)):
            for ex in ss["Exercises"]:
                if ex["Definition"]["Name"] == "Hip Abduction":
                    assert all(sd["Secondary"] == 140 for sd in ex["SetDetails"])


def test_wrist_prehab_in_hip_superset_twelve_per_week():
    grip = {"Wrist Rotation", "Wrist Extension"}
    for suffix in ("Tuesday", "Thursday"):
        hip_block = next(
            ss
            for ss in _superset_blocks(build_day(_day(suffix), MAPPINGS))
            if any(ex["Definition"]["Name"] == "Hip Adduction" for ex in ss["Exercises"])
        )
        names = {ex["Definition"]["Name"] for ex in hip_block["Exercises"]}
        assert grip <= names, f"{suffix}: wrist prehab not in the hip superset"
    counts = _set_counts(build_all(MAPPINGS).values())
    assert counts["Wrist Rotation"] == 12
    assert counts["Wrist Extension"] == 12


def test_external_rotation_on_tue_thu_only():
    for suffix in ("Tuesday", "Thursday"):
        assert _set_counts([build_day(_day(suffix), MAPPINGS)])["Cable External Rotation"] == 3
    for suffix in ("Monday", "Wednesday", "Friday"):
        assert _set_counts([build_day(_day(suffix), MAPPINGS)])["Cable External Rotation"] == 0


def test_elephant_walk_is_friday_finisher():
    blocks = _flatten(build_day(_day("Friday"), MAPPINGS))
    last = blocks[-1]
    assert len(last["Exercises"]) == 1
    assert last["Exercises"][0]["Definition"]["Name"] == "Elephant Walk"


def test_split_squat_has_bodyweight_onramp():
    # Round 1 is a bodyweight on-ramp (0), rounds 2-3 are the working weight.
    split = next(
        ex
        for ss in _flatten(build_day(_day("Monday"), MAPPINGS))
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == "ATG Split Squat"
    )
    assert [sd["Secondary"] for sd in split["SetDetails"]] == [0, 90, 90]


def test_hamstring_curl_registered():
    assert MAPPINGS.equipment["Hamstring Curl"] == "Machine"
    assert MAPPINGS.primary_muscle["Hamstring Curl"] == "Hamstrings"


def test_wrist_prehab_registered():
    for name in ("Wrist Rotation", "Wrist Extension"):
        assert MAPPINGS.equipment[name] == "Single Dumbbell"
        assert MAPPINGS.primary_muscle[name] == "Forearms"


def test_band_neck_registered_and_on_tue_thu():
    for name in ("Band Neck Flexion", "Band Neck Extension"):
        assert MAPPINGS.equipment[name] == "None"
        assert MAPPINGS.primary_muscle[name] == "Neck"
    for suffix in ("Tuesday", "Thursday"):
        counts = _set_counts([build_day(_day(suffix), MAPPINGS)])
        assert counts["Band Neck Flexion"] == 2
        assert counts["Band Neck Extension"] == 2
    for suffix in ("Monday", "Wednesday", "Friday"):
        counts = _set_counts([build_day(_day(suffix), MAPPINGS)])
        assert counts["Band Neck Flexion"] == 0
        assert counts["Band Neck Extension"] == 0


def test_nordic_curl_absent_everywhere():
    counts = _set_counts(build_all(MAPPINGS).values())
    assert counts["Nordic Hamstring Curl"] == 0
