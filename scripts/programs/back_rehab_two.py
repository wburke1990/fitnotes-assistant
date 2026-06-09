#!/usr/bin/env python3
"""Generate the "Back Rehab 2" plan as a .fnw file.

A time-based hip rehab circuit from a YouTube routine. Every exercise is a
timed hold, not reps/weight, so each is built with ``focus="time"`` (durations
are stored in seconds). Done as a circuit -- each exercise its own block, in
order -- not as supersets.

Per-side moves are logged as two sets (left then right) of the per-side
duration; whole-body holds are a single set:

    Hip strengthening
        Hip Internal Rotation   2 x 2:00   (per side)
        Hip Airplane            2 x 2:00   (per side)
        Side Hip Abduction      2 x 2:00   (per side)
        Side Hip Adduction      2 x 2:00   (per side)
    Core strengthening
        Hip Flexor Lift         2 x 2:00   (per side)
        QL Plank                2 x 2:00   (per side)
        Plank                   1 x 4:00
        Wall Back Extension     1 x 4:00
    Hip mobility
        Wall Groin Stretch      1 x 4:00
        90 90 Push Up           2 x 2:00   (per side)
        Couch Stretch           2 x 2:00   (per side)
        Elephant Walk           1 x 4:00

The section headers are documentation only -- a .fnw plan has no notes field.

Usage:
    uv --directory scripts run python -m programs.back_rehab_two
"""

import argparse
from pathlib import Path
from typing import Any

from common import (
    build_exercise,
    build_workout,
    load_exercise_mappings,
    write_workout_file,
)
from common.builders import SetConfig
from common.io import ExerciseMapping

PLAN_NAME = "Back Rehab 2"

_MINUTE = 60

# Performed order: (exercise, seconds per set, number of sets). Per-side moves
# are two sets (left, right); whole-body holds are one set.
EXERCISES: list[tuple[str, int, int]] = [
    # Hip strengthening
    ("Hip Internal Rotation", 2 * _MINUTE, 2),
    ("Hip Airplane", 2 * _MINUTE, 2),
    ("Side Hip Abduction", 2 * _MINUTE, 2),
    ("Side Hip Adduction", 2 * _MINUTE, 2),
    # Core strengthening
    ("Hip Flexor Lift", 2 * _MINUTE, 2),
    ("QL Plank", 2 * _MINUTE, 2),
    ("Plank", 4 * _MINUTE, 1),
    ("Wall Back Extension", 4 * _MINUTE, 1),
    # Hip mobility
    ("Wall Groin Stretch", 4 * _MINUTE, 1),
    ("90 90 Push Up", 2 * _MINUTE, 2),
    ("Couch Stretch", 2 * _MINUTE, 2),
    ("Elephant Walk", 4 * _MINUTE, 1),
]

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "back_rehab"


def build_plan(mappings: ExerciseMapping) -> dict[str, Any]:
    """Build the Back Rehab 2 workout dict from the exercise definitions.

    Args:
        mappings: ExerciseMapping loaded from the exercises folder.

    Returns:
        Complete workout dict ready to write to a .fnw file.
    """
    exercises = [
        build_exercise(
            name,
            [SetConfig(reps=seconds) for _ in range(sets)],
            mappings,
            focus="time",
        )
        for name, seconds, sets in EXERCISES
    ]
    return build_workout(PLAN_NAME, exercises)


def main() -> None:
    """Generate Back Rehab 2 and write it to the back_rehab plans folder."""
    parser = argparse.ArgumentParser(description="Generate the Back Rehab 2 plan")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory to write the .fnw file (default: {_DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    mappings = load_exercise_mappings()
    workout = build_plan(mappings)

    output_path = args.output_dir / f"{PLAN_NAME}.fnw"
    write_workout_file(workout, output_path)
    print(f"Wrote {PLAN_NAME} -> {output_path}")


if __name__ == "__main__":
    main()
