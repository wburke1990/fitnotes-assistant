#!/usr/bin/env python3
"""Generate the "WH + JJ (2x)" 5-day/week plan as five .fnw files.

The WH-gym plan for the twice-a-week jujitsu schedule: JJ on Tuesday + Thursday
only, lifting Monday-Friday. This supersedes the older "WH + JJ" plan (wh_jj.py),
which assumed JJ ~5x/week and used all five lifts as short post-JJ sessions.

Now the split is:
  * Mon / Wed / Fri -- FULL lower-body / posterior-chain / back-rehab days
    (not after JJ, so there's time and a fresh back).
  * Tue / Thu -- SHORT sessions right after the JJ class (shower at the gym
    anyway): one dense hip adduction/abduction machine circuit, nothing more.

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
  * Tibialis machine -- rep progression, ~18/wk.

Programming principles (see scripts/programs/README.md):
  * Per-MUSCLE weekly volume >= 12 sets to PROGRESS (add load or reps); secondary
    muscles count 0.5, pooled across every movement. Below 12 is maintenance.
  * LOW BACK is trained Mon/Wed/Fri only -- never on consecutive days (Tue/Thu
    carry no low-back work), and the heavy RDL lands on the two freshest days.
  * With JJ down to 2x/week the old plan's wrist/rotator/neck durability block is
    dropped to keep Tue/Thu short; fold it back into a M/W/F rest if wanted.

Progression targets (>=12 sets/wk): Gluteals (leg press), Hamstrings (RDL +
curl), Back (Lower) (hypers + RDL), Adductors, Abductors (reps only -- machine
maxed), Tibialis (reps). Maintenance: Quadriceps (split squat), Calves.

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


def _reps(name: str, reps: int, weight: int, count: int) -> Move:
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
# until the back is strong enough. 3 rounds on each full day (Mon/Wed/Fri).
_LEG_PRESS = _reps("Leg Press", reps=12, weight=360, count=3)
# Single-leg machine curl, logged as "Hamstring Curl" (same exercise as last
# year, so history carries over). Reps per side; starting 12/side @ 100.
_CURL = _reps("Hamstring Curl", reps=12, weight=100, count=3)
# Quad / knee MAINTENANCE, two DBs at the sides (less low-back demand than a
# barbell front rack). Reps per side; weight = total of both DBs (two 45s = 90).
# Round 1 is a bodyweight on-ramp; rounds 2-3 are the working sets.
_SPLIT_SQUAT = Move(
    "ATG Split Squat",
    [SetConfig(reps=12, weight=0), SetConfig(reps=12, weight=90), SetConfig(reps=12, weight=90)],
)
# Bodyweight hyperextension -- the rehab progression driver, in the leg superset
# on Mon/Wed/Fri (3 each = 9; +RDL erectors -> low back ~13). The 1-leg +
# curved-back leading reps and the flat-machine static-hold restart are in the
# companion note.
_HYPER = _reps("Hyperextension", reps=35, weight=0, count=3)
# The Mon/Wed/Fri leg superset, run 3 rounds.
_LEG_SUPERSET = [_LEG_PRESS, _CURL, _SPLIT_SQUAT, _HYPER]

# Tibialis progresses by reps (light fixed load). 3 in the Mon/Fri RDL rest,
# 6 on each short day (rides the hip circuit) = ~18/wk.
_TIB = _reps("Tibialis Raise", reps=25, weight=20, count=3)
_TIB_SHORT = _reps("Tibialis Raise", reps=25, weight=20, count=6)
# Maintenance calf, 2 sets on Friday.
_CALF = _reps("Seated Calf Raise", reps=20, weight=90, count=2)
# Quad stretch (per side, 2 min), riding the RDL rest to prep the split squats --
# 2 sides x 120s logged as one set (counts once for volume).
_COUCH = Move(
    "Couch Stretch",
    [SetConfig(reps=2, weight=120), SetConfig(reps=2, weight=120)],
    secondary_focus="time",
)

# Adductor can still take load; abductor is maxed at the machine's 140 ceiling,
# so it progresses by reps only. 6 rounds each on Tue/Thu = 12/wk each. The whole
# short session is this one dense antagonist machine circuit + tibialis filler.
_HIP_ADDUCTION = _reps("Hip Adduction", reps=10, weight=110, count=6)
_HIP_ABDUCTION = _reps("Hip Abduction", reps=12, weight=140, count=6)
_HIP_CIRCUIT = [_HIP_ADDUCTION, _HIP_ABDUCTION, _TIB_SHORT]


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
            # RDL on a fresh back, with tibialis + the quad stretch in its rest.
            [_RDL, _TIB, _COUCH],
            # Leg superset, 3 rounds.
            list(_LEG_SUPERSET),
        ],
    )
    tuesday = Day("Tuesday", [list(_HIP_CIRCUIT)])
    wednesday = Day(
        "Wednesday",
        [
            # Leg superset only -- no low-back-heavy RDL mid-week.
            list(_LEG_SUPERSET),
        ],
    )
    thursday = Day("Thursday", [list(_HIP_CIRCUIT)])
    friday = Day(
        "Friday",
        [
            # RDL with calf + tibialis + quad stretch (mirrors Monday, +calf).
            [_RDL, _CALF, _TIB, _COUCH],
            # Leg superset, 3 rounds.
            list(_LEG_SUPERSET),
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
