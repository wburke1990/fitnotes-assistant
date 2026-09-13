#!/usr/bin/env python3
"""Generate the "CHI" 5-day/week plan as five .fnw files.

The first plan written for the CHICAGO home gym. Everything else under plans/ is
a travel gym: plans/wh/ is the machine gym, and plans/pit/ (with its duplicate
plans/pa/) plus plans/back_rehab/ and plans/back_rehab_jj/ are all Pittsburgh.

Context this plan is built for:
  * Lifting Monday-Friday, up to ~90 min a session. No weekends.
  * NO jujitsu for the first month back. That makes month one the highest-quality
    lifting window of the block: no grappling soreness, no recovery tax, and no
    delayed-soreness gate on the neck ramp.

Three progressions DRIVE the block (the user's own pick); everything else is held
at a maintenance dose:
  1. LOW BACK -- the hyperextension ladder, now on the one-legged CURVED-BACK
     variant, ramping reps toward 3 sets x 35 per side before any load goes on.
  2. ADDUCTORS -- side-lying hyperextension adductor raises, same reps-then-load
     structure, starting from 8 per side.
  3. FRONT RACK SPLIT SQUAT -- a linear load ramp, +5 lb/week from 70 to 135
     (13 weeks). The goal is not the 135 itself: it is to earn a MAINTENANCE
     weight worth holding. Strength is kept by training at the same load, not
     the same volume, so a heavier maintenance weight preserves more ability.

Structure (Mon/Wed/Fri = back days, Tue/Thu = leg days):
  * Low back is trained Mon/Wed/Fri only -- never on consecutive days. The heavy
    snatch-grip RDL lands Mon + Fri (the freshest backs); Wednesday carries no
    hinge at all.
  * The front rack split squat runs Tue/Thu heavy plus a lighter PAUSED exposure
    on Wednesday. The pause (3-5 s at full depth) is the end-range strength work:
    the lift is limited by strength in the deep position, not by the rack, so
    depth and pause time progress alongside load.
  * One heavy-slow HAMSTRING TENDON slot, Tue/Thu: cable leg curl (ankle strap on
    the low row), 5 x 5 at a 6RM, 3 s down / 3 s up. Tendon adaptation is driven
    by strain magnitude held ~3 s, and saturates at a low volume -- so this stays
    5 sets and never becomes a hypertrophy block.
  * Upper body is explicitly NOT a priority: it rides the rest between the
    driving sets, as the filler inside each superset.

Volume model (see scripts/programs/README.md): a muscle needs >=12 sets/week
(secondaries at 0.5, pooled) to be PROGRESSED. Below 12 is maintenance.
Progression targets here: Back (Lower), Adductors, Quadriceps, Hamstrings,
Tibialis. Deliberately held at maintenance: Abductors (cable, load kept high),
Calves, Pectorals, Deltoids, Latissimus Dorsi, Hip Flexors.

Weights are starting targets -- adjust in FitNotes. The progression detail lives
in the companion note (a .fnw has no notes field):
plans/chi/CHI - progression notes.txt

Usage:
    uv --directory scripts run python -m programs.chi_block
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

PLAN_PREFIX = "CHI"


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


def _hold(name: str, seconds: int, count: int = 1) -> Move:
    """A whole-body timed hold (Primary = seconds)."""
    return Move(name, [SetConfig(reps=seconds) for _ in range(count)], focus="time")


# --- Per-side recording convention -------------------------------------------
# Sided moves are recorded as TOTAL reps across both sides, logged as ONE set per
# round. Two metrics stay honest that way: SET-count volume (the 12-set floor)
# counts sets, so one set per round keeps a per-side move from double-counting;
# TONNAGE (reps x weight x sets) needs the full rep count, so per-side reps would
# halve it. Weights stay per-side / what is actually on the bar.

# --- The three drivers --------------------------------------------------------

# 1. LOW BACK. One-legged CURVED-BACK hyperextension on the 45-degree bench --
# the rung above the one-legged work finished at the machine gym (whose bench is
# flat, and therefore harder: peak load lands at full extension rather than
# partway down, so the flat-bench work transfers favourably here). Ramp reps to
# 35 PER SIDE for 3 sets before adding any load. Starting 5/side = 10 total.
# 3 sets x 3 days = 9 direct; the RDL's erectors carry the rest of the floor.
_HYPER = _reps("Hyperextension", reps=10, weight=0, count=3)

# 2. ADDUCTORS. Side-lying hyperextension adductor raise, same bench. Same
# reps-then-load structure: currently 8 per side (= 16 total), ramp reps first.
# 4 sets x 3 days = 12/wk, clearing the floor on its own.
_SIDE_HYPER = _reps("Side-Lying Hyperextension Adductor Raise", reps=16, weight=0, count=4)

# 3. FRONT RACK SPLIT SQUAT. Barbell, +5 lb/week, 70 -> 135 over 13 weeks.
# 12 reps/side = 24 total. Warm-ups (bodyweight, then the empty bar) are stored
# as warm-up sets, so they add session time but not working volume.
_SPLIT_WARMUPS = [SetConfig(reps=24, weight=0), SetConfig(reps=24, weight=45)]
_SPLIT_SQUAT_HEAVY = Move(
    "Front Rack Split Squat",
    [SetConfig(reps=24, weight=70) for _ in range(4)],
    warmups=list(_SPLIT_WARMUPS),
)
# Wednesday: the PAUSED exposure. Lighter load, 3-5 s held at full depth. The
# limiter on this lift is strength in the deep position, so pause time and depth
# progress alongside the Tue/Thu load. Counted volume -- it is real work.
_SPLIT_SQUAT_PAUSED = Move(
    "Front Rack Split Squat",
    [SetConfig(reps=16, weight=50) for _ in range(3)],
    warmups=[SetConfig(reps=24, weight=0)],
)

# --- Supporting lifts ---------------------------------------------------------

# Snatch-grip RDL, NO straps (grip trained raw). HELD STEADY at 155 while the
# hypers progress; the ceiling for this gym is 300 (past that means buying
# plates, and 300 is well past what the back needs). Mon + Fri only.
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

# The hamstring TENDON slot: cable leg curl off the low row with the ankle strap.
# 5 sets x 5 reps/side (= 10 total) at a 6RM, 3 s down / 3 s up. Toes turned OUT
# to bias biceps femoris, whose distal tendon shares the fibular head with the
# LCL. Stays at 5 sets: tendon adaptation saturates at roughly a minute of
# high-strain time per session, so more volume buys nothing and costs recovery.
# Tue/Thu only -- heavy loading leaves a tendon in net collagen breakdown for
# about a day, so it wants every-other-day, not daily.
_CABLE_CURL = _reps("Cable Leg Curl", reps=10, weight=50, count=5)

# Abductors: MAINTENANCE, not a driver. Cable abduction with the ankle strap,
# 3 sets x 2 days = 6/wk. Keep the LOAD high -- strength is maintained by
# training at the same weight, not the same volume, so a light maintenance dose
# only works if it stays heavy.
_ABDUCTION = _reps("Cable Hip Abduction", reps=24, weight=60, count=3)

# QL raise -- lateral trunk, Wednesday only (the hinge-free back day).
_QL_RAISE = _reps("QL Raise", reps=16, weight=0, count=3)

# Tibialis on the tib bar, one-legged (the harder version). 35/side = 70 total,
# 4 sets x 3 days = 12/wk, its progression floor.
_TIB = _reps("Tibialis Raise", reps=70, weight=25, count=4)
# Calves: maintenance, kettlebell in hand. 35/side = 70 total.
_CALF = _reps("Standing Calf Raise", reps=70, weight=35, count=3)

# Hip/quad mobility opening the leg days, warming the deep position the split
# squat is limited by. 2 sides x 120 s logged as one set.
_COUCH = Move(
    "Couch Stretch",
    [SetConfig(reps=2, weight=120) for _ in range(2)],
    secondary_focus="time",
)

# --- Upper body: rest-filler, not a priority ----------------------------------
# Every one of these rides the rest between the driving sets. Low counts on
# purpose -- they are maintenance for a gym that finally has pulling again.
_INCLINE = _reps("Barbell Incline Bench Press", reps=8, weight=135, count=3)
_RING_DIP = _reps("Ring Dip", reps=8, weight=0, count=3)
# Handstand push-up ramp -- currently around 80 degrees off the parallettes.
_HSPU = _reps("Handstand Push-Up", reps=5, weight=0, count=3)
_PULLDOWN = _reps("Lat Pulldown", reps=10, weight=120, count=3)
_LOW_ROW = _reps("Low Row", reps=10, weight=120, count=3)
_FACE_PULL = _reps("Face Pull", reps=15, weight=40, count=3)
# Compression / hip flexors off the same parallettes, 30 s holds.
_L_SIT = _hold("L-Sit", 30, count=3)

# Neck (harness on the cable). Front / back / sides, 20 reps @ 30, 4 sets each on
# Tue/Thu. PROGRESSION IS BY SETS: each direction is its own muscle, so each gets
# its own 12-set weekly floor -- ramp to 6 sets/session per direction. The gate is
# normally DELAYED soreness landing on a jujitsu day; with no jujitsu in month
# one that gate is gone, so this is the month to ramp it fast. Lateral is one set
# = BOTH sides, so its reps are the total (40).
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
    """Build the five-day program (Mon/Wed/Fri back, Tue/Thu legs)."""
    monday = Day(
        "Monday",
        [
            # RDL on a fresh back; the pulldown fills the rest (non-interfering).
            [_RDL, _PULLDOWN],
            # The hyper gets its own block so the side hyper is never stacked
            # straight onto it -- same bench, and the trunk needs the rest.
            # Incline + tib are the filler.
            [_HYPER, _INCLINE, _TIB],
            # Side hyper with upper-body and calf filler.
            [_SIDE_HYPER, _FACE_PULL, _CALF],
        ],
    )
    tuesday = Day(
        "Tuesday",
        [
            # Open on the stretch -- the split squat is limited by the deep
            # position, so the hips get warmed before it, not after.
            [_COUCH, _LOW_ROW],
            # The heavy front rack ramp, with compression + dips as filler.
            [_SPLIT_SQUAT_HEAVY, _L_SIT, _RING_DIP],
            # Tendon slot + abductor maintenance, both off the ankle strap.
            [_CABLE_CURL, _ABDUCTION],
            # Neck last.
            list(_NECK_BLOCK),
        ],
    )
    wednesday = Day(
        "Wednesday",
        [
            # No hinge at all on Wednesday -- the back's mid-week rest.
            [_HYPER, _HSPU, _TIB],
            # The paused split squat: end-range strength for the deep position.
            [_SPLIT_SQUAT_PAUSED, _PULLDOWN, _CALF],
            [_SIDE_HYPER, _FACE_PULL, _QL_RAISE],
        ],
    )
    thursday = Day(
        "Thursday",
        [
            [_COUCH, _LOW_ROW],
            [_SPLIT_SQUAT_HEAVY, _L_SIT, _INCLINE],
            [_CABLE_CURL, _ABDUCTION],
            list(_NECK_BLOCK),
        ],
    )
    friday = Day(
        "Friday",
        [
            [_RDL, _PULLDOWN],
            [_HYPER, _RING_DIP, _TIB],
            [_SIDE_HYPER, _FACE_PULL, _CALF],
            # Posterior-chain decompression to finish the week.
            [_hold("Elephant Walk", 240)],
        ],
    )
    return [monday, tuesday, wednesday, thursday, friday]


DAYS = _days()

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "chi"


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
    """Generate the five CHI days and write them to plans/chi/."""
    parser = argparse.ArgumentParser(description="Generate the CHI plan")
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
