#!/usr/bin/env python3
"""Generate the "Back Rehab 2" plan as a .fnw file.

A time-based hip rehab circuit from a YouTube routine. Done as a circuit --
each exercise its own block, in order -- not as supersets.

Per-side moves are logged as a single set of 2 reps (left, right) x the per-side
hold, so they count as one group-set for volume, not two. The set carries the
side count in Primary (reps focus) and the hold seconds in Secondary (time
focus). Whole-body holds are a single timed-hold set (duration in seconds):

    Hip strengthening
        Hip Internal Rotation   1 x (2 reps x 2:00)   (per side)
        Hip Airplane            1 x (2 reps x 2:00)   (per side)
        Side Hip Abduction      1 x (2 reps x 2:00)   (per side)
        Side Hip Adduction      1 x (2 reps x 2:00)   (per side)
    Core strengthening
        Hip Flexor Lift         1 x (2 reps x 2:00)   (per side)
        QL Plank                1 x (2 reps x 2:00)   (per side)
        Plank                   1 x 4:00
        Wall Back Extension     1 x 4:00
    Hip mobility
        Wall Groin Stretch      1 x 4:00
        90 90 Push Up           1 x (2 reps x 2:00)   (per side)
        Couch Stretch           1 x (2 reps x 2:00)   (per side)
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

# Performed order: (exercise, seconds per hold, per_side). Per-side moves are
# one set of 2 reps (left, right) x the hold; whole-body holds are one timed set.
_SIDES = 2

EXERCISES: list[tuple[str, int, bool]] = [
    # Hip strengthening
    ("Hip Internal Rotation", 2 * _MINUTE, True),
    ("Hip Airplane", 2 * _MINUTE, True),
    ("Side Hip Abduction", 2 * _MINUTE, True),
    ("Side Hip Adduction", 2 * _MINUTE, True),
    # Core strengthening
    ("Hip Flexor Lift", 2 * _MINUTE, True),
    ("QL Plank", 2 * _MINUTE, True),
    ("Plank", 4 * _MINUTE, False),
    ("Wall Back Extension", 4 * _MINUTE, False),
    # Hip mobility
    ("Wall Groin Stretch", 4 * _MINUTE, False),
    ("90 90 Push Up", 2 * _MINUTE, True),
    ("Couch Stretch", 2 * _MINUTE, True),
    ("Elephant Walk", 4 * _MINUTE, False),
]

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "back_rehab"


def build_plan(mappings: ExerciseMapping) -> dict[str, Any]:
    """Build the Back Rehab 2 workout dict from the exercise definitions.

    Args:
        mappings: ExerciseMapping loaded from the exercises folder.

    Returns:
        Complete workout dict ready to write to a .fnw file.
    """
    exercises: list[dict[str, Any]] = []
    for name, seconds, per_side in EXERCISES:
        if per_side:
            # One set of 2 reps (left, right): side count in Primary (reps),
            # hold seconds in Secondary (time). Counts as one group-set.
            exercises.append(
                build_exercise(
                    name,
                    [SetConfig(reps=_SIDES, weight=seconds)],
                    mappings,
                    focus="reps",
                    secondary_focus="time",
                ),
            )
        else:
            exercises.append(
                build_exercise(
                    name,
                    [SetConfig(reps=seconds)],
                    mappings,
                    focus="time",
                ),
            )
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
