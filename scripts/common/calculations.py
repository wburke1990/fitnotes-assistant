"""Calculations for RPE-based programming and volume tracking."""

import math
from collections import defaultdict
from typing import Any

# Standard barbell plate increment in pounds; weights snap to multiples of this.
_PLATE_INCREMENT = 2.5
# Epley formula's denominator constant (reps_at_failure ≈ 30 * (1RM/weight - 1)).
_EPLEY_DENOMINATOR = 30
# Default secondary-muscle credit per set when computing weekly volume.
_SECONDARY_SET_WEIGHT = 0.5


# RPE to Reps-in-Reserve (RIR) mapping
# RPE 10 = 0 RIR (failure), RPE 9 = 1 RIR, etc.
def _rpe_to_rir(rpe: float) -> float:
    """Convert RPE to Reps in Reserve."""
    return 10 - rpe


def _rir_to_rpe(rir: float) -> float:
    """Convert Reps in Reserve to RPE."""
    return 10 - rir


def estimated_1rm(weight: float, reps: int) -> float:
    """Estimate 1RM using Epley formula.

    Args:
        weight: Weight lifted
        reps: Reps completed

    Returns:
        Estimated 1RM
    """
    if reps == 1:
        return weight
    return weight * (1 + reps / _EPLEY_DENOMINATOR)


def weight_at_rpe(one_rm: float, reps: int, rpe: float) -> float:
    """Calculate weight for target reps at target RPE.

    Uses Epley formula adjusted for RPE (reps in reserve).

    Args:
        one_rm: Known or estimated 1RM
        reps: Target rep count
        rpe: Target RPE (6-10 scale)

    Returns:
        Weight to use (rounded to nearest 2.5)

    Example:
        >>> weight_at_rpe(300, 5, 8)  # 5 reps @ RPE 8 with 300lb 1RM
        242.5
    """
    rir = _rpe_to_rir(rpe)
    # Total reps possible = target reps + reps in reserve
    effective_reps = reps + rir

    if effective_reps <= 0:
        return one_rm

    # Inverse Epley: weight = 1RM / (1 + reps/30)
    weight = one_rm / (1 + effective_reps / _EPLEY_DENOMINATOR)

    # Round to nearest 2.5 (standard plate increment)
    return round(weight / _PLATE_INCREMENT) * _PLATE_INCREMENT


def reps_at_rpe(one_rm: float, weight: float, rpe: float) -> int:
    """Calculate reps achievable at given weight and RPE.

    Args:
        one_rm: Known or estimated 1RM
        weight: Weight to lift
        rpe: Target RPE (6-10 scale)

    Returns:
        Number of reps (minimum 1). Rounded down so the prescription stays
        conservative — better to leave a rep in the tank than fail mid-set.

    Example:
        >>> reps_at_rpe(300, 240, 8)  # How many reps @ RPE 8 with 240lb?
        5
    """
    if weight >= one_rm:
        return 1

    rir = _rpe_to_rir(rpe)

    # From Epley: reps = 30 * (1RM/weight - 1)
    total_reps_possible = _EPLEY_DENOMINATOR * (one_rm / weight - 1)

    # Subtract RIR to get target reps
    target_reps = total_reps_possible - rir

    return max(1, math.floor(target_reps))


def percentage_of_1rm(one_rm: float, percentage: float) -> float:
    """Calculate weight as percentage of 1RM.

    Args:
        one_rm: Known or estimated 1RM
        percentage: Percentage as decimal (0.85 for 85%)

    Returns:
        Weight rounded to nearest 2.5
    """
    return round(one_rm * percentage / _PLATE_INCREMENT) * _PLATE_INCREMENT


def calculate_weekly_volume(workouts: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate total weekly volume per muscle group.

    Primary muscles count as 1.0 sets, secondary muscles as 0.5 sets.

    Args:
        workouts: List of workout dicts in .fnw format

    Returns:
        Dict mapping muscle name to total sets (float)

    Example:
        >>> volume = calculate_weekly_volume([monday, tuesday, wednesday])
        >>> volume["Quadriceps"]
        16.0
    """
    volume: dict[str, float] = defaultdict(float)

    for workout in workouts:
        for data in workout.get("Data", []):
            for workout_def in data.get("Workouts", []):
                for superset in workout_def.get("SuperSets", []):
                    for exercise in superset.get("Exercises", []):
                        definition = exercise.get("Definition", {})
                        categories = definition.get("Categories", [])
                        num_sets = len(exercise.get("SetDetails", []))

                        if not categories:
                            continue

                        # First category is primary (1.0 per set)
                        primary = categories[0].get("Name", "")
                        if primary:
                            volume[primary] += float(num_sets)

                        # Remaining categories are secondary (0.5 per set)
                        for cat in categories[1:]:
                            secondary = cat.get("Name", "")
                            if secondary:
                                volume[secondary] += num_sets * _SECONDARY_SET_WEIGHT

    return dict(volume)


def check_volume_minimums(
    volume: dict[str, float],
    targets: dict[str, int] | None = None,
    default_minimum: int = 12,
) -> dict[str, dict[str, Any]]:
    """Check if volume meets minimum targets per muscle group.

    Args:
        volume: Dict from calculate_weekly_volume()
        targets: Optional dict of muscle -> target sets (overrides default)
        default_minimum: Default minimum sets per muscle (default: 12)

    Returns:
        Dict mapping muscle to {current, target, deficit, meets_minimum}

    Example:
        >>> results = check_volume_minimums(volume, targets={"Quadriceps": 18})
        >>> results["Quadriceps"]
        {"current": 16.0, "target": 18, "deficit": 2.0, "meets_minimum": False}
    """
    targets = targets or {}
    results: dict[str, dict[str, Any]] = {}

    # Get all muscles from both volume and targets
    all_muscles = set(volume.keys()) | set(targets.keys())

    for muscle in all_muscles:
        current = volume.get(muscle, 0)
        target = targets.get(muscle, default_minimum)
        deficit = max(0, target - current)

        results[muscle] = {
            "current": current,
            "target": target,
            "deficit": deficit,
            "meets_minimum": current >= target,
        }

    return results


def summarize_volume(volume: dict[str, float]) -> str:
    """Create a formatted summary of volume by muscle group.

    Args:
        volume: Dict from calculate_weekly_volume()

    Returns:
        Formatted string summary
    """
    lines = ["Weekly Volume by Muscle Group", "=" * 35]

    for muscle, sets in sorted(volume.items(), key=lambda x: -x[1]):
        bar = "#" * int(sets)
        lines.append(f"{muscle:25} {sets:5.1f}  {bar}")

    return "\n".join(lines)
