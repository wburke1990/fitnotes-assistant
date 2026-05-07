#!/usr/bin/env python3
"""
Example program: Generate a weekly workout split with heavy/medium/light days.

Heavy (Mon/Tue): 4 sets, 5-6 reps, RPE 8
Medium (Wed/Thu): 3 sets, 8-10 reps, RPE 7
Light (Fri/Sat): 2-3 sets, 12-15 reps, RPE 6

Usage:
    uv run python -m programs.weekly_split --output-dir ./output
"""

import argparse
from pathlib import Path

from common import (
    load_exercise_mappings,
    write_workout_file,
    build_exercise,
    build_workout,
    weight_at_rpe,
    calculate_weekly_volume,
    check_volume_minimums,
    summarize_volume,
)
from common.builders import SetConfig


# Example exercise list with 1RMs (you would customize this)
EXERCISE_1RMS = {
    "ATG Split Squat": 50,  # Single dumbbell weight
    "Romanian Deadlift (RDL)": 225,
    "Hamstring Curl": 120,
    "Lat Pulldown": 180,
    "Dumbbell Incline Bench Press": 70,  # Per dumbbell
    "Machine Overhead Press": 100,
    "Face Pull": 60,
    "Hyperextension": 0,  # Bodyweight, track time instead
}

# Day configurations
DAY_CONFIGS = {
    "heavy": {"sets": 4, "reps": 5, "rpe": 8},
    "medium": {"sets": 3, "reps": 8, "rpe": 7},
    "light": {"sets": 3, "reps": 12, "rpe": 6},
}

# Weekly schedule
WEEKLY_SCHEDULE = {
    "Monday": ("heavy", ["ATG Split Squat", "Romanian Deadlift (RDL)", "Hyperextension"]),
    "Tuesday": ("heavy", ["Lat Pulldown", "Dumbbell Incline Bench Press", "Face Pull"]),
    "Wednesday": ("medium", ["Hamstring Curl", "Machine Overhead Press", "Hyperextension"]),
    "Thursday": ("medium", ["ATG Split Squat", "Lat Pulldown", "Face Pull"]),
    "Friday": ("light", ["Romanian Deadlift (RDL)", "Dumbbell Incline Bench Press"]),
    "Saturday": ("light", ["Hamstring Curl", "Machine Overhead Press"]),
}


def generate_workout_for_day(
    day_name: str,
    intensity: str,
    exercises: list[str],
    mappings,
) -> dict:
    """Generate a single day's workout."""
    config = DAY_CONFIGS[intensity]

    workout_exercises = []
    for exercise_name in exercises:
        one_rm = EXERCISE_1RMS.get(exercise_name, 0)

        if one_rm > 0:
            weight = weight_at_rpe(one_rm, config["reps"], config["rpe"])
        else:
            weight = 0  # Bodyweight exercise

        sets = [
            SetConfig(reps=config["reps"], weight=weight, rpe=config["rpe"])
            for _ in range(config["sets"])
        ]

        exercise = build_exercise(exercise_name, sets, mappings)
        workout_exercises.append(exercise)

    return build_workout(f"Generated {day_name}", workout_exercises)


def main():
    parser = argparse.ArgumentParser(description="Generate weekly workout split")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./output"),
        help="Directory to write workout files",
    )
    parser.add_argument(
        "--prefix",
        default="GEN",
        help="Prefix for workout names (default: GEN)",
    )
    args = parser.parse_args()

    # Load exercise mappings
    mappings = load_exercise_mappings()
    print(f"Loaded {len(mappings.equipment)} exercises from mappings")

    # Generate workouts for each day
    workouts = []
    for day_name, (intensity, exercises) in WEEKLY_SCHEDULE.items():
        workout = generate_workout_for_day(day_name, intensity, exercises, mappings)

        # Update workout name with prefix
        workout["Data"][0]["Name"] = f"{args.prefix} {day_name}"

        # Write to file
        output_path = args.output_dir / f"{args.prefix} {day_name}.fnw"
        write_workout_file(workout, output_path)
        print(f"  {day_name} ({intensity}): {len(exercises)} exercises -> {output_path}")

        workouts.append(workout)

    # Calculate and display volume
    print("\n" + summarize_volume(calculate_weekly_volume(workouts)))

    # Check minimums
    print("\nVolume Check (12 set minimum):")
    results = check_volume_minimums(calculate_weekly_volume(workouts))
    deficits = [(m, r) for m, r in results.items() if r["deficit"] > 0]
    if deficits:
        for muscle, r in sorted(deficits, key=lambda x: -x[1]["deficit"]):
            print(f"  {muscle}: {r['current']:.1f}/{r['target']} sets (need {r['deficit']:.1f} more)")
    else:
        print("  All muscles meet minimum volume!")


if __name__ == "__main__":
    main()
