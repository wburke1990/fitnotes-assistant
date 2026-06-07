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
| `build_exercise(name, sets, mappings)` | one exercise; `sets` is a list of `SetConfig` (or dicts). **One list item = one set.** |
| `build_superset(exercises)` | one superset group from a list of exercises |
| `build_workout(name, exercises, *, supersets=False)` | whole workout; `False` = each exercise its own superset, `True` = all in one superset |
| `build_workout_from_supersets(name, supersets)` | whole workout from **multiple distinct** pre-built supersets (use this when a plan has more than one superset group) |

Load mappings with `load_exercise_mappings()` and write with
`write_workout_file(workout, path)` (both in `common.io`).

### SetDetails semantics

- `Primary` = reps, `Secondary` = weight (int). `0` weight = bodyweight /
  fill-in-later, and the builder sets `SecondaryFocusId` to 0 automatically.
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

`weekly_split.py` (flat days) and `back_rehab_one.py` (two supersets) are the
worked examples. A generator factors a `build_*` function (returns the workout
dict, easy to unit-test) from a `main()` that writes the file. Add tests under
`tests/` — see `test_back_rehab_one.py`.

Run one with:

```sh
uv --directory scripts run python -m programs.back_rehab_one
```
