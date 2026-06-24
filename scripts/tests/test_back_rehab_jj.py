"""Tests for the Back Rehab + JJ 3-day plan generator."""

from collections import Counter

from common import calculate_weekly_volume
from common.io import load_exercise_mappings
from programs.back_rehab_jj import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()


def _flatten(workout):
    blocks = workout["Data"][0]["Workouts"]
    return [ss for block in blocks for ss in block["SuperSets"]]


def _superset_blocks(workout):
    """The supersets that contain more than one exercise (the main SS1-3)."""
    return [ss for ss in _flatten(workout) if len(ss["Exercises"]) > 1]


def _standalone_names(workout):
    """Ordered names of single-exercise blocks (prehab drills / Yoga)."""
    return [
        ss["Exercises"][0]["Definition"]["Name"]
        for ss in _flatten(workout)
        if len(ss["Exercises"]) == 1
    ]


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


def test_each_day_has_three_main_supersets():
    # Each day still has exactly three multi-exercise supersets (SS1-SS3); the
    # prehab drills (and Sunday's Yoga) now sit in their own standalone blocks.
    for day in DAYS:
        workout = build_day(day, MAPPINGS)
        assert len(_superset_blocks(workout)) == 3
        # FitNotes renders only the first SuperSet per block.
        blocks = workout["Data"][0]["Workouts"]
        assert all(len(block["SuperSets"]) == 1 for block in blocks)


def test_block_counts_per_day():
    # Sunday: SS1, [Yoga], SS2, SS3 = 4 blocks.
    # Tuesday/Thursday: SS1, [drill], SS2, [drill], SS3, [drill] = 6 blocks.
    expected = {"Sunday": 4, "Tuesday": 6, "Thursday": 6}
    for day in DAYS:
        workout = build_day(day, MAPPINGS)
        assert len(workout["Data"][0]["Workouts"]) == expected[day.suffix]


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
    # Copenhagen is kept out of the adductor supersets, so it appears only once
    # per Tue/Thu session (2 sets each) -> 4 total.
    assert counts["Copenhagen Plank"] == 4
    assert counts["Standing Calf Raise"] == 10
    # Sunday SS3 Tibialis went from 2 -> 3 sets, so weekly total is now 11.
    assert counts["Tibialis Raise"] == 11
    assert counts["Couch Stretch"] == 2
    assert counts["Yoga"] == 1


def test_copenhagen_and_adductor_never_share_a_superset():
    # Copenhagen Plank and the adductor raise are both adductor movements; they
    # must never sit in the same superset on Tuesday or Thursday.
    for day in DAYS[1:]:
        for ss in _flatten(build_day(day, MAPPINGS)):
            names = {ex["Definition"]["Name"] for ex in ss["Exercises"]}
            assert not (
                "Copenhagen Plank" in names and "Side-Lying Hyperextension Adductor Raise" in names
            ), f"{day.suffix}: Copenhagen and adductor raise share a superset"


def test_ss3_adductor_before_hyperextension():
    # In Tuesday & Thursday SS3, the Side-Lying Hyperextension Adductor Raise
    # (heavier / less stable) must be sequenced before the regular
    # Hyperextension for safety.
    for day in DAYS[1:]:
        ss3 = _superset_blocks(build_day(day, MAPPINGS))[2]
        names = [ex["Definition"]["Name"] for ex in ss3["Exercises"]]
        assert "Side-Lying Hyperextension Adductor Raise" in names
        assert "Hyperextension" in names
        assert names.index("Side-Lying Hyperextension Adductor Raise") < names.index(
            "Hyperextension"
        ), f"{day.suffix}: adductor raise must come before hyperextension in SS3"


def test_calf_and_copenhagen_map_forearms_secondary():
    # The global registry change adds Forearms as a secondary muscle on both
    # the Standing Calf Raise and the (weighted) Copenhagen Plank.
    for name in ("Standing Calf Raise", "Copenhagen Plank"):
        assert "Forearms" in MAPPINGS.secondary_muscles[name], (
            f"{name} should map Forearms as a secondary muscle"
        )


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


def test_prehab_drills_are_standalone_blocks_after_supersets():
    # Each prehab drill must be its OWN single-exercise block placed
    # immediately AFTER the superset it follows (the between-superset rest),
    # not a member of the round-robin superset.
    main_names = {
        "Snatch-Grip Stiff-Legged RDL",
        "Nordic Hamstring Curl",
        "Hyperextension",
    }
    expected = {
        "Tuesday": ["Hip Internal Rotation", "Hip Airplane", "Plank"],
        "Thursday": ["Side Hip Abduction", "Wall Back Extension", "QL Plank"],
    }
    for day in DAYS[1:]:
        workout = build_day(day, MAPPINGS)
        blocks = _flatten(workout)
        # The standalone drills, in order, match the expected post-SS sequence.
        assert _standalone_names(workout) == expected[day.suffix]
        # No drill is a member of any multi-exercise superset.
        drills = set(expected[day.suffix])
        for ss in _superset_blocks(workout):
            ss_names = {ex["Definition"]["Name"] for ex in ss["Exercises"]}
            assert not (drills & ss_names)
        # Each drill block directly follows a superset (the block before it is
        # a multi-exercise superset anchored by an RDL/Nordic/Hyper movement).
        for i, ss in enumerate(blocks):
            name = ss["Exercises"][0]["Definition"]["Name"]
            if name in drills:
                assert i > 0
                prev_names = {ex["Definition"]["Name"] for ex in blocks[i - 1]["Exercises"]}
                assert len(blocks[i - 1]["Exercises"]) > 1
                assert prev_names & main_names


def test_atg_split_squat_warmup_loads():
    sunday = build_day(DAYS[0], MAPPINGS)
    # The two warm-up sets now live in a single ATG entry (SS2), so the
    # distinct loads are gathered across every set of every ATG entry.
    weights = sorted(
        {
            sd["Secondary"]
            for ss in _flatten(sunday)
            for ex in ss["Exercises"]
            if ex["Definition"]["Name"] == "ATG Split Squat"
            for sd in ex["SetDetails"]
        }
    )
    # Bodyweight, empty bar, working sets.
    assert weights == [0, 45, 70]


def test_atg_warmup_is_one_entry_with_two_sets():
    # The bodyweight + empty-bar warm-up sets are merged into ONE ATG entry in
    # SS2 with two sets [0, 45]; the working sets (70) remain a separate entry.
    sunday = build_day(DAYS[0], MAPPINGS)
    ss2 = _superset_blocks(sunday)[1]
    atg = [ex for ex in ss2["Exercises"] if ex["Definition"]["Name"] == "ATG Split Squat"]
    assert len(atg) == 1
    assert [sd["Secondary"] for sd in atg[0]["SetDetails"]] == [0, 45]


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
    # 2 sets, each 2 sides x 120 seconds, time carried in the Secondary field.
    assert len(couch["SetDetails"]) == 2
    assert all(sd["Primary"] == 2 for sd in couch["SetDetails"])
    assert all(sd["Secondary"] == 120 for sd in couch["SetDetails"])
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


def test_yoga_is_standalone_block_between_ss1_and_ss2():
    # Yoga is its own single-exercise block placed immediately AFTER SS1 (the
    # RDL superset) and BEFORE SS2; it is not a member of any main superset.
    workout = build_day(DAYS[0], MAPPINGS)
    blocks = _flatten(workout)
    # SS1 (RDL), then a standalone Yoga block, then SS2 (Nordic).
    ss1_names = [ex["Definition"]["Name"] for ex in blocks[0]["Exercises"]]
    assert "Snatch-Grip Stiff-Legged RDL" in ss1_names
    assert "Yoga" not in ss1_names
    assert len(blocks[1]["Exercises"]) == 1
    assert blocks[1]["Exercises"][0]["Definition"]["Name"] == "Yoga"
    ss2_names = [ex["Definition"]["Name"] for ex in blocks[2]["Exercises"]]
    assert "Nordic Hamstring Curl" in ss2_names
    assert "Yoga" not in ss2_names
    # Yoga appears in no multi-exercise superset.
    for ss in _superset_blocks(workout):
        assert "Yoga" not in [ex["Definition"]["Name"] for ex in ss["Exercises"]]


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
    assert 16 <= vol["Calves"] <= 19
    assert 10 <= vol["Adductors"] <= 14
    assert 13 <= vol["Back (Lower)"] <= 16
    assert vol["Tibialis"] == 11
    # Forearms is a secondary on the grip-heavy RDL (9 sets), Standing Calf
    # Raise (10) and Copenhagen Plank (4): (9 + 10 + 4) * 0.5 = 11.5.
    assert vol["Forearms"] == 11.5
