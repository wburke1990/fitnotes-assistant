# Authoring a workout plan

Read this before generating a `.fnw` — it captures the format and the builder
API so you don't have to re-derive them from the code each session.

## Where plans live

- Plans are written under `plans/<gym-or-group>/` (e.g. `plans/back_rehab/`).
- Filenames keep spaces and use a numeral: `Back Rehab 1.fnw`, not
  `back_rehab_1.fnw`.
- A `.fnw` is just JSON. **Don't `Read` existing ones** — they're large.
  Generate them with the builders instead.

## The builder API (`common.builders`)

| Function | What it makes |
| --- | --- |
| `SetConfig(reps, weight=0, rpe=0)` | one set |
| `build_exercise(name, sets, mappings, *, focus="reps")` | one exercise; `sets` is a list of `SetConfig` (or dicts). **One list item = one set.** Pass `focus="time"` for timed holds (each set's `reps` is then a duration in *seconds*). |
| `build_superset(exercises)` | one superset group from a list of exercises |
| `build_workout(name, exercises, *, supersets=False)` | whole workout; `False` = each exercise its own superset, `True` = all in one superset |
| `build_workout_from_supersets(name, supersets)` | whole workout from **multiple distinct** pre-built supersets (use this when a plan has more than one superset group) |

Load mappings with `load_exercise_mappings()` and write with
`write_workout_file(workout, path)` (both in `common.io`).

### Workout layout (the part that bites)

A routine is `Data[0]`. **`Data[0].Workouts[]` is the ordered list of blocks,
and each block holds exactly one `SuperSet`.** FitNotes renders only the *first*
`SuperSet` in a block, so a plan with two supersets needs two `Workouts[]`
entries — not one block with two `SuperSets`. The builders handle this: each
superset you pass becomes its own block.

A multi-exercise block must carry a `Name` (`"Set 1"`, `"Set 2"`, … — assigned
automatically) or FitNotes collapses its exercises onto the first one's
`Definition` on import. Single-exercise blocks carry no `Name`. The file also
needs `Version` `"3.4.2"`, `Type` `"FNWorkoutDefinitionDTO"`, and a `SortIndex`
on the routine — all set by `build_workout_from_supersets`. When in doubt,
structurally diff against `plans/back_rehab/Back Rehab 3.fnw` (a known-good
export) with `jq`.

### SetDetails semantics

- `Primary` = reps, `Secondary` = weight (int). `0` weight = bodyweight /
  fill-in-later, and the builder sets `SecondaryFocusId` to 0 automatically.
- For `focus="time"` exercises, `Primary` is the set's duration in **seconds**
  (the builder sets `PrimaryFocusId` to 3); `back_rehab_two.py` is the worked
  example (a timed hip-rehab circuit). Verified against a real FitNotes import:
  the holds display as `M:SS`.
- Number of sets = number of items in the `SetDetails` list.

### Gotcha: no notes field

A `.fnw` plan is only supersets of exercises with reps/weight. There is **no
free-text/notes field**, so stretches, warmup routines, and rest cues can't be
attached to the plan. Either encode them as (timed) exercises or keep them in a
companion `.txt` note — confirm which the user wants.

## Exercises must be registered first

`build_exercise` raises `KeyError` if the name isn't in **both** tab-separated
files under `exercises/`:

- `exercise_equipment_map.txt` — `Name<TAB>Equipment`
  (Equipment ∈ None, Barbell, Double Dumbbell, Single Dumbbell, Machine)
- `exercise_primary_secondary_muscles.txt` —
  `Name<TAB>Primary<TAB>Secondary, comma, list`

Muscle names should already exist in `builders.CATEGORY_IDS` so they get stable
IDs; add new ones there if needed.

## Pattern to copy

`weekly_split.py` (flat days), `back_rehab_one.py` (two supersets), and
`back_rehab_two.py` (a `focus="time"` circuit) are the worked examples. A
generator factors a `build_*` function (returns the workout dict, easy to
unit-test) from a `main()` that writes the file. Add tests under `tests/` —
see `test_back_rehab_one.py`.

The program modules carry a `#!/usr/bin/env python3` shebang, so a new one
must be executable (`chmod +x programs/your_plan.py`) or the pre-commit
`ruff` check fails with `EXE001` and aborts the commit.

Run one with:

```sh
uv --directory scripts run python -m programs.back_rehab_one
```
