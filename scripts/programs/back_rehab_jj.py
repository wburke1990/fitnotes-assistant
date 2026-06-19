#!/usr/bin/env python3
"""Generate the "Back Rehab + JJ" 3-day/week plan as three .fnw files.

A back-rehab block (RDL / Nordic / Hyperextension posterior chain) layered with
adductor and ankle/knee (JJ) work plus per-day prehab drills. Three sessions:

    Sunday   - quad/calf JJ emphasis, ATG split-squat working sets
    Tuesday  - adductor + calf circuits, hip prehab
    Thursday - adductor + tibialis circuits, lateral-hip prehab

Each session is a set of supersets (blocks), mirroring Back Rehab 1.

Encoding notes (see scripts/programs/README.md):
  * Normal lifts: SetConfig(reps, weight), default focus="reps".
  * Timed holds (whole body): SetConfig(reps=seconds), focus="time".
  * Per-side timed holds: SetConfig(reps=2 sides, weight=seconds),
    focus="reps", secondary_focus="time" (counts once for volume).
  * WEIGHTED Copenhagen Plank: the schema's Secondary field holds a single
    measure, so a hold cannot store both load AND seconds. We preserve the
    added load: SetConfig(reps=2 sides, weight=lb), focus="reps",
    secondary_focus="weight". The (short) hold duration lives only in the
    plan notes here, not the .fnw.

Usage:
    uv --directory scripts run python -m programs.back_rehab_jj
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

PLAN_PREFIX = "Back Rehab + JJ"

_MINUTE = 60
_SIDES = 2


@dataclass
class Move:
    """One exercise within a superset, with its set configs and focus mode."""

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


def _per_side_hold(name: str, seconds: int) -> Move:
    """A per-side timed hold logged as one set of 2 sides x seconds."""
    return Move(
        name,
        [SetConfig(reps=_SIDES, weight=seconds)],
        focus="reps",
        secondary_focus="time",
    )


def _weighted_copenhagen(load_lb: int, count: int) -> Move:
    """Weighted Copenhagen Plank: 2 sides x load lb, preserving the load.

    The hold is short; the .fnw schema cannot store both load and a timed
    duration, so we keep the added weight and drop the seconds.
    """
    return Move(
        "Copenhagen Plank",
        [SetConfig(reps=_SIDES, weight=load_lb) for _ in range(count)],
        focus="reps",
        secondary_focus="weight",
    )


@dataclass
class Day:
    """One training day: a name suffix and its ordered list of supersets."""

    suffix: str
    blocks: list[list[Move]] = field(default_factory=list)

    @property
    def plan_name(self) -> str:
        """Full workout Name as shown in FitNotes."""
        return f"{PLAN_PREFIX} - {self.suffix}"


# --- Shared move builders (reuse Back Rehab 1-3 configs) ---------------------

_RDL = _reps("Snatch-Grip Stiff-Legged RDL", reps=8, weight=135, count=3)
_NORDIC = _reps("Nordic Hamstring Curl", reps=12, weight=0, count=3)
_HYPER = _reps("Hyperextension", reps=35, weight=0, count=3)
_CALF = _reps("Standing Calf Raise", reps=70, weight=20, count=2)
_TIB = _reps("Tibialis Raise", reps=35, weight=0, count=2)
_ADDUCTOR = _reps("Side-Lying Hyperextension Adductor Raise", reps=7, weight=0, count=2)
_COUCH = _per_side_hold("Couch Stretch", 2 * _MINUTE)

# Weighted Copenhagen used as activation before the adductor raise (2 sets).
_COPENHAGEN = _weighted_copenhagen(load_lb=25, count=2)


def _days() -> list[Day]:
    """Build the three-day program definition."""
    sunday = Day(
        "Sunday",
        [
            [_RDL, _COUCH],
            [
                _NORDIC,
                _hold("Yoga", 2 * _MINUTE),
                _reps("ATG Split Squat", reps=12, weight=0, count=1),
                _reps("ATG Split Squat", reps=12, weight=45, count=1),
                _CALF,
            ],
            [
                _HYPER,
                _reps("ATG Split Squat", reps=12, weight=70, count=4),
                _TIB,
            ],
        ],
    )
    tuesday = Day(
        "Tuesday",
        [
            # SS1: Tibialis sits next to the grip-heavy RDL (grip relief);
            # Copenhagen stays here, adductor raise stays out.
            [
                _RDL,
                _COPENHAGEN,
                _TIB,
                _per_side_hold("Hip Internal Rotation", 2 * _MINUTE),
            ],
            # SS2: calf moves here alongside the adductor raise.
            [
                _NORDIC,
                _ADDUCTOR,
                _CALF,
                _per_side_hold("Hip Airplane", 2 * _MINUTE),
            ],
            # SS3: adductor raise listed BEFORE the regular hyperextension
            # (heavier/less-stable movement first); tibialis added here too.
            [
                _ADDUCTOR,
                _HYPER,
                _CALF,
                _TIB,
                _hold("Plank", 4 * _MINUTE),
            ],
        ],
    )
    thursday = Day(
        "Thursday",
        [
            # SS1: Tibialis sits next to the grip-heavy RDL (grip relief);
            # Copenhagen stays here, adductor raise stays out.
            [
                _RDL,
                _COPENHAGEN,
                _TIB,
                _per_side_hold("Side Hip Abduction", 2 * _MINUTE),
            ],
            # SS2: calf moves here alongside the adductor raise.
            [
                _NORDIC,
                _ADDUCTOR,
                _CALF,
                _hold("Wall Back Extension", 4 * _MINUTE),
            ],
            # SS3: adductor raise listed BEFORE the regular hyperextension
            # (heavier/less-stable movement first); tibialis added here too.
            [
                _ADDUCTOR,
                _HYPER,
                _CALF,
                _TIB,
                _per_side_hold("QL Plank", 2 * _MINUTE),
            ],
        ],
    )
    return [sunday, tuesday, thursday]


DAYS = _days()

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "back_rehab_jj"


def _build_move(move: Move, mappings: ExerciseMapping) -> dict[str, Any]:
    return build_exercise(
        move.name,
        move.sets,
        mappings,
        focus=move.focus,  # type: ignore[arg-type]
        secondary_focus=move.secondary_focus,  # type: ignore[arg-type]
    )


def build_day(day: Day, mappings: ExerciseMapping) -> dict[str, Any]:
    """Build one day's workout dict from its superset definitions.

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
    """Generate the three Back Rehab + JJ days and write them to plans/."""
    parser = argparse.ArgumentParser(description="Generate the Back Rehab + JJ plan")
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
