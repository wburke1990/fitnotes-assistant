#!/usr/bin/env python3
"""Generate the "WH 3-Day" plan as three .fnw files.

Built around training jujitsu only TWICE a week (Tue + Thu), three lifts total
for the long haul: two SHORT sessions right after the Tue/Thu JJ classes (shower
at the gym anyway), plus one longer standalone session on a non-JJ day -- named
Sunday here, but use any non-JJ day. The WH machines the user doesn't have at
home get the emphasis: the leg press (loaded for glutes), the hip
adduction/abduction machine, and the tibialis ("tip") machine.

Must-hit, per the user:
  * Back-rehab progression CONTINUES -- snatch-grip RDL (heavy, on the fresh
    standalone day only) plus the hyperextension (the low-back progression
    driver, held across all three days). Low back clears the 12-set floor (~13).
  * Hip adduction + abduction machine -- 6 rounds on each short day = 12/wk each.
  * Leg press -- loaded, gluteal-biased; pools to ~20 across the week.
  * Tibialis machine -- 15/wk, rep progression.

Programming principles (see scripts/programs/README.md):
  * Per-MUSCLE weekly volume >= 12 sets to PROGRESS (add load or reps); secondary
    muscles count 0.5, pooled across every movement. Below 12 is maintenance.
  * LOW BACK is trained Sun/Tue/Thu -- none consecutive (Mon, Wed, Fri+Sat rest
    between), so it is never worked on back-to-back days. The heavy RDL lands on
    the fresh standalone day ONLY, never on a post-JJ back; the hypers carry the
    low-back progression on the two short days.
  * The balance/stability work (ATG split squat) stays on the fresh day; the
    post-JJ short days are machine circuits only, so a tired body isn't asked to
    stabilise under load.

Progression targets (>=12 sets/wk): Gluteals (leg press), Hamstrings (RDL +
curl), Back (Lower) (hypers + RDL), Adductors, Abductors (reps only -- machine
maxed), Tibialis (reps). Maintenance: Quadriceps (split squat), Calves (carried
by the leg-press / curl secondaries).

The hyperextension progression detail lives in the companion note (a .fnw has no
notes field): plans/wh/WH 3-Day - progression notes.txt

Usage:
    uv --directory scripts run python -m programs.wh_3day
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

PLAN_PREFIX = "WH 3-Day"


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
# sets, so it adds gym time but NOT working volume. Fresh standalone day only.
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
# until the back is strong enough. 3 rounds on the fresh day, 4 on each short day.
_LEG_PRESS_LONG = _reps("Leg Press", reps=12, weight=360, count=3)
_LEG_PRESS_SHORT = _reps("Leg Press", reps=12, weight=360, count=4)
# Single-leg machine curl, logged as "Hamstring Curl" (same exercise as last
# year, so history carries over). Reps per side; starting 12/side @ 100.
_CURL_LONG = _reps("Hamstring Curl", reps=12, weight=100, count=3)
_CURL_SHORT = _reps("Hamstring Curl", reps=12, weight=100, count=4)
# Quad / knee MAINTENANCE, two DBs at the sides (less low-back demand than a
# barbell front rack). Reps per side; weight = total of both DBs (two 45s = 90).
# Round 1 is a bodyweight on-ramp; rounds 2-3 are the working sets. Fresh day
# only -- balance work stays off the post-JJ (tired) days.
_SPLIT_SQUAT = Move(
    "ATG Split Squat",
    [SetConfig(reps=12, weight=0), SetConfig(reps=12, weight=90), SetConfig(reps=12, weight=90)],
)
# Bodyweight hyperextension -- the rehab progression driver, held across all
# three days (Sun 3 + Tue 4 + Thu 4 = 11; +RDL erectors -> low back ~13). The
# 1-leg + curved-back leading reps and the flat-machine static-hold restart are
# in the companion note.
_HYPER_LONG = _reps("Hyperextension", reps=35, weight=0, count=3)
_HYPER_SHORT = _reps("Hyperextension", reps=35, weight=0, count=4)

# Tibialis progresses by reps (light fixed load). 3 on the fresh day, 6 on each
# short day (rides the hip circuit) = 15/wk.
_TIB_LONG = _reps("Tibialis Raise", reps=25, weight=20, count=3)
_TIB_SHORT = _reps("Tibialis Raise", reps=25, weight=20, count=6)

# Quad stretch (per side, 2 min), riding the RDL rest to prep the split squats --
# 2 sides x 120s logged as one set (counts once for volume).
_COUCH = Move(
    "Couch Stretch",
    [SetConfig(reps=2, weight=120), SetConfig(reps=2, weight=120)],
    secondary_focus="time",
)

# Adductor can still take load; abductor is maxed at the machine's 140 ceiling,
# so it progresses by reps only. 6 rounds each on Tue/Thu = 12/wk each.
_HIP_ADDUCTION = _reps("Hip Adduction", reps=10, weight=110, count=6)
_HIP_ABDUCTION = _reps("Hip Abduction", reps=12, weight=140, count=6)


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
    """Build the three-day program definition (Sunday long + Tue/Thu short)."""
    sunday = Day(
        "Sunday",
        [
            # SS1: heavy RDL on the fresh back, with tibialis + the quad stretch
            # filling its rest.
            [_RDL, _TIB_LONG, _COUCH],
            # SS2: the leg superset, 3 rounds (hyper sits in it, as trained last
            # year). Split squat round 1 is a bodyweight on-ramp.
            [_LEG_PRESS_LONG, _CURL_LONG, _SPLIT_SQUAT, _HYPER_LONG],
            # Elephant walk to finish -- posterior-chain decompression.
            [_hold("Elephant Walk", 240)],
        ],
    )
    short_blocks = [
        # Hip adduction/abduction machine circuit (6 rounds) with tibialis in the
        # rest -- the machines WH has that home doesn't.
        [_HIP_ADDUCTION, _HIP_ABDUCTION, _TIB_SHORT],
        # Leg press + curl + hyperextension circuit (4 rounds). This block is
        # what keeps glutes/hamstrings/low-back at their weekly floors -- the
        # hypers here carry the back rehab on the post-JJ days.
        [_LEG_PRESS_SHORT, _CURL_SHORT, _HYPER_SHORT],
    ]
    tuesday = Day("Tuesday", [list(block) for block in short_blocks])
    thursday = Day("Thursday", [list(block) for block in short_blocks])
    return [sunday, tuesday, thursday]


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
    """Build all three days, keyed by full plan name."""
    return {day.plan_name: build_day(day, mappings) for day in DAYS}


def main() -> None:
    """Generate the three WH 3-Day days and write them to plans/wh/."""
    parser = argparse.ArgumentParser(description="Generate the WH 3-Day plan")
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
