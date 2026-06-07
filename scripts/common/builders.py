"""Builders for creating workout structures in .fnw format."""

import uuid
from dataclasses import dataclass
from typing import Any

from .io import EQUIPMENT_IDS, ExerciseMapping

CATEGORY_COLORS: dict[str, dict[str, Any]] = {
    "default": {
        "Alpha": 1,
        "IsPro": False,
        "IsDeletable": False,
        "Deleted": False,
        "Green": 217,
        "Red": 12,
        "Name": "Green",
        "Blue": 88,
        "Id": "2",
    },
}

CATEGORY_IDS: dict[str, str] = {
    "Quadriceps": "7",
    "Adductors": "6",
    "Gluteals": "12",
    "Calves": "14",
    "Hamstrings": "13",
    "Back (Lower)": "11",
    "Latissimus Dorsi": "16a8f3c5-7b2e-4d91-9f45-8e3d4c9a1b7f",
    "Biceps": "1",
    "Triceps": "2",
    "Deltoids": "9",
    "Pectorals": "17",
    "Trapezius": "8",
    "Forearms": "10",
    "Abdominals (Upper)": "4",
    "Abdominals (Lower)": "5",
    "Obliques": "3",
    "Rotator Cuff": "18",
    "Abductors": "1da1c21b-6d4b-49ee-b579-98e4a28a4c3b",
    "Hip Flexors": "D2064B30-8C3D-4794-89DD-77C080535633",
    "Quadratus Lumborum": "507d90fc-ce73-4a2c-a532-802cffb917fe",
    "Tibialis": "19",
    "Cardio": "15",
}


@dataclass
class SetConfig:
    """Configuration for a single set."""

    reps: int
    weight: float = 0
    rpe: float = 0


def _generate_uuid() -> str:
    """Generate a UUID string in the format used by .fnw files."""
    return str(uuid.uuid4()).upper()


def _build_category(name: str) -> dict[str, Any]:
    """Build a category object for a muscle group."""
    return {
        "Name": name,
        "Id": CATEGORY_IDS.get(name, _generate_uuid()),
        "Color": CATEGORY_COLORS["default"],
    }


def _build_equipment(name: str) -> dict[str, Any]:
    """Build an equipment object."""
    return {
        "Name": name,
        "Id": EQUIPMENT_IDS.get(name, "0"),
        "Deleted": False,
        "IsDeletable": False,
    }


def _build_set_detail(reps: int, weight: float, rpe: float = 0) -> dict[str, Any]:
    """Build a single set detail object."""
    return {
        "Id": _generate_uuid(),
        "Primary": reps,
        "Secondary": int(weight),
        "RPE": int(rpe),
        "Type": 0,
        "Status": 0,
        "IsPersonalRecord": False,
    }


def build_exercise(
    name: str,
    sets: list[SetConfig] | list[dict[str, Any]],
    mappings: ExerciseMapping,
) -> dict[str, Any]:
    """Build a complete exercise object from name and set configurations.

    Args:
        name: Exercise name (must exist in mappings)
        sets: List of SetConfig or dicts with {reps, weight, rpe?}
        mappings: ExerciseMapping loaded from files

    Returns:
        Complete exercise dict in .fnw format

    Raises:
        KeyError: If exercise name not found in mappings
    """
    if name not in mappings.equipment:
        msg = f"Exercise '{name}' not found in mappings"
        raise KeyError(msg)

    normalized_sets: list[SetConfig] = []
    for s in sets:
        if isinstance(s, SetConfig):
            normalized_sets.append(s)
        else:
            normalized_sets.append(
                SetConfig(
                    reps=s["reps"],
                    weight=s.get("weight", 0),
                    rpe=s.get("rpe", 0),
                ),
            )

    categories: list[dict[str, Any]] = []
    primary = mappings.primary_muscle.get(name, "")
    if primary:
        categories.append(_build_category(primary))
    categories.extend(_build_category(s) for s in mappings.secondary_muscles.get(name, []))

    set_details = [_build_set_detail(s.reps, s.weight, s.rpe) for s in normalized_sets]

    max_reps = max((s.reps for s in normalized_sets), default=0)
    max_weight = max((s.weight for s in normalized_sets), default=0)

    # 1 = reps, 2 = weight, 3 = time
    primary_focus_id = 1
    secondary_focus_id = 2 if max_weight > 0 else 0

    exercise_id = _generate_uuid()

    return {
        "Id": _generate_uuid(),
        "RestTime": 0,
        "Rules": [],
        "WarmupSetDetails": [],
        "SetDetails": set_details,
        "Definition": {
            "Id": exercise_id,
            "Name": name,
            "Deleted": False,
            "Equipment": _build_equipment(mappings.equipment[name]),
            "Categories": categories,
            "MaxPrimary": max_reps,
            "MaxSecondary": int(max_weight),
            "PrimaryFocusId": primary_focus_id,
            "SecondaryFocusId": secondary_focus_id,
        },
    }


def build_superset(exercises: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a superset containing one or more exercises.

    Args:
        exercises: List of exercise dicts (from build_exercise)

    Returns:
        Superset dict in .fnw format
    """
    return {
        "Id": _generate_uuid(),
        "Exercises": exercises,
    }


def build_workout_from_supersets(
    name: str,
    supersets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a complete workout file structure from pre-built supersets.

    Use this when a plan needs several distinct superset groups in one
    workout (e.g. two separate supersets done back to back). For the simpler
    cases of one-exercise-per-superset or a single all-in-one superset,
    prefer build_workout.

    Args:
        name: Workout name (e.g., "Back Rehab 1")
        supersets: List of superset dicts (from build_superset), in order

    Returns:
        Complete workout dict ready to write to .fnw file
    """
    return {
        "Version": "3.2.0",
        "IsList": True,
        "Type": "WorkoutDefinitionDTO",
        "Data": [
            {
                "Id": _generate_uuid(),
                "Name": name,
                "Deleted": False,
                "Workouts": [
                    {
                        "Id": _generate_uuid(),
                        "IsCurrent": False,
                        "IsEveryday": True,
                        "Measurements": [],
                        "SuperSets": supersets,
                    },
                ],
            },
        ],
    }


def build_workout(
    name: str,
    exercises: list[dict[str, Any]],
    *,
    supersets: bool = False,
) -> dict[str, Any]:
    """Build a complete workout file structure.

    Args:
        name: Workout name (e.g., "WH Monday")
        exercises: List of exercise dicts (from build_exercise)
        supersets: If False (default), each exercise is its own superset.
                   If True, all exercises are grouped into one superset.

    Returns:
        Complete workout dict ready to write to .fnw file
    """
    workout_supersets = (
        [build_superset(exercises)] if supersets else [build_superset([ex]) for ex in exercises]
    )

    return build_workout_from_supersets(name, workout_supersets)
