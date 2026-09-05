#!/usr/bin/env python3
"""Generate the "WH + JJ (2x)" 5-day/week plan as five .fnw files.

The WH-gym plan for the twice-a-week jujitsu schedule: JJ on Tuesday + Thursday
only, lifting Monday-Friday. This supersedes the older "WH + JJ" plan (wh_jj.py),
which assumed JJ ~5x/week and used all five lifts as short post-JJ sessions.

Now the split is:
  * Mon / Wed / Fri -- FULL lower-body / posterior-chain / back-rehab days
    (not after JJ, so there's time and a fresh back).
  * Tue / Thu -- SHORT sessions right after the JJ class (shower at the gym
    anyway): one dense hip adduction/abduction machine circuit, with wrist
    prehab (rotation + extension) filling the rest during the 6 ad/ab rounds,
    then a quick neck-machine block (front / back / sides) last.

The WH machines the user doesn't have at home get the emphasis: the leg press
(loaded for glutes), the hip adduction/abduction machine, and the tibialis
("tip") machine.

Must-hit, per the user:
  * Back-rehab progression CONTINUES -- snatch-grip RDL (heavy, Mon + Fri, the
    freshest-back days) plus the hyperextension (the low-back progression driver,
    on Mon/Wed/Fri). Low back clears the 12-set floor (~13) from M/W/F alone, so
    Tue/Thu stay short and the low back is never trained on consecutive days.
  * Hip adduction + abduction machine -- 6 rounds on each short day = 12/wk each.
  * Leg press -- loaded, gluteal-biased; pools to ~22 across the week.
  * Tibialis machine -- rep progression, 12/wk (4 sets on each full day, paired
    with calf in the hyper block at the adjacent machines).

Programming principles (see scripts/programs/README.md):
  * Per-MUSCLE weekly volume >= 12 sets to PROGRESS (add load or reps); secondary
    muscles count 0.5, pooled across every movement. Below 12 is maintenance.
  * LOW BACK is trained Mon/Wed/Fri only -- never on consecutive days (Tue/Thu
    carry no low-back work), and the heavy RDL lands on the two freshest days.
    Within a full day the two low-back hits are spread apart: RDL block first,
    then the leg superset, then the hyper block -- max recovery between them.
  * Wrist prehab (rotation + extension) rides the Tue/Thu ad/ab rest -- free
    rest-work on adjacent machines. Rotator-cuff external rotation rides the
    Mon/Wed/Fri hyper block (cables next to the hyper), off the short days so the
    tight T/Th circuit stays at the ad/ab machines. Neck (machine, front/back/
    sides) is done last on Tue/Thu -- grappling-durability prehab.

Progression targets (>=12 sets/wk): Gluteals (leg press), Hamstrings (RDL +
curl), Back (Lower) (hypers + RDL), Adductors, Abductors (reps only -- machine
maxed), Tibialis (reps). Maintenance: Quadriceps (split squat), Calves, Forearms
(wrist prehab, 12/wk each), Rotator Cuff (external rotation, 6/wk).

The hyperextension progression detail lives in the companion note (a .fnw has no
notes field): plans/wh/WH + JJ (2x) - progression notes.txt

Usage:
    uv --directory scripts run python -m programs.wh_jj_2x
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common import (
    build_exercise,
    build_superset,
    build_workout_from_supersets,
    load_exercise_mappings,
    write_workout_file,
)
from common.builders import SetConfig
from common.io import ExerciseMapping

PLAN_PREFIX = "WH + JJ (2x)"


@dataclass
class Move:
    """One exercise within a block: its working sets, focus mode, and warm-ups."""

    name: str
    sets: list[SetConfig]
    focus: str = "reps"
    secondary_focus: str = "weight"
    warmups: list[SetConfig] = field(default_factory=list)


def _reps(name: str, reps: int, weight: float, count: int) -> Move:
    """A normal reps/weight lift repeated `count` sets."""
    return Move(name, [SetConfig(reps=reps, weight=weight) for _ in range(count)])


def _hold(name: str, seconds: int) -> Move:
    """A whole-body timed hold (Primary = seconds)."""
    return Move(name, [SetConfig(reps=seconds)], focus="time")


# --- Shared moves. Weights are starting targets, adjustable in FitNotes. ------

# RDL: snatch-grip, NO straps (grip trained raw), held steady at 155 while the
# hypers progress. Warm-up ramp (empty bar x2, 95, 135) is stored as warm-up
# sets, so it adds gym time but NOT working volume. Mon + Fri (freshest backs).
_RDL = Move(
    "Snatch-Grip Stiff-Legged RDL",
    [SetConfig(reps=8, weight=155) for _ in range(4)],
    warmups=[
        SetConfig(reps=12, weight=45),
        SetConfig(reps=12, weight=45),
        SetConfig(reps=12, weight=95),
        SetConfig(reps=8, weight=135),
    ],
)

# Gluteal-biased leg press (feet high, deep stretch) -- stands in for squats
# until the back is strong enough. 3 working rounds on each full day @ 430.
# Carries a quick warm-up ramp (~1 min to the working weight). Warm-ups don't
# count toward volume.
_LEG_PRESS = Move(
    "Leg Press",
    [SetConfig(reps=12, weight=430) for _ in range(3)],
    warmups=[
        SetConfig(reps=10, weight=180),
        SetConfig(reps=6, weight=280),
        SetConfig(reps=3, weight=360),
    ],
)
# Single-leg machine curl, logged as "Hamstring Curl" (same exercise as last
# year, so history carries over). Reps per side; starting 12/side @ 100.
_CURL = _reps("Hamstring Curl", reps=24, weight=100, count=3)


# Quad / knee MAINTENANCE, two DBs at the sides (less low-back demand than a
# barbell front rack). Reps per side; weight = total of both DBs (two 45s = 90).
# The bodyweight + light on-ramp is stored as warm-up sets (not counted). WORKING
# sets differ by day: 3 on Mon/Fri (you arrive fully warm from the RDL block, and
# do the split-squat warm-ups during the RDL rests), but 2 on Wednesday -- there's
# no RDL block, so Wednesday spends session time warming the legs up and runs one
# fewer working set. 3 + 2 + 3 = 8 working sets/wk.
def _split_squat(working: int) -> Move:
    return Move(
        "ATG Split Squat",
        [SetConfig(reps=24, weight=90) for _ in range(working)],
        warmups=[SetConfig(reps=24, weight=0), SetConfig(reps=24, weight=50)],
    )


_SPLIT_SQUAT = _split_squat(3)  # Monday
# Friday: warm-up ramp matches Wednesday's two bodyweight sets -> 50 before the
# working 90s (bodyweight, bodyweight, 50). Warm-ups stay uncounted.
_SPLIT_SQUAT_FRI = Move(
    "ATG Split Squat",
    [SetConfig(reps=24, weight=90) for _ in range(3)],
    warmups=[
        SetConfig(reps=24, weight=0),
        SetConfig(reps=24, weight=0),
        SetConfig(reps=24, weight=50),
    ],
)
# Wednesday: the split squat is LAST in SS2 and ramps across the round-robin as 4
# regular sets -- bodyweight -> 50 (two 25s) -> 90 -> 90, one per round -- plus ONE
# bodyweight WARM-UP set (uncounted) on top. So 3 sets sit below the 90 working
# weight: the warm-up at 0, then the 0 and 50 that are the squat's first two sets.
# The four round-robin sets count toward volume; the warm-up doesn't.
_SPLIT_SQUAT_WED = Move(
    "ATG Split Squat",
    [
        SetConfig(reps=24, weight=0),
        SetConfig(reps=24, weight=50),
        SetConfig(reps=24, weight=90),
        SetConfig(reps=24, weight=90),
    ],
    warmups=[SetConfig(reps=24, weight=0)],
)
# The Mon/Fri leg superset (leg press / curl / split squat). Hyper is NOT here --
# it moved to its own block with calf/tib (see below), which spreads the low-back
# work (RDL early, hyper late) and keeps the ankle work off the platform. Wednesday
# splits this up differently (stretch in SS1, split squat in SS2) -- see _days().
# Friday uses a variant whose split squat carries one extra warm-up rung.
_LEG_SUPERSET = [_LEG_PRESS, _CURL, _SPLIT_SQUAT]
_LEG_SUPERSET_FRI = [_LEG_PRESS, _CURL, _SPLIT_SQUAT_FRI]

# Bodyweight hyperextension -- the rehab progression driver, 3 sets on each full
# day (Mon/Wed/Fri) = 9; +RDL erectors -> low back ~13. The 1-leg + curved-back
# leading reps and the flat-machine static-hold restart are in the companion note.
_HYPER = _reps("Hyperextension", reps=35, weight=0, count=3)
# Tibialis progresses by reps (light fixed load): 4 sets on each full day
# (Mon/Wed/Fri) = 12/wk. Calf + tib are the REST between hyper sets, so they must
# be EQUAL -- otherwise a hyper set has no filler to rest against. 4 each covers
# all 3 hyper sets plus a trailing pair, and keeps tib at its 12 floor.
_TIB = _reps("Tibialis Raise", reps=70, weight=22.5, count=4)
_CALF = _reps("Seated Calf Raise", reps=20, weight=100, count=4)
# The hyper block: hyper paired with calf + tibialis + rotator-cuff external
# rotation, whose machines (and the cables) all sit next to the hyper at WH.
# Non-interfering (low back vs lower leg vs shoulder), and they fill the rest
# between hyper sets. This is where the ankle + cuff work lives now -- off the
# RDL platform, so the platform is never left unattended. (_EXT_ROTATION defined
# below.)


# Couch stretch -- warms the quads/hip flexors for the split squats (per side,
# 2 min = 4 min/set). Mon/Fri: 3 sets riding the RDL rest, at the platform (never
# abandoned). Wednesday: 2 sets (~8 min) riding the leg-press/curl rests, since
# there's no RDL block -- the split squats then come in the SECOND superset, warm.
# 2 sides x 120s logged as one set (counts once for volume).
def _couch(sets: int, minutes_per_side: int = 2, sides_per_set: int = 2) -> Move:
    return Move(
        "Couch Stretch",
        [SetConfig(reps=sides_per_set, weight=minutes_per_side * 60) for _ in range(sets)],
        secondary_focus="time",
    )


# Mon/Fri: 3 sets, both sides x 2 min, riding the RDL rest at the platform.
_COUCH = _couch(3)
# Wednesday SS1: the stretch is split ONE SIDE per superset round (2 min each),
# 4 bouts leading each round (stretch -> ham -> press) -- alternate L/R/L/R. A
# stretch fills every rest, and being one set longer than the leg press the block
# FINISHES on a stretch. Same ~8 min total, just distributed one side at a time.
_COUCH_WED = _couch(4, sides_per_set=1)
# Rotator-cuff prehab (shoulder health): external rotation, the antagonist to all
# the internal-rotation gripping/pulling in JJ. Light, higher-rep (never heavy --
# that's how a cuff gets tweaked). 2 sets x 3 full days = 6/wk, maintenance (not a
# 12 floor). Rides the hyper block on the cables next to the hyper machine -- kept
# off the short days so the tight T/Th circuit stays at the ad/ab machines.
_EXT_ROTATION = _reps("Cable External Rotation", reps=30, weight=12, count=2)
# Order: tib + calf lead, so the block OPENS with them (they warm up the lower
# leg) and each hyper set gets an ankle pair right before it as its rest. Because
# tib/calf are 4 and hypers are 3, exactly one tib/calf pair lands at the very end
# -- one trailing pair instead of the two you'd get with hyper listed first.
_HYPER_BLOCK = [_TIB, _CALF, _HYPER, _EXT_ROTATION]

# Antagonist machine circuit, 6 rounds each on Tue/Thu = 12/wk each. Both are
# ramping load back up right now: abduction 150, adduction 100 (starting targets).
# Keep adding load; if abduction tops out the machine's plate, switch it to reps.
_HIP_ADDUCTION = _reps("Hip Adduction", reps=10, weight=100, count=6)
_HIP_ABDUCTION = _reps("Hip Abduction", reps=12, weight=150, count=6)
# Wrist prehab (anti-flexion extensors + rotation) fills the rest during the 6
# ad/ab rounds -- the machines sit next to each other, so it's free rest-work.
# 6 each = 12/wk, balancing the heavy JJ gripping and the raw-grip RDLs. This
# circuit is the whole short session.
_WRIST_ROTATION = _reps("Wrist Rotation", reps=15, weight=10, count=6)
_WRIST_EXTENSION = _reps("Wrist Extension", reps=15, weight=15, count=6)
_HIP_CIRCUIT = [_HIP_ADDUCTION, _HIP_ABDUCTION, _WRIST_ROTATION, _WRIST_EXTENSION]

# Neck (machine): flexion (front) / extension (back) / lateral flexion (sides),
# done LAST on Tue/Thu. Grappling-durability prehab. 20 reps @ 30, currently 4
# sets each (12/day). PROGRESSION IS BY SETS: each direction is its own muscle
# (flexors / extensors / lateral flexors don't cross-train), so ramp toward 6
# sets each per session = 12/wk PER DIRECTION -- the 12-set floor applied to each,
# same as the plan's other accessories. Add a set per direction every week or two,
# gated by DELAYED soreness (the neck's tissue lags, a tweak flares a day or two
# later, and it's already stressed by the JJ you just did). Hold 20 reps @ 30
# through the volume ramp; layer load (double progression: reps to ~35, then the
# smallest weight bump, reset reps -- patiently) only once each direction sits at
# 12/wk and feels easy. Lateral is one set = BOTH sides (per-side counts once), so
# 6 lateral sets = 12/wk per side. The tool lumps all neck into one "Neck" number,
# so it reads ~36 at target -- fine, that's 12 per real muscle.
_NECK_FLEXION = _reps("Neck Flexion", reps=20, weight=30, count=4)
_NECK_EXTENSION = _reps("Neck Extension", reps=20, weight=30, count=4)
_NECK_LATERAL = _reps("Neck Lateral Flexion", reps=40, weight=30, count=4)
_NECK_BLOCK = [_NECK_FLEXION, _NECK_EXTENSION, _NECK_LATERAL]


@dataclass
class Day:
    """One training day: a name suffix and its ordered list of blocks."""

    suffix: str
    blocks: list[list[Move]] = field(default_factory=list)

    @property
    def plan_name(self) -> str:
        """Full workout Name as shown in FitNotes."""
        return f"{PLAN_PREFIX} - {self.suffix}"


def _days() -> list[Day]:
    """Build the five-day program (Mon/Wed/Fri full, Tue/Thu short post-JJ)."""
    monday = Day(
        "Monday",
        [
            # RDL on a fresh back, with stretches riding the rest at the platform.
            [_RDL, _COUCH],
            # Leg superset (leg press / curl / split squat), 3 rounds.
            list(_LEG_SUPERSET),
            # Hyper + calf + tibialis + cuff (all adjacent machines/cables).
            list(_HYPER_BLOCK),
        ],
    )
    tuesday = Day("Tuesday", [list(_HIP_CIRCUIT), list(_NECK_BLOCK)])
    wednesday = Day(
        "Wednesday",
        [
            # SS1: stretch -> ham curl -> leg press. The couch stretch is split
            # into 4 short bouts that lead each round, so a stretch fills every
            # rest and the block finishes on a stretch (couch is one set longer
            # than the press). Warms the hips for the squats -- no RDL block on
            # Wednesday to stretch during.
            [_COUCH_WED, _CURL, _LEG_PRESS],
            # SS2: tib/calf lead (rest each hyper); the split squat is LAST and
            # ramps one set per round (0 -> 50 -> 90 -> 90), with a bodyweight
            # warm-up on top. No RDL mid-week -- the back rests before Thursday JJ,
            # and nothing needs a hinge warm-up (the hypers are light).
            [_TIB, _CALF, _HYPER, _EXT_ROTATION, _SPLIT_SQUAT_WED],
        ],
    )
    thursday = Day("Thursday", [list(_HIP_CIRCUIT), list(_NECK_BLOCK)])
    friday = Day(
        "Friday",
        [
            # RDL with stretches at the platform (mirrors Monday).
            [_RDL, _COUCH],
            # Leg superset, 3 rounds (split squat carries an extra warm-up rung).
            list(_LEG_SUPERSET_FRI),
            # Hyper + calf + tibialis + cuff.
            list(_HYPER_BLOCK),
            # Elephant walk to finish -- posterior-chain decompression.
            [_hold("Elephant Walk", 240)],
        ],
    )
    return [monday, tuesday, wednesday, thursday, friday]


DAYS = _days()

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "wh"


def _build_move(move: Move, mappings: ExerciseMapping) -> dict[str, Any]:
    return build_exercise(
        move.name,
        move.sets,
        mappings,
        focus=move.focus,  # type: ignore[arg-type]
        secondary_focus=move.secondary_focus,  # type: ignore[arg-type]
        warmups=move.warmups,
    )


def build_day(day: Day, mappings: ExerciseMapping) -> dict[str, Any]:
    """Build one day's workout dict from its block definitions.

    Args:
        day: Day definition (suffix + ordered blocks of Moves).
        mappings: ExerciseMapping loaded from the exercises folder.

    Returns:
        Complete workout dict ready to write to a .fnw file.
    """
    supersets = [
        build_superset([_build_move(move, mappings) for move in block]) for block in day.blocks
    ]
    return build_workout_from_supersets(day.plan_name, supersets)


def build_all(mappings: ExerciseMapping) -> dict[str, dict[str, Any]]:
    """Build all five days, keyed by full plan name."""
    return {day.plan_name: build_day(day, mappings) for day in DAYS}


def main() -> None:
    """Generate the five WH + JJ (2x) days and write them to plans/wh/."""
    parser = argparse.ArgumentParser(description="Generate the WH + JJ (2x) plan")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory to write the .fnw files (default: {_DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    mappings = load_exercise_mappings()
    for name, workout in build_all(mappings).items():
        output_path = args.output_dir / f"{name}.fnw"
        write_workout_file(workout, output_path)
        print(f"Wrote {name} -> {output_path}")


if __name__ == "__main__":
    main()
