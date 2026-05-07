"""Tests for common.calculations."""

import pytest

from common.calculations import (
    _rir_to_rpe,
    _rpe_to_rir,
    calculate_weekly_volume,
    check_volume_minimums,
    estimated_1rm,
    percentage_of_1rm,
    reps_at_rpe,
    summarize_volume,
    weight_at_rpe,
)


# ---------------------------------------------------------------------------
# RPE <-> RIR
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rpe,rir",
    [(10, 0), (9, 1), (8, 2), (7, 3), (6.5, 3.5)],
)
def test_rpe_rir_round_trip(rpe, rir):
    assert _rpe_to_rir(rpe) == rir
    assert _rir_to_rpe(rir) == rpe


# ---------------------------------------------------------------------------
# estimated_1rm
# ---------------------------------------------------------------------------


def test_estimated_1rm_single_rep_returns_weight():
    assert estimated_1rm(225, 1) == 225


def test_estimated_1rm_epley_formula():
    # Epley: w * (1 + reps/30); 200 * (1 + 5/30) = 233.333...
    assert estimated_1rm(200, 5) == pytest.approx(200 * (1 + 5 / 30))


def test_estimated_1rm_increases_with_reps():
    base = estimated_1rm(200, 1)
    higher = estimated_1rm(200, 8)
    assert higher > base


# ---------------------------------------------------------------------------
# weight_at_rpe
# ---------------------------------------------------------------------------


def test_weight_at_rpe_docstring_example():
    # 5 reps @ RPE 8 with a 300 lb 1RM → 242.5 lb
    assert weight_at_rpe(300, 5, 8) == 242.5


def test_weight_at_rpe_rounds_to_nearest_2_5():
    result = weight_at_rpe(300, 5, 8)
    assert (result * 10) % 25 == 0  # multiple of 2.5


def test_weight_at_rpe_max_effort_single():
    # 1 rep @ RPE 10 means 0 RIR → effective_reps=1, so weight ≈ 1RM / (1+1/30)
    expected = 300 / (1 + 1 / 30)
    expected = round(expected / 2.5) * 2.5
    assert weight_at_rpe(300, 1, 10) == expected


def test_weight_at_rpe_higher_rpe_means_more_weight():
    # Same target reps, higher RPE = closer to failure = heavier
    light = weight_at_rpe(300, 5, 7)
    heavy = weight_at_rpe(300, 5, 9)
    assert heavy > light


def test_weight_at_rpe_more_reps_means_less_weight():
    # Same RPE, more reps = lighter
    fewer = weight_at_rpe(300, 3, 8)
    more = weight_at_rpe(300, 8, 8)
    assert fewer > more


def test_weight_at_rpe_zero_effective_reps_returns_one_rm():
    # 0 reps at RPE 10 → effective_reps = 0 → returns 1RM unrounded
    assert weight_at_rpe(300, 0, 10) == 300


# ---------------------------------------------------------------------------
# reps_at_rpe
# ---------------------------------------------------------------------------


def test_reps_at_rpe_weight_at_or_above_1rm_returns_one():
    assert reps_at_rpe(300, 300, 8) == 1
    assert reps_at_rpe(300, 350, 6) == 1


def test_reps_at_rpe_known_value():
    # 1RM=300, 240 lb, RPE 8:
    #   total possible = 30 * (300/240 - 1) = 7.5
    #   target = 7.5 - 2 (RIR) = 5.5 → floor()'d to 5 (conservative)
    assert reps_at_rpe(300, 240, 8) == 5


def test_reps_at_rpe_rounds_down_for_safety():
    # Anything in [5.0, 6.0) target reps should return 5, never 6.
    # This pins the conservative-rounding contract.
    assert reps_at_rpe(300, 240, 8) == 5  # target = 5.5
    # 1RM=300, 230 lb, RPE 8 → total = 30*(300/230-1) ≈ 9.13, target ≈ 7.13 → 7
    assert reps_at_rpe(300, 230, 8) == 7
    # Exact integer target should pass through unchanged.
    # 1RM=300, 200 lb, RPE 7 → total = 15, target = 15 - 3 = 12
    assert reps_at_rpe(300, 200, 7) == 12


def test_reps_at_rpe_minimum_is_one():
    # Heavy weight near 1RM at low RPE: target reps would be < 1
    assert reps_at_rpe(300, 295, 6) == 1


def test_reps_at_rpe_higher_rpe_yields_more_reps():
    low = reps_at_rpe(300, 200, 7)
    high = reps_at_rpe(300, 200, 10)
    assert high > low


# ---------------------------------------------------------------------------
# percentage_of_1rm
# ---------------------------------------------------------------------------


def test_percentage_of_1rm_clean_value():
    assert percentage_of_1rm(300, 0.85) == 255.0


def test_percentage_of_1rm_rounds_to_2_5():
    # 300 * 0.83 = 249 → nearest 2.5 is 250
    assert percentage_of_1rm(300, 0.83) == 250.0


def test_percentage_of_1rm_full_load():
    assert percentage_of_1rm(300, 1.0) == 300.0


def test_percentage_of_1rm_zero():
    assert percentage_of_1rm(300, 0.0) == 0.0


# ---------------------------------------------------------------------------
# calculate_weekly_volume
# ---------------------------------------------------------------------------


def _make_exercise(primary, secondaries=(), num_sets=1):
    """Build a minimal Exercise dict matching the .fnw structure."""
    categories = [{"Name": primary}] + [{"Name": s} for s in secondaries]
    return {
        "Definition": {"Categories": categories},
        "SetDetails": [{"Reps": 5, "Metric": {"Value": 100}} for _ in range(num_sets)],
    }


def _make_workout(exercises):
    return {
        "Data": [
            {
                "Workouts": [
                    {"SuperSets": [{"Exercises": exercises}]},
                ],
            },
        ],
    }


def test_calculate_weekly_volume_empty():
    assert calculate_weekly_volume([]) == {}


def test_calculate_weekly_volume_primary_only():
    workout = _make_workout([_make_exercise("Quadriceps", num_sets=4)])
    assert calculate_weekly_volume([workout]) == {"Quadriceps": 4.0}


def test_calculate_weekly_volume_secondaries_count_half():
    workout = _make_workout(
        [_make_exercise("Chest", secondaries=["Triceps", "Front Delts"], num_sets=3)]
    )
    volume = calculate_weekly_volume([workout])
    assert volume == {"Chest": 3.0, "Triceps": 1.5, "Front Delts": 1.5}


def test_calculate_weekly_volume_accumulates_across_workouts():
    monday = _make_workout([_make_exercise("Quadriceps", num_sets=4)])
    wednesday = _make_workout(
        [_make_exercise("Quadriceps", secondaries=["Hamstrings"], num_sets=2)]
    )
    volume = calculate_weekly_volume([monday, wednesday])
    assert volume == {"Quadriceps": 6.0, "Hamstrings": 1.0}


def test_calculate_weekly_volume_skips_exercises_without_categories():
    workout = _make_workout(
        [
            {"Definition": {"Categories": []}, "SetDetails": [{}, {}]},
            _make_exercise("Back", num_sets=2),
        ]
    )
    assert calculate_weekly_volume([workout]) == {"Back": 2.0}


def test_calculate_weekly_volume_handles_missing_keys():
    # Workouts missing nested keys should be tolerated, not crash.
    assert calculate_weekly_volume([{}]) == {}
    assert calculate_weekly_volume([{"Data": [{}]}]) == {}
    assert calculate_weekly_volume([{"Data": [{"Workouts": [{}]}]}]) == {}


def test_calculate_weekly_volume_multiple_supersets():
    workout = {
        "Data": [
            {
                "Workouts": [
                    {
                        "SuperSets": [
                            {"Exercises": [_make_exercise("Chest", num_sets=3)]},
                            {"Exercises": [_make_exercise("Back", num_sets=3)]},
                        ]
                    }
                ]
            }
        ]
    }
    assert calculate_weekly_volume([workout]) == {"Chest": 3.0, "Back": 3.0}


# ---------------------------------------------------------------------------
# check_volume_minimums
# ---------------------------------------------------------------------------


def test_check_volume_minimums_default_threshold():
    volume = {"Quadriceps": 16.0, "Calves": 6.0}
    results = check_volume_minimums(volume, default_minimum=12)

    assert results["Quadriceps"] == {
        "current": 16.0,
        "target": 12,
        "deficit": 0,
        "meets_minimum": True,
    }
    assert results["Calves"] == {
        "current": 6.0,
        "target": 12,
        "deficit": 6,
        "meets_minimum": False,
    }


def test_check_volume_minimums_target_overrides_default():
    volume = {"Quadriceps": 16.0}
    results = check_volume_minimums(volume, targets={"Quadriceps": 18})
    assert results["Quadriceps"]["target"] == 18
    assert results["Quadriceps"]["deficit"] == 2.0
    assert results["Quadriceps"]["meets_minimum"] is False


def test_check_volume_minimums_includes_targets_with_no_volume():
    # Muscle in targets but missing from volume → current = 0, full deficit.
    results = check_volume_minimums({}, targets={"Rear Delts": 10})
    assert results["Rear Delts"] == {
        "current": 0,
        "target": 10,
        "deficit": 10,
        "meets_minimum": False,
    }


def test_check_volume_minimums_meets_exactly_at_target():
    results = check_volume_minimums({"Chest": 12.0}, default_minimum=12)
    assert results["Chest"]["meets_minimum"] is True
    assert results["Chest"]["deficit"] == 0


def test_check_volume_minimums_deficit_never_negative():
    results = check_volume_minimums({"Chest": 30.0}, default_minimum=12)
    assert results["Chest"]["deficit"] == 0


# ---------------------------------------------------------------------------
# summarize_volume
# ---------------------------------------------------------------------------


def test_summarize_volume_has_header():
    out = summarize_volume({"Chest": 10.0})
    lines = out.splitlines()
    assert lines[0] == "Weekly Volume by Muscle Group"
    assert set(lines[1]) == {"="}


def test_summarize_volume_sorts_descending_by_sets():
    volume = {"Chest": 8.0, "Back": 16.0, "Calves": 4.0}
    out = summarize_volume(volume)
    body = out.splitlines()[2:]
    order = [line.split()[0] for line in body]
    assert order == ["Back", "Chest", "Calves"]


def test_summarize_volume_empty():
    out = summarize_volume({})
    assert out.splitlines() == ["Weekly Volume by Muscle Group", "=" * 35]


def test_summarize_volume_bar_length_matches_int_sets():
    out = summarize_volume({"Chest": 7.5})
    chest_line = [ln for ln in out.splitlines() if ln.startswith("Chest")][0]
    # Bar uses int(sets), so 7.5 → 7 hashes
    assert chest_line.count("#") == 7
