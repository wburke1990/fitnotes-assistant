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


def _heavy_in(superset):
    """Heavy movements in a superset, ignoring the split-squat RAMP.

    The ramp (bodyweight and the empty bar) deliberately rides the Nordic block
    so it costs no extra time; it is not a heavy set and does not count against
    the one-heavy-movement-per-block rule.
    """
    heavy = set()
    for ex in superset["Exercises"]:
        name = ex["Definition"]["Name"]
        if name not in HEAVY_MOVES:
            continue
        if name == _SPLIT and max(s["Secondary"] for s in ex["SetDetails"]) <= 45:
            continue
        heavy.add(name)
    return heavy


def test_heavy_movements_never_share_a_superset():
    # Each of the four gets its own block, so none rests against another taxing
    # the same tissue.
    for day in DAYS:
        for superset in _blocks(day):
            assert len(_heavy_in(superset)) <= 1, [
                ex["Definition"]["Name"] for ex in superset["Exercises"]
            ]


def test_both_pull_angles_ride_a_big_day_rest():
    # Grip confines pulling to the big days. The vertical pull rides the Nordic's
    # rest (Nordics cost neither grip nor low back); the horizontal one rides the
    # split squat's (the front rack costs no grip either). Every big day gets both.
    for suffix in BIG_DAYS:
        blocks = _names(_by_suffix(suffix))
        nordic_block = next(b for b in blocks if _NORDIC in b)
        assert "Lat Pulldown" in nordic_block
        work_block = next(b for b in blocks if _SPLIT in b and b is not nordic_block)
        assert "Low Row" in work_block
    for suffix in LIGHT_DAYS:
        assert not ({"Lat Pulldown", "Low Row"} & _flat(suffix))


def test_low_back_never_on_consecutive_days():
    trained = [any(_HYPER in block for block in _names(d)) for d in DAYS]  # Mon..Fri
    assert trained == [True, False, True, False, True]


# ---------------------------------------------------------------------------
# The three drivers
# ---------------------------------------------------------------------------


def test_hyper_sets_never_fall_below_thirty_five_reps():
    # The convention is to TRANSFORM the reps, not shorten the set: the opening
    # reps are the hardest variant currently owned, the rest are finished as
    # regular reps, and every set totals at least 35. Progression is the hard
    # fraction growing, so the logged count only ever goes up.
    for suffix in BIG_DAYS:
        hyper = _find(suffix, _HYPER)
        assert len(hyper["SetDetails"]) == 3
        assert all(s["Primary"] >= 35 for s in hyper["SetDetails"])
        assert all(s["Secondary"] == 0 for s in hyper["SetDetails"])


def test_hypers_finish_every_big_day_alone():
    # At 35+ reps a hyper set is long enough to need no filler to rest against,
    # and it is the driver, so it gets the end of the session to itself. Friday's
    # elephant walk is decompression after the work, not part of it.
    for suffix in BIG_DAYS:
        blocks = [b for b in _names(_by_suffix(suffix)) if b != ["Elephant Walk"]]
        assert blocks[-1] == [_HYPER]


def test_side_hyper_clears_its_floor_on_the_light_days():
    # 6 sets x 2 light days = 12/wk. It costs no grip and no hamstring, so it
    # belongs off the big days.
    assert _days_with(_SIDE_HYPER) == set(LIGHT_DAYS)
    for suffix in LIGHT_DAYS:
        assert _set_counts(suffix)[_SIDE_HYPER] == 6
        assert all(s["Secondary"] == 0 for s in _find(suffix, _SIDE_HYPER)["SetDetails"])


def _split_entries(suffix):
    """The split squat appears twice on a big day: the ramp, then the work."""
    return [
        ex
        for ss in _blocks(_by_suffix(suffix))
        for ex in ss["Exercises"]
        if ex["Definition"]["Name"] == _SPLIT
    ]


def test_split_squat_runs_heavy_twice_and_paused_once():
    assert _days_with(_SPLIT) == set(BIG_DAYS)
    # Two bodyweight rungs before the empty bar -- the deep position needs more
    # opening than the load does, and the reps are free inside the Nordic's rest.
    for suffix in ("Monday", "Friday"):
        ramp, work = _split_entries(suffix)
        assert [s["Secondary"] for s in ramp["SetDetails"]] == [0, 0, 45]
        assert [s["Secondary"] for s in work["SetDetails"]] == [70, 70, 70, 70]
    ramp, work = _split_entries("Wednesday")
    assert [s["Secondary"] for s in ramp["SetDetails"]] == [0, 0]
    assert [s["Secondary"] for s in work["SetDetails"]] == [50, 50, 50]


def test_the_ramp_fits_inside_the_nordic_rounds():
    # The ramp rides one rung per round, so it cannot be longer than the Nordic.
    for suffix in BIG_DAYS:
        ramp = _split_entries(suffix)[0]
        assert len(ramp["SetDetails"]) <= _set_counts(suffix)[_NORDIC]


def test_split_squat_ramp_rides_the_nordic_block():
    # The ramp is not stacked on top of the working sets as warm-ups -- it goes
    # one rung per round inside the Nordic/pull block, so it costs no extra time
    # and the bar is warm when the working block starts.
    for suffix in BIG_DAYS:
        blocks = _names(_by_suffix(suffix))
        nordic_at = next(i for i, b in enumerate(blocks) if _NORDIC in b)
        assert _SPLIT in blocks[nordic_at]
        # And the working block, which the split squat LEADS, comes after it.
        work_at = next(i for i, b in enumerate(blocks) if b[0] == _SPLIT)
        assert nordic_at < work_at


def test_split_squat_carries_no_warmup_sets():
    # The ramp is real, counted reps inside the Nordic block, not WarmupSetDetails.
    for suffix in BIG_DAYS:
        for entry in _split_entries(suffix):
            assert entry["WarmupSetDetails"] == []


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


def test_tibialis_holds_its_twelve_set_floor_on_the_light_days():
    # Moved off the big days to save time there; 6 sets x 2 days still clears 12.
    assert _days_with("Tibialis Raise") == set(LIGHT_DAYS)
    for suffix in LIGHT_DAYS:
        assert _set_counts(suffix)["Tibialis Raise"] == 6


def test_all_pushing_lives_on_the_light_days():
    # Pressing costs neither grip nor hamstrings, so it has no business taking
    # up time on a big day.
    for move in ("Barbell Incline Bench Press", "Handstand Push-Up", "Ring Dip"):
        assert _days_with(move) == set(LIGHT_DAYS), f"{move} is on a big day"


def test_big_days_are_four_blocks_of_work():
    # Hinge, Nordic block, working split squat, hypers. Nothing else.
    for suffix in BIG_DAYS:
        blocks = [b for b in _names(_by_suffix(suffix)) if b != ["Elephant Walk"]]
        assert len(blocks) == 4, blocks


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


def test_filler_never_leads_a_block_on_a_big_day():
    # On a big day every block is led by its driving movement; the accessories
    # ride its rest. (Light days are the opposite by design -- the pushing block
    # is led by the incline press, because there is no driver to displace.)
    filler = {
        "Barbell Incline Bench Press",
        "Handstand Push-Up",
        "Lat Pulldown",
        "Low Row",
        "L-Sit",
        "Couch Stretch",
    }
    for suffix in BIG_DAYS:
        for block in _names(_by_suffix(suffix)):
            if block[0] == _SPLIT:  # the working split-squat block leads its own
                continue
            assert block[0] not in filler, block


def test_timed_holds_use_time_focus():
    for name, suffix in (("L-Sit", "Tuesday"), ("Elephant Walk", "Friday")):
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
