"""Tests for the CHI (Chicago home gym) plan generator."""

from common.calculations import calculate_weekly_volume, check_volume_minimums
from common.io import load_exercise_mappings
from programs.chi_block import DAYS, PLAN_PREFIX, build_all, build_day

MAPPINGS = load_exercise_mappings()

BIG_DAYS = ("Monday", "Wednesday", "Friday")
LIGHT_DAYS = ("Tuesday", "Thursday")

_RDL = "Snatch-Grip Stiff-Legged RDL"
_SPLIT = "Front Rack Split Squat"
_HYPER = "Hyperextension"
_NORDIC = "Nordic Hamstring Curl"
_SIDE_HYPER = "Side-Lying Hyperextension Adductor Raise"

# Grip is a recovery limiter, so every grip-heavy movement clusters on the same
# days. The RDL is trained raw (no straps) and is the biggest stressor. The 40 lb
# one-arm calf raise is NOT on this list -- that weight doesn't tire the hands.
GRIP_MOVES = {_RDL, "Lat Pulldown", "Low Row"}

# The posterior chain is the same story: these cannot be spread across
# alternating days and recovered, so they cluster too. The split squat is in the
# list because it taxes the hamstrings hard, even though it costs no grip.
POSTERIOR_MOVES = {_RDL, _NORDIC, _SPLIT, _HYPER}

# The four movements that each get their OWN superset on a big day, so none of
# them rests against another taxing the same tissue.
HEAVY_MOVES = {_RDL, _SPLIT, _HYPER, _NORDIC}

# The three drivers, plus the two supporting progressions also expected to clear
# the 12-set floor.
_PROGRESSION_TARGETS = [
    "Back (Lower)",
    "Adductors",
    "Quadriceps",
    "Hamstrings",
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


def _flat(suffix):
    return {name for block in _names(_by_suffix(suffix)) for name in block}


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
# The two recovery constraints that shape the week
# ---------------------------------------------------------------------------


def test_grip_work_is_clustered_on_the_big_days():
    # Heavy grip on back-to-back days does not recover, so every grip-heavy
    # movement lands Mon/Wed/Fri and the light days carry none.
    for move in GRIP_MOVES:
        assert _days_with(move) <= set(BIG_DAYS), f"{move} escapes the grip cluster"
    for suffix in LIGHT_DAYS:
        assert not (GRIP_MOVES & _flat(suffix))


def test_posterior_chain_is_clustered_on_the_big_days():
    # Same reasoning: RDLs, hamstring work and the hypers cannot be spread across
    # alternating days. The split squat joins them because it taxes hamstrings.
    for move in POSTERIOR_MOVES:
        assert _days_with(move) <= set(BIG_DAYS), f"{move} escapes the posterior cluster"
    for suffix in LIGHT_DAYS:
        assert not (POSTERIOR_MOVES & _flat(suffix))


def test_every_big_day_carries_the_full_cluster():
    # Wednesday runs the same shape at reduced load rather than dropping
    # movements -- alternating hinge days with non-hinge days is the pattern that
    # does not recover.
    for suffix in BIG_DAYS:
        assert _flat(suffix) >= HEAVY_MOVES, f"{suffix} is missing part of the cluster"


def test_heavy_movements_never_share_a_superset():
    # Each of the four gets its own block, so none rests against another taxing
    # the same tissue.
    for day in DAYS:
        for block in _names(day):
            assert len(HEAVY_MOVES & set(block)) <= 1, block


def test_the_pull_only_ever_rides_the_nordic_curl():
    # The one deliberate pairing: Nordics tax neither grip nor low back, so the
    # grip-heavy pull can rest against them for free.
    for day in DAYS:
        for block in _names(day):
            pulls = {"Lat Pulldown", "Low Row"} & set(block)
            if pulls:
                assert _NORDIC in block, f"{pulls} paired with {block}"


def test_low_back_never_on_consecutive_days():
    trained = [any(_HYPER in block for block in _names(d)) for d in DAYS]  # Mon..Fri
    assert trained == [True, False, True, False, True]


# ---------------------------------------------------------------------------
# The three drivers
# ---------------------------------------------------------------------------


def test_hyper_is_three_unloaded_sets_on_each_big_day():
    # Reps ramp to 35/side before any load goes on, so every set is bodyweight.
    for suffix in BIG_DAYS:
        assert _set_counts(suffix)[_HYPER] == 3
        assert all(s["Secondary"] == 0 for s in _find(suffix, _HYPER)["SetDetails"])


def test_side_hyper_clears_its_floor_on_the_light_days():
    # 6 sets x 2 light days = 12/wk. It costs no grip and no hamstring, so it
    # belongs off the big days.
    assert _days_with(_SIDE_HYPER) == set(LIGHT_DAYS)
    for suffix in LIGHT_DAYS:
        assert _set_counts(suffix)[_SIDE_HYPER] == 6
        assert all(s["Secondary"] == 0 for s in _find(suffix, _SIDE_HYPER)["SetDetails"])


def test_split_squat_runs_heavy_twice_and_paused_once():
    assert _days_with(_SPLIT) == set(BIG_DAYS)
    for suffix in ("Monday", "Friday"):
        assert [s["Secondary"] for s in _find(suffix, _SPLIT)["SetDetails"]] == [70, 70, 70, 70]
        assert [s["Secondary"] for s in _find(suffix, _SPLIT)["WarmupSetDetails"]] == [0, 45]
    paused = _find("Wednesday", _SPLIT)
    assert [s["Secondary"] for s in paused["SetDetails"]] == [50, 50, 50]
    assert [s["Secondary"] for s in paused["WarmupSetDetails"]] == [0]


def test_wednesday_cuts_rdl_volume_not_rdl_load():
    # The RDL is a maintenance lift here (held steady while the hypers drive),
    # and strength is maintained by training at the same LOAD, not the same
    # volume. So Wednesday keeps 155 and drops two sets. A lighter bar would be
    # neither heavy enough to hold anything nor light enough to be free, and
    # high-rep RDL is off the table -- form degrades where the back is rehabbing.
    for suffix in ("Monday", "Friday"):
        assert [s["Secondary"] for s in _find(suffix, _RDL)["SetDetails"]] == [155] * 4
    assert [s["Secondary"] for s in _find("Wednesday", _RDL)["SetDetails"]] == [155] * 2


def test_hinge_leads_every_big_day_with_the_stretch_on_its_rest():
    # Hinge first, on the freshest back; the couch stretch rides its rest at the
    # bar and warms the deep position the split squat is limited by.
    for suffix in BIG_DAYS:
        first = _names(_by_suffix(suffix))[0]
        assert first == [_RDL, "Couch Stretch"]
        split_block = next(i for i, b in enumerate(_names(_by_suffix(suffix))) if _SPLIT in b)
        assert split_block > 0


# ---------------------------------------------------------------------------
# Tendon slot and accessories
# ---------------------------------------------------------------------------


def test_nordic_is_the_tendon_slot_at_four_sets():
    # A slow heavy eccentric is the high-strain loading tendons adapt to, and it
    # saturates at a low volume -- so this stays 4 sets and never grows into a
    # hypertrophy block.
    assert _days_with(_NORDIC) == set(BIG_DAYS)
    for suffix in BIG_DAYS:
        assert _set_counts(suffix)[_NORDIC] == 4


def test_neck_is_last_and_only_on_the_light_days():
    neck = ["Neck Flexion", "Neck Extension", "Neck Lateral Flexion"]
    for suffix in LIGHT_DAYS:
        assert _names(_by_suffix(suffix))[-1] == neck
    for suffix in BIG_DAYS:
        assert not any(name.startswith("Neck ") for name in _flat(suffix))


def test_tibialis_holds_its_twelve_set_floor():
    assert _days_with("Tibialis Raise") == set(BIG_DAYS)
    for suffix in BIG_DAYS:
        assert _set_counts(suffix)["Tibialis Raise"] == 4


def test_abductors_are_a_maintenance_dose_at_load():
    # Deliberately below the floor (3 x 2 days = 6/wk) -- held, not progressed,
    # which only works if the weight stays up.
    assert _days_with("Cable Hip Abduction") == set(LIGHT_DAYS)
    for suffix in LIGHT_DAYS:
        assert _set_counts(suffix)["Cable Hip Abduction"] == 3
    assert all(s["Secondary"] > 0 for s in _find("Tuesday", "Cable Hip Abduction")["SetDetails"])


def test_calves_are_loaded_and_live_on_the_light_days():
    # 40 lb kettlebell in one hand, 35 reps per side (70 total). It is a one-arm
    # hold, but 40 lb does not tire the hands, so it is exempt from the grip
    # cluster -- and keeping it here holds three sets off the time-pressured
    # big days.
    assert _days_with("Standing Calf Raise") == set(LIGHT_DAYS)
    for suffix in LIGHT_DAYS:
        calf = _find(suffix, "Standing Calf Raise")
        assert all(s["Secondary"] == 40 for s in calf["SetDetails"])
        assert all(s["Primary"] == 70 for s in calf["SetDetails"])


def test_shoulder_health_work_is_present_on_the_light_days():
    # Face pulls are the only external-rotation / rear-delt work in the plan --
    # the antagonist to the grappling pulls and posts, so they matter from month
    # two on. Light enough that the rope costs no meaningful grip, which is what
    # lets them sit on a no-grip day instead of competing for a big-day slot.
    assert _days_with("Face Pull") == set(LIGHT_DAYS)
    for suffix in LIGHT_DAYS:
        assert _set_counts(suffix)["Face Pull"] == 3


def test_pulling_is_thin_but_present_on_every_big_day():
    # The grip cluster confines pulling to Mon/Wed/Fri and, within them, to the
    # Nordic's rest. Guard that it does not vanish entirely in a later edit.
    for suffix in BIG_DAYS:
        assert {"Lat Pulldown", "Low Row"} & _flat(suffix)


def test_filler_never_leads_a_block():
    # Accessories ride the rest between the driving sets; they never displace one.
    filler = {
        "Barbell Incline Bench Press",
        "Ring Dip",
        "Handstand Push-Up",
        "Lat Pulldown",
        "Low Row",
        "L-Sit",
        "Tibialis Raise",
        "Standing Calf Raise",
        "Face Pull",
        "Couch Stretch",
    }
    for day in DAYS:
        for block in _names(day):
            assert block[0] not in filler


def test_timed_holds_use_time_focus():
    for name, suffix in (("L-Sit", "Monday"), ("Elephant Walk", "Friday")):
        assert _find(suffix, name)["Definition"]["PrimaryFocusId"] == 3


def test_couch_stretch_logs_per_side_time():
    # 2 sides x 120 s stored as one set: Primary = sides, Secondary = seconds.
    stretch = _find("Monday", "Couch Stretch")
    assert stretch["Definition"]["SecondaryFocusId"] == 3
    assert all(s["Primary"] == 2 and s["Secondary"] == 120 for s in stretch["SetDetails"])


def test_progression_targets_clear_the_floor():
    volume = calculate_weekly_volume(list(build_all(MAPPINGS).values()))
    results = check_volume_minimums(volume, default_minimum=12)
    below = {
        m: results[m]["current"] for m in _PROGRESSION_TARGETS if not results[m]["meets_minimum"]
    }
    assert not below, f"muscles below the 12-set floor: {below}"
