"""Tests for the WH + JJ 5-day plan generator."""

from collections import Counter

from common import calculate_weekly_volume
from common.io import load_exercise_mappings
from programs.wh_jj import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()

# Movements that share the hamstrings as a prime mover with the RDL; the RDL
# must never sit in a superset with any of them (same-muscle interference).
_HAMSTRING_PARTNERS = {"Hamstring Curl", "Hyperextension"}
# Grip-free, non-competing fillers the RDL is allowed to pair with.
_RDL_ALLOWED_PARTNERS = {"Tibialis Raise", "Seated Calf Raise"}


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
        workout = build_day(day, MAPPINGS)
        assert workout["Data"][0]["Name"] == day.plan_name


def test_one_superset_per_block():
    # FitNotes renders only the first SuperSet per block, so each block holds
    # exactly one.
    for day in DAYS:
        blocks = build_day(day, MAPPINGS)["Data"][0]["Workouts"]
        assert all(len(block["SuperSets"]) == 1 for block in blocks)


def test_block_counts_per_day():
    # Mon/Wed: [LP+curl], [split+tib], [Hyper]                   = 3
    # Tue:     [RDL+tib], [hips]                                 = 2
    # Thu:     [hips], [calf+tib], side plank, QL, scissors      = 5
    # Fri:     [RDL+calf], [LP], [Hyper]                         = 3
    expected = {"Monday": 3, "Tuesday": 2, "Wednesday": 3, "Thursday": 5, "Friday": 3}
    for day in DAYS:
        workout = build_day(day, MAPPINGS)
        assert len(workout["Data"][0]["Workouts"]) == expected[day.suffix]


def test_multi_exercise_blocks_are_named():
    for day in DAYS:
        for ss in _flatten(build_day(day, MAPPINGS)):
            if len(ss["Exercises"]) > 1:
                assert ss["Name"].startswith("Set ")


def test_weekly_set_counts():
    counts = _set_counts(build_all(MAPPINGS).values())
    assert counts["Leg Press"] == 12
    assert counts["Hamstring Curl"] == 8
    assert counts["ATG Split Squat"] == 4
    assert counts["Tibialis Raise"] == 12
    assert counts["Seated Calf Raise"] == 4
    assert counts["Hip Adduction"] == 12
    assert counts["Hip Abduction"] == 12
    assert counts["Snatch-Grip Stiff-Legged RDL"] == 8
    assert counts["Hyperextension"] == 9
    assert counts["QL Raise"] == 3
    assert counts["Side Plank"] == 1
    assert counts["Slow Scissors"] == 1
    # Bird Dog was cut -- progressed past it.
    assert counts["Bird Dog"] == 0


def test_progression_targets_clear_twelve_sets():
    # Every muscle we intend to progressively overload must reach the 12-set/wk
    # floor (secondary muscles counted at 0.5).
    vol = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    for muscle in ("Gluteals", "Hamstrings", "Adductors", "Abductors", "Tibialis", "Back (Lower)"):
        assert vol[muscle] >= 12, f"{muscle} under the 12-set floor: {vol[muscle]}"


def test_key_muscle_volumes():
    vol = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    assert vol["Hamstrings"] == 26.5
    assert vol["Gluteals"] == 22.5
    assert vol["Abductors"] == 13.0
    assert vol["Tibialis"] == 12.0
    assert vol["Adductors"] == 12.0
    # 9 hyper sets (primary) + the RDL's erectors (0.5 each) = 13; low back is the
    # hyperextension progression target with the RDL held steady at 155.
    assert vol["Back (Lower)"] == 13.0
    # Quads are maintenance only (below the floor by design).
    assert vol["Quadriceps"] == 10.0


def test_hyperextension_is_last_and_standalone_on_lifting_days():
    # Hyper leaves the low back acutely weak, so it is always the final block of
    # the day, alone, with nothing spine-loading after it. Mon/Wed/Fri only.
    for suffix in ("Monday", "Wednesday", "Friday"):
        day = next(d for d in DAYS if d.suffix == suffix)
        blocks = _flatten(build_day(day, MAPPINGS))
        last = blocks[-1]
        assert len(last["Exercises"]) == 1
        assert last["Exercises"][0]["Definition"]["Name"] == "Hyperextension"


def test_hyperextension_only_on_lifting_days():
    counts_by_day = {day.suffix: _set_counts([build_day(day, MAPPINGS)]) for day in DAYS}
    assert counts_by_day["Tuesday"]["Hyperextension"] == 0
    assert counts_by_day["Thursday"]["Hyperextension"] == 0


def test_rdl_never_supersets_with_a_hamstring_movement():
    # The RDL is grip/spine/hamstring limited; it may pair only with grip-free,
    # non-competing fillers, never with another hamstring movement.
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
    # RDL is held steady at 155 both days while the hyperextension progresses.
    def _rdl_weights(suffix):
        day = next(d for d in DAYS if d.suffix == suffix)
        rdl = next(
            ex
            for ss in _flatten(build_day(day, MAPPINGS))
            for ex in ss["Exercises"]
            if ex["Definition"]["Name"] == "Snatch-Grip Stiff-Legged RDL"
        )
        return {sd["Secondary"] for sd in rdl["SetDetails"]}

    assert _rdl_weights("Tuesday") == {155}
    assert _rdl_weights("Friday") == {155}


def test_hip_abduction_capped_at_machine_max():
    # The machine tops out at 140 lb (maxed last year), so abduction progresses
    # by reps only -- every set stays at 140.
    for day in DAYS:
        for ss in _flatten(build_day(day, MAPPINGS)):
            for ex in ss["Exercises"]:
                if ex["Definition"]["Name"] == "Hip Abduction":
                    assert all(sd["Secondary"] == 140 for sd in ex["SetDetails"])


def test_hamstring_curl_registered():
    # The single-leg curl is logged under the existing "Hamstring Curl" name so
    # last year's history carries over.
    assert MAPPINGS.equipment["Hamstring Curl"] == "Machine"
    assert MAPPINGS.primary_muscle["Hamstring Curl"] == "Hamstrings"


def test_nordic_curl_absent_everywhere():
    # The Nordic curl is dropped in favour of the single-leg machine curl.
    counts = _set_counts(build_all(MAPPINGS).values())
    assert counts["Nordic Hamstring Curl"] == 0
