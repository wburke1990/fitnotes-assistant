#!/usr/bin/env python3
"""Generate the "WH + JJ" 5-day/week plan as five .fnw files.

A short post-jujitsu lift for the WH gym stint: JJ ~5x/week (weekdays) covers
the upper-body pulling/pressing/grip, so the lift is lower body, posterior
chain, and back rehab on WH's machines. Five weekday sessions, no weekends.

Programming principles (see scripts/programs/README.md):
  * Per-MUSCLE weekly volume >= 12 sets is required to PROGRESS a muscle
    (add load or reps); below 12 is fine for maintenance only. Secondary
    muscles count 0.5. Sets/session for a target = 12 / weekly frequency.
  * High frequency, low per-session volume, so DOMS never accumulates enough
    to compromise the next day's rolling (there are no rest days mid-week).
  * RDL is held steady at 155 while the hyperextension progression is the focus.
    RDL + hypers feed the same posterior chain, so the low back clears its floor
    (9 hyper sets + the RDL's erectors) even with the RDL not advancing.
  * Supersets pair only non-interfering movements. RDL is grip/spine/hamstring
    limited, so it pairs only with grip-free, non-competing fillers (tibialis,
    calf) and its heavy Friday set stays straight. Hyperextension is always
    straight and last (it leaves the low back acutely weak), with nothing
    spine-loading after it.

Progression targets (>=12 sets/wk): Gluteals (leg press), Hamstrings (RDL +
single-leg curl), Adductors, Abductors (reps only -- machine maxed at 140),
Tibialis (reps). Maintenance (<12): quads (split squat), calves, core.

RDL is snatch-grip with NO straps (grip trained raw). The hyperextension
progression detail lives in the companion note (the .fnw has no notes field):
    plans/wh/WH + JJ - progression notes.txt

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
    """One exercise within a block, with its set configs and focus mode."""

    name: str
    sets: list[SetConfig]
    focus: str = "reps"
    secondary_focus: str = "weight"


def _reps(name: str, reps: int, weight: int, count: int) -> Move:
    """A normal reps/weight lift repeated `count` sets."""
    return Move(name, [SetConfig(reps=reps, weight=weight) for _ in range(count)])


def _hold(name: str, seconds: int) -> Move:
    """A whole-body timed hold (Primary = seconds)."""
    return Move(name, [SetConfig(reps=seconds)], focus="time")


# --- Shared moves. Weights are starting targets, adjustable in FitNotes. ------

# Gluteal-biased leg press (feet high, deep stretch) -- can't squat for glutes
# until the back is stronger, so the leg press covers glutes here.
_LEG_PRESS = _reps("Leg Press", reps=12, weight=360, count=4)
# Single-leg machine curl -- logged as "Hamstring Curl" last year (same
# exercise, so the history carries over). Replaces the Nordic curl: far lower
# DOMS, which matters with JJ every day. Reps are per side; starting 12/side
# @ 90. 4 sets = 4 per leg.
_CURL = _reps("Hamstring Curl", reps=12, weight=90, count=4)
# Quad / knee maintenance -- the feet-high leg press is deliberately glute-biased
# and won't cover the quads. Done with two DBs held at the sides (WH's big
# dumbbells): less low-back demand than a barbell front rack. NEW convention this
# year: reps are logged PER SIDE and weight PER DUMBBELL -- starting 12/side with
# the 45s. (Last year used totals: the top was two 60s for 10 total = 5/side.)
_SPLIT_SQUAT = _reps("ATG Split Squat", reps=12, weight=45, count=2)
# Rep-progression filler; sits in the rest of the main lift (~free volume).
_TIB = _reps("Tibialis Raise", reps=25, weight=20, count=3)
# Maintenance filler.
_CALF = _reps("Seated Calf Raise", reps=20, weight=90, count=2)
# Adductor can still take load; abductor is maxed at the machine's 140, so it
# progresses by reps only.
_HIP_ADDUCTION = _reps("Hip Adduction", reps=10, weight=110, count=6)
_HIP_ABDUCTION = _reps("Hip Abduction", reps=12, weight=140, count=6)
# Bodyweight; the 1-leg + curved-back reps that lead the first sets, and the
# flat-machine 1-leg static-hold restart, are described in the companion note.
_HYPER = _reps("Hyperextension", reps=35, weight=0, count=3)


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
            # SS1: leg press paired with the single-leg curl (non-competing).
            [_LEG_PRESS, _CURL],
            # SS2: split-squat maintenance with tibialis as the filler.
            [_SPLIT_SQUAT, _TIB],
            # Hyperextension: its own block, last, nothing spine-loading after.
            [_HYPER],
        ],
    )
    tuesday = Day(
        "Tuesday",
        [
            # SS1: moderate RDL with tibialis (grip-free) in the rest.
            [_reps("Snatch-Grip Stiff-Legged RDL", reps=8, weight=155, count=4), _TIB],
            # SS2: adductor / abductor antagonist pair (the hip machine floor).
            [_HIP_ADDUCTION, _HIP_ABDUCTION],
        ],
    )
    wednesday = Day(
        "Wednesday",
        [
            [_LEG_PRESS, _CURL],
            [_SPLIT_SQUAT, _TIB],
            [_HYPER],
        ],
    )
    thursday = Day(
        "Thursday",
        [
            # SS1: adductor / abductor antagonist pair.
            [_HIP_ADDUCTION, _HIP_ABDUCTION],
            # SS2: calf maintenance with tibialis filler.
            [_CALF, _TIB],
            # Core rehab: each its own block (quick, straight).
            [_hold("Side Plank", 80)],
            [_reps("QL Raise", reps=20, weight=0, count=3)],
            [_reps("Slow Scissors", reps=30, weight=0, count=1)],
        ],
    )
    friday = Day(
        "Friday",
        [
            # RDL held steady at 155 (progression is on the hypers now), paired
            # with calf (non-competing) in the rest.
            [_reps("Snatch-Grip Stiff-Legged RDL", reps=8, weight=155, count=4), _CALF],
            # Leg press its own block after the RDL.
            [_LEG_PRESS],
            # Hyperextension last.
            [_HYPER],
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
