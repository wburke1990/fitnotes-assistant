#!/usr/bin/env python3
"""Generate the "WH + JJ" 5-day/week plan as five .fnw files.

A short post-jujitsu lift for the WH gym stint: JJ ~5x/week (weekdays) covers
the upper-body pulling/pressing/grip, so the lift is lower body, posterior
chain, and back rehab on WH's machines. Five weekday sessions, no weekends.

Programming principles (see scripts/programs/README.md):
  * Per-MUSCLE weekly volume >= 12 sets is required to PROGRESS a muscle
    (add load or reps); below 12 is fine for maintenance. Secondary muscles
    count 0.5, pooled across every movement.
  * LOW BACK IS CLUSTERED ONTO MON/WED/FRI and rested Tue/Thu (+ weekend), so it
    is never trained on consecutive days. RDL lands Mon and Fri only -- the two
    freshest back days (after the weekend, and before it) -- never on a
    pre-fatigued back.
  * The leg superset (leg press + curl + split squat + hyperextension) runs 3
    rounds on Mon/Wed/Fri. Every floor still clears with margin, so the 4th
    round isn't needed and the sessions stay short. Hyper sits IN this superset
    (paired with the leg work), which is how it was actually trained last year.
  * Hip adduction/abduction (6 rounds) pair with wrist prehab on Tue/Thu; calf,
    tibialis, and rotator-cuff external rotation fill the second Tue/Thu block.
  * RDL warm-ups (empty-bar ramp) are stored as warm-up sets, so they add gym
    time but NOT working volume -- the floors are unaffected.

Progression targets (>=12 sets/wk): Gluteals (leg press), Hamstrings (RDL +
curl), Adductors, Abductors (reps only -- machine maxed at 140), Tibialis
(reps), low back (hypers). Maintenance: quads (split squat), calves, rotator
cuff. Wrist prehab runs 12/wk each side (rotation + extension).

RDL is snatch-grip with NO straps (grip trained raw). Band neck prehab (flexion
+ extension) rides the Tue/Thu accessory block -- start light, it's new. The
hyperextension progression detail lives in the companion note (the .fnw has no
notes field): plans/wh/WH + JJ - progression notes.txt

Usage:
    uv --directory scripts run python -m programs.wh_jj
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

PLAN_PREFIX = "WH + JJ"


@dataclass
class Move:
    """One exercise within a block: its working sets, focus mode, and warm-ups."""

    name: str
    sets: list[SetConfig]
    focus: str = "reps"
    secondary_focus: str = "weight"
    warmups: list[SetConfig] = field(default_factory=list)


def _reps(name: str, reps: int, weight: int, count: int) -> Move:
    """A normal reps/weight lift repeated `count` sets."""
    return Move(name, [SetConfig(reps=reps, weight=weight) for _ in range(count)])


def _hold(name: str, seconds: int) -> Move:
    """A whole-body timed hold (Primary = seconds)."""
    return Move(name, [SetConfig(reps=seconds)], focus="time")


# --- Shared moves. Weights are starting targets, adjustable in FitNotes. ------

# Gluteal-biased leg press (feet high, deep stretch) -- can't squat for glutes
# until the back is stronger, so the leg press covers glutes here.
_LEG_PRESS = _reps("Leg Press", reps=12, weight=360, count=3)
# Single-leg machine curl -- logged as "Hamstring Curl" (same exercise as last
# year, so history carries over). Reps per side; starting 12/side @ 100.
_CURL = _reps("Hamstring Curl", reps=12, weight=100, count=3)
# Quad / knee maintenance, two DBs held at the sides (less low-back demand than a
# barbell front rack). Reps per side; weight = total of both DBs (two 45s = 90).
# Round 1 is a bodyweight on-ramp; rounds 2-3 are the working sets.
_SPLIT_SQUAT = Move(
    "ATG Split Squat",
    [SetConfig(reps=12, weight=0), SetConfig(reps=12, weight=90), SetConfig(reps=12, weight=90)],
)
# Bodyweight hyperextension -- the rehab centerpiece, in the leg superset (how it
# was trained last year). The 1-leg + curved-back reps that lead the first sets,
# and the flat-machine 1-leg static-hold restart, are in the companion note.
_HYPER = _reps("Hyperextension", reps=35, weight=0, count=3)
# The Mon/Wed/Fri leg superset, run 3 rounds.
_LEG_SUPERSET = [_LEG_PRESS, _CURL, _SPLIT_SQUAT, _HYPER]

# RDL: snatch-grip, no straps, held steady at 155. Warm-up ramp (empty bar x2,
# 95, 135) is stored as warm-up sets, so it adds time but not working volume.
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

# Rep-progression target, fed into the rests. 3 sets on Mon/Tue/Thu/Fri = 12/wk.
_TIB = _reps("Tibialis Raise", reps=25, weight=20, count=3)
# Maintenance filler, 2 sets on Tue/Thu/Fri = 6/wk.
_CALF = _reps("Seated Calf Raise", reps=20, weight=90, count=2)
# Rotator-cuff prehab (shoulder health) -- rides the Tue/Thu calf/tib block.
_EXT_ROTATION = _reps("Cable External Rotation", reps=15, weight=12, count=3)
# Band neck prehab -- the biggest durability gap for 5x/week grappling. New to
# it, so start conservative (2 sets each) and build up; flexion + extension cover
# the sagittal plane (guillotine / crank defense), add lateral later.
_NECK_FLEXION = _reps("Band Neck Flexion", reps=15, weight=0, count=2)
_NECK_EXTENSION = _reps("Band Neck Extension", reps=15, weight=0, count=2)
# Quad stretch (per side, 2 min), riding the RDL rest on Mon/Fri to prep the
# split squats -- 2 sides x 120s logged as one set.
_COUCH = Move(
    "Couch Stretch",
    [SetConfig(reps=2, weight=120), SetConfig(reps=2, weight=120)],
    secondary_focus="time",
)

# Adductor can still take load; abductor is maxed at the machine's 140 ceiling,
# so it progresses by reps only. 6 rounds each on Tue/Thu = 12/wk.
_HIP_ADDUCTION = _reps("Hip Adduction", reps=10, weight=110, count=6)
_HIP_ABDUCTION = _reps("Hip Abduction", reps=12, weight=140, count=6)
# Wrist prehab, one of each every round of the 6-round hip superset -> 6/session,
# 12/wk each. Anti-flexion (extensors) + rotation balance the heavy gripping from
# JJ and the raw-grip RDLs, keeping the wrists and elbows healthy.
_WRIST_ROTATION = _reps("Wrist Rotation", reps=15, weight=10, count=6)
_WRIST_EXTENSION = _reps("Wrist Extension", reps=15, weight=15, count=6)
_HIP_SUPERSET = [_HIP_ADDUCTION, _HIP_ABDUCTION, _WRIST_ROTATION, _WRIST_EXTENSION]


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
    """Build the five-day program definition (Mon-Fri)."""
    monday = Day(
        "Monday",
        [
            # RDL (fresh back after the weekend) with tibialis + the quad stretch
            # filling its rest. No calf here -- calf lives on Tue/Thu/Fri.
            [_RDL, _TIB, _COUCH],
            # Leg superset, 3 rounds.
            list(_LEG_SUPERSET),
        ],
    )
    tuesday = Day(
        "Tuesday",
        [
            # Hip adduction/abduction (6 rounds) with wrist prehab in the rest.
            list(_HIP_SUPERSET),
            # Calf + tibialis + rotator-cuff external rotation + band neck.
            [_CALF, _TIB, _EXT_ROTATION, _NECK_FLEXION, _NECK_EXTENSION],
        ],
    )
    wednesday = Day(
        "Wednesday",
        [
            # Leg superset only -- the short day, no low-back-heavy RDL.
            list(_LEG_SUPERSET),
        ],
    )
    thursday = Day(
        "Thursday",
        [
            list(_HIP_SUPERSET),
            [_CALF, _TIB, _EXT_ROTATION, _NECK_FLEXION, _NECK_EXTENSION],
        ],
    )
    friday = Day(
        "Friday",
        [
            # RDL with calf + tibialis + quad stretch (mirrors Monday).
            [_RDL, _CALF, _TIB, _COUCH],
            # Leg superset, 3 rounds.
            list(_LEG_SUPERSET),
            # Single Elephant Walk to finish the week.
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
    """Generate the five WH + JJ days and write them to plans/wh/."""
    parser = argparse.ArgumentParser(description="Generate the WH + JJ plan")
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
