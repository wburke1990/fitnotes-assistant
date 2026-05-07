"""Builders for creating workout structures in .fnw format."""

import uuid
from dataclasses import dataclass

from .io import ExerciseMapping, EQUIPMENT_IDS


# Category color palette (from existing .fnw files)
CATEGORY_COLORS = {
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
    }
}

# Known category IDs from existing workouts
CATEGORY_IDS = {
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


def _build_category(name: str) -> dict:
    """Build a category object for a muscle group."""
    return {
        "Name": name,
        "Id": CATEGORY_IDS.get(name, _generate_uuid()),
        "Color": CATEGORY_COLORS["default"],
    }


def _build_equipment(name: str) -> dict:
    """Build an equipment object."""
    return {
        "Name": name,
        "Id": EQUIPMENT_IDS.get(name, "0"),
        "Deleted": False,
        "IsDeletable": False,
    }


def _build_set_detail(reps: int, weight: float, rpe: float = 0) -> dict:
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
    sets: list[SetConfig] | list[dict],
    mappings: ExerciseMapping,
) -> dict:
    """
    Build a complete exercise object from name and set configurations.

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
        raise KeyError(f"Exercise '{name}' not found in mappings")

    # Normalize sets to SetConfig
    normalized_sets = []
    for s in sets:
        if isinstance(s, SetConfig):
            normalized_sets.append(s)
        else:
            normalized_sets.append(SetConfig(
                reps=s["reps"],
                weight=s.get("weight", 0),
                rpe=s.get("rpe", 0),
            ))

    # Build categories list (primary first, then secondaries)
    categories = []
    primary = mappings.primary_muscle.get(name, "")
    if primary:
        categories.append(_build_category(primary))
    for secondary in mappings.secondary_muscles.get(name, []):
        categories.append(_build_category(secondary))

    # Build set details
    set_details = [
        _build_set_detail(s.reps, s.weight, s.rpe)
        for s in normalized_sets
    ]

    # Determine max values from sets
    max_reps = max(s.reps for s in normalized_sets) if normalized_sets else 0
    max_weight = max(s.weight for s in normalized_sets) if normalized_sets else 0

    # Determine focus IDs based on what we're tracking
    # 1 = reps, 2 = weight, 3 = time
    primary_focus_id = 1  # reps
    secondary_focus_id = 2 if max_weight > 0 else 0  # weight if used

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


def build_superset(exercises: list[dict]) -> dict:
    """
    Build a superset containing one or more exercises.

    Args:
        exercises: List of exercise dicts (from build_exercise)

    Returns:
        Superset dict in .fnw format
    """
    return {
        "Id": _generate_uuid(),
        "Exercises": exercises,
    }


def build_workout(
    name: str,
    exercises: list[dict],
    supersets: bool = False,
) -> dict:
    """
    Build a complete workout file structure.

    Args:
        name: Workout name (e.g., "WH Monday")
        exercises: List of exercise dicts (from build_exercise)
        supersets: If False (default), each exercise is its own superset.
                   If True, all exercises are grouped into one superset.

    Returns:
        Complete workout dict ready to write to .fnw file
    """
    if supersets:
        # All exercises in one superset
        workout_supersets = [build_superset(exercises)]
    else:
        # Each exercise in its own superset
        workout_supersets = [build_superset([ex]) for ex in exercises]

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
                        "SuperSets": workout_supersets,
                    }
                ],
            }
        ],
    }
