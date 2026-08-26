"""Tests for the WH + JJ (2x) plan generator."""

from common.calculations import calculate_weekly_volume, check_volume_minimums
from common.io import load_exercise_mappings
from programs.wh_jj_2x import DAYS, PLAN_PREFIX, build_all, build_day

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


def test_short_days_are_hip_circuit_then_neck():
    # Tue/Thu are short: the ad/ab + wrist circuit, then a neck block last.
    for suffix in ("Tuesday", "Thursday"):
        assert _names(_by_suffix(suffix)) == [
            ["Hip Adduction", "Hip Abduction", "Wrist Rotation", "Wrist Extension"],
            ["Neck Flexion", "Neck Extension", "Neck Lateral Flexion"],
        ]


def test_neck_is_last_and_only_on_the_short_days():
    # Neck-machine work (front/back/sides) is the final block on Tue/Thu, and
    # nowhere on the full days.
    for suffix in ("Tuesday", "Thursday"):
        assert _names(_by_suffix(suffix))[-1] == [
            "Neck Flexion",
            "Neck Extension",
            "Neck Lateral Flexion",
        ]
    for suffix in ("Monday", "Wednesday", "Friday"):
        flat = [name for block in _names(_by_suffix(suffix)) for name in block]
        assert not any(name.startswith("Neck ") for name in flat)


def test_rdl_block_is_just_rdl_and_stretches_at_the_platform():
    # On Mon/Fri the platform block is RDL + stretches only -- no walking off to
    # the ankle machines. Ankle work lives in the hyper block instead.
    for suffix in ("Monday", "Friday"):
        rdl_block = _names(_by_suffix(suffix))[0]
        assert rdl_block == ["Snatch-Grip Stiff-Legged RDL", "Couch Stretch"]


def test_hyper_block_opens_with_ankle_work_then_hyper_then_cuff():
    # Mon/Fri: tib + calf lead the block (they open it and rest each hyper set),
    # then hyper, then rotator-cuff external rotation. (Wednesday folds the split
    # squat into the front of this block -- see the Wednesday structure test.)
    for suffix in ("Monday", "Friday"):
        blocks = _names(_by_suffix(suffix))
        assert [
            "Tibialis Raise",
            "Seated Calf Raise",
            "Hyperextension",
            "Cable External Rotation",
        ] in blocks


def test_wednesday_stretches_before_the_split_squats():
    # No RDL block on Wednesday. SS1 leads with the stretch (stretch -> ham ->
    # press, finishing on a stretch); the split squat moves to the BACK of SS2 so
    # it lands warm and its 2 sets don't stack at the front.
    blocks = _names(_by_suffix("Wednesday"))
    assert blocks[0] == ["Couch Stretch", "Hamstring Curl", "Leg Press"]
    ss2 = blocks[1]
    assert ss2[-1] == "ATG Split Squat"
    # Tib/calf still precede the hyper for its rest pairing.
    assert ss2.index("Tibialis Raise") < ss2.index("Hyperextension")
    assert ss2.index("Seated Calf Raise") < ss2.index("Hyperextension")


def test_wednesday_ss1_finishes_on_a_stretch():
    # The couch stretch has one more set than the leg press, so the round-robin
    # ends SS1 on a stretch (the last exercise to still have a set left).
    ss1 = _blocks(_by_suffix("Wednesday"))[0]
    counts = {ex["Definition"]["Name"]: len(ex["SetDetails"]) for ex in ss1["Exercises"]}
    assert counts["Couch Stretch"] > counts["Leg Press"]


def test_calf_and_tib_are_equal_as_the_hyper_rest_pairing():
    # Calf + tib fill the rest between hyper sets, so their set counts must match
    # (an unequal count leaves a hyper set with no filler to rest against).
    for suffix in ("Monday", "Wednesday", "Friday"):
        counts = {
            ex["Definition"]["Name"]: len(ex["SetDetails"])
            for ss in _blocks(_by_suffix(suffix))
            for ex in ss["Exercises"]
        }
        assert counts["Seated Calf Raise"] == counts["Tibialis Raise"]


def test_external_rotation_is_not_a_standalone_block():
    # Ext rotation now rides the hyper block, never its own single-exercise block.
    for day in DAYS:
        for block in _names(day):
            assert block != ["Cable External Rotation"]


def test_leg_superset_no_longer_contains_the_hyper():
    # Mon/Fri leg superset is leg press / curl / split squat; hyper moved out.
    # (Wednesday's SS1 is leg press / curl / stretch -- covered separately.)
    for suffix in ("Monday", "Friday"):
        blocks = _names(_by_suffix(suffix))
        assert ["Leg Press", "Hamstring Curl", "ATG Split Squat"] in blocks
        assert all("Hyperextension" not in b for b in blocks if "Leg Press" in b)


def test_split_squat_working_sets_by_day_plus_uncounted_warmups():
    # 3 working sets on Mon/Fri (fully warm from the RDL block), 2 on Wednesday
    # (leave session time to warm the legs up). Bodyweight/light on-ramp is stored
    # as warm-ups that don't count toward volume.
    expected = {"Monday": 3, "Wednesday": 2, "Friday": 3}
    for suffix, working in expected.items():
        split = next(
            ex
            for ss in _blocks(_by_suffix(suffix))
            for ex in ss["Exercises"]
            if ex["Definition"]["Name"] == "ATG Split Squat"
        )
        assert len(split["SetDetails"]) == working
        assert all(s["Secondary"] == 90 for s in split["SetDetails"])
        assert len(split["WarmupSetDetails"]) == 2


def test_leg_press_carries_a_warmup_ramp():
    # Quick ramp to the 400 working weight so it isn't hit cold.
    for suffix in ("Monday", "Wednesday", "Friday"):
        press = next(
            ex
            for ss in _blocks(_by_suffix(suffix))
            for ex in ss["Exercises"]
            if ex["Definition"]["Name"] == "Leg Press"
        )
        assert len(press["WarmupSetDetails"]) == 3
        assert all(s["Secondary"] == 410 for s in press["SetDetails"])


def test_wrist_prehab_runs_six_rounds_each_short_day():
    for suffix in ("Tuesday", "Thursday"):
        ss1 = _blocks(_by_suffix(suffix))[0]
        counts = {ex["Definition"]["Name"]: len(ex["SetDetails"]) for ex in ss1["Exercises"]}
        assert counts["Wrist Rotation"] == 6
        assert counts["Wrist Extension"] == 6


def test_rotator_cuff_finishes_the_full_days_only():
    # Cable external rotation ends each full day (Mon/Wed/Fri) and is absent from
    # the short T/Th days.
    with_cuff = {
        d.suffix for d in DAYS if any("Cable External Rotation" in block for block in _names(d))
    }
    assert with_cuff == {"Monday", "Wednesday", "Friday"}
    # It is a late block, never the first (leg/RDL work leads each full day).
    for suffix in ("Monday", "Wednesday", "Friday"):
        blocks = _names(_by_suffix(suffix))
        assert "Cable External Rotation" not in blocks[0]


def test_rdl_only_on_the_fresh_full_days():
    # The heavy hinge lands Mon + Fri only, never on a post-JJ (Tue/Thu) back or
    # on mid-week Wednesday.
    with_rdl = {
        d.suffix
        for d in DAYS
        if any("Snatch-Grip Stiff-Legged RDL" in block for block in _names(d))
    }
    assert with_rdl == {"Monday", "Friday"}


def test_low_back_never_on_consecutive_days():
    # Hyperextension (low back) appears Mon/Wed/Fri only, so no two adjacent
    # weekdays both train the low back.
    with_hyper = [
        any("Hyperextension" in block for block in _names(d))
        for d in DAYS  # Mon..Fri order
    ]
    assert with_hyper == [True, False, True, False, True]


def test_rdl_has_warmup_ramp_without_working_volume():
    ss1 = _blocks(_by_suffix("Monday"))[0]
    rdl = next(ex for ex in ss1["Exercises"] if ex["Definition"]["Name"].endswith("RDL"))
    assert len(rdl["SetDetails"]) == 4
    assert len(rdl["WarmupSetDetails"]) == 4


def test_hip_machine_runs_six_rounds_each_short_day():
    for suffix in ("Tuesday", "Thursday"):
        ss1 = _blocks(_by_suffix(suffix))[0]
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
