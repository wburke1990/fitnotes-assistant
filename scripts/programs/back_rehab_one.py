#!/usr/bin/env python3
"""Generate the "Back Rehab 1" plan as a .fnw file.

Two supersets, four sets each:

Superset 1 (hamstring posterior-chain pairing):
    1. Nordic Hamstring Curl        4 x 12
    2. Snatch-Grip Stiff-Legged RDL 4 x 8 @ 135  (snatch grip to reach more depth)

Superset 2 (split squat gives the lower back a break before the hyperextensions,
the row comes right after):
    1. ATG Split Squat (front rack) 4 x 12 @ 75
    2. Hyperextension               4 x 35       (bodyweight for now, load to come)
    3. Bird Dog Row                 4 x 12 @ 55

Between-set interludes (couch stretch, ATG warmup routine) are part of the
protocol but intentionally not encoded here -- a .fnw plan has no notes field.

Usage:
    uv --directory scripts run python -m programs.back_rehab_one
"""

import argparse
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

PLAN_NAME = "Back Rehab 1"
SETS_PER_EXERCISE = 4

# Each inner list is one superset, in performed order: (exercise, reps, weight lb).
SUPERSETS: list[list[tuple[str, int, int]]] = [
    [
        ("Nordic Hamstring Curl", 12, 0),
        ("Snatch-Grip Stiff-Legged RDL", 8, 135),
    ],
    [
        ("ATG Split Squat", 12, 75),
        ("Hyperextension", 35, 0),
        ("Bird Dog Row", 12, 55),
    ],
]

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "back_rehab"


def build_plan(mappings: ExerciseMapping) -> dict[str, Any]:
    """Build the Back Rehab 1 workout dict from the superset definitions.

    Args:
        mappings: ExerciseMapping loaded from the exercises folder.

    Returns:
        Complete workout dict ready to write to a .fnw file.
    """
    supersets: list[dict[str, Any]] = []
    for group in SUPERSETS:
        exercises = [
            build_exercise(
                name,
                [SetConfig(reps=reps, weight=weight) for _ in range(SETS_PER_EXERCISE)],
                mappings,
            )
            for name, reps, weight in group
        ]
        supersets.append(build_superset(exercises))

    return build_workout_from_supersets(PLAN_NAME, supersets)


def main() -> None:
    """Generate Back Rehab 1 and write it to the back_rehab plans folder."""
    parser = argparse.ArgumentParser(description="Generate the Back Rehab 1 plan")
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
