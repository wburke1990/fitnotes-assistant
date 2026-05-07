"""I/O utilities for loading exercise mappings and writing workout files."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExerciseMapping:
    """Holds equipment and muscle category mappings for all exercises."""

    equipment: dict[str, str]
    primary_muscle: dict[str, str]
    secondary_muscles: dict[str, list[str]]


EQUIPMENT_IDS = {
    "None": "0",
    "Barbell": "1",
    "Double Dumbbell": "2",
    "Single Dumbbell": "3",
    "Machine": "4",
}

# Minimum tab-separated columns required for a row to carry the noted field.
_MIN_PARTS_FOR_EQUIPMENT = 2
_MIN_PARTS_FOR_PRIMARY = 2
_MIN_PARTS_FOR_SECONDARY = 3


def load_exercise_mappings(exercises_dir: Path | str | None = None) -> ExerciseMapping:
    """Load exercise mappings from TSV files.

    Args:
        exercises_dir: Path to exercises folder. Defaults to ../exercises relative to scripts.

    Returns:
        ExerciseMapping with equipment and muscle data for all exercises.
    """
    resolved_dir = (
        Path(__file__).parent.parent.parent / "exercises"
        if exercises_dir is None
        else Path(exercises_dir)
    )

    equipment_file = resolved_dir / "exercise_equipment_map.txt"
    muscles_file = resolved_dir / "exercise_primary_secondary_muscles.txt"

    equipment: dict[str, str] = {}
    with equipment_file.open() as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= _MIN_PARTS_FOR_EQUIPMENT:
                equipment[parts[0].strip()] = parts[1].strip()

    primary_muscle: dict[str, str] = {}
    secondary_muscles: dict[str, list[str]] = {}
    with muscles_file.open() as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("\t")
            exercise_name = parts[0].strip()
            primary_muscle[exercise_name] = (
                parts[1].strip() if len(parts) >= _MIN_PARTS_FOR_PRIMARY else ""
            )
            if len(parts) >= _MIN_PARTS_FOR_SECONDARY and parts[2].strip():
                secondary_muscles[exercise_name] = [
                    m.strip() for m in parts[2].split(",") if m.strip()
                ]
            else:
                secondary_muscles[exercise_name] = []

    return ExerciseMapping(
        equipment=equipment,
        primary_muscle=primary_muscle,
        secondary_muscles=secondary_muscles,
    )


def write_workout_file(workout: dict[str, Any], output_path: Path | str) -> None:
    """Write a workout to a .fnw file.

    Args:
        workout: Complete workout dict in .fnw format
        output_path: Path to write the file
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w") as f:
        json.dump(workout, f, indent=2)


def read_workout_file(input_path: Path | str) -> dict[str, Any]:
    """Read a workout from a .fnw file.

    Args:
        input_path: Path to the .fnw file

    Returns:
        Workout dict
    """
    with Path(input_path).open() as f:
        result: dict[str, Any] = json.load(f)
        return result
