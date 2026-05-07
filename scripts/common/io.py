"""I/O utilities for loading exercise mappings and writing workout files."""

import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ExerciseMapping:
    """Holds equipment and muscle category mappings for all exercises."""
    equipment: dict[str, str]  # exercise_name -> equipment_name
    primary_muscle: dict[str, str]  # exercise_name -> primary muscle
    secondary_muscles: dict[str, list[str]]  # exercise_name -> [secondary muscles]


# Equipment ID mapping (from .fnw files)
EQUIPMENT_IDS = {
    "None": "0",
    "Barbell": "1",
    "Double Dumbbell": "2",
    "Single Dumbbell": "3",
    "Machine": "4",
}


def load_exercise_mappings(exercises_dir: Path | str | None = None) -> ExerciseMapping:
    """
    Load exercise mappings from TSV files.

    Args:
        exercises_dir: Path to exercises folder. Defaults to ../exercises relative to scripts.

    Returns:
        ExerciseMapping with equipment and muscle data for all exercises.
    """
    if exercises_dir is None:
        exercises_dir = Path(__file__).parent.parent.parent / "exercises"
    else:
        exercises_dir = Path(exercises_dir)

    equipment_file = exercises_dir / "exercise_equipment_map.txt"
    muscles_file = exercises_dir / "exercise_primary_secondary_muscles.txt"

    # Load equipment mapping
    equipment = {}
    with open(equipment_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                exercise_name = parts[0].strip()
                equipment_name = parts[1].strip()
                equipment[exercise_name] = equipment_name

    # Load muscle mappings
    primary_muscle = {}
    secondary_muscles = {}
    with open(muscles_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            exercise_name = parts[0].strip()
            primary_muscle[exercise_name] = parts[1].strip() if len(parts) > 1 else ""
            if len(parts) > 2 and parts[2].strip():
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


def write_workout_file(workout: dict, output_path: Path | str) -> None:
    """
    Write a workout to a .fnw file.

    Args:
        workout: Complete workout dict in .fnw format
        output_path: Path to write the file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(workout, f, indent=2)


def read_workout_file(input_path: Path | str) -> dict:
    """
    Read a workout from a .fnw file.

    Args:
        input_path: Path to the .fnw file

    Returns:
        Workout dict
    """
    with open(input_path, "r") as f:
        return json.load(f)
