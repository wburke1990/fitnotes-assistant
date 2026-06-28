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
| `build_exercise(name, sets, mappings, *, focus="reps", secondary_focus="weight")` | one exercise; `sets` is a list of `SetConfig` (or dicts). **One list item = one set.** Pass `focus="time"` for timed holds (each set's `reps` is then a duration in *seconds*). Pass `secondary_focus="time"` to store a hold duration (seconds) in the Secondary field of a reps-focused move — see per-side holds below. |
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

### Block order is round-robin (decides where an exercise *appears*)

FitNotes performs a superset block round-robin by set number: set 1 of every
exercise, then set 2 of every exercise, and so on. So **a 1-set exercise inside
a 3-set superset shows up in round 1, not at the end** — which bit us when
prehab drills landed next to the first heavy set instead of after it. Three
consequences for layout:

- **Do-it-after items** (a prehab drill, a finisher, a between-superset rest
  movement) must be their **own single-exercise block placed after** the
  superset — not an extra exercise inside it. Otherwise they round-robin to the
  front.
- **To spread a warm-up across a lift's rest,** encode it as **one exercise with
  N sets**, not N separate single-set exercises (which all pile into round 1).
  The Sunday split-squat on-ramp is one ATG Split Squat entry with 2 sets
  `[0, 45]` inside the Nordic superset, so bodyweight lands in round 1 and the
  empty bar in round 2.
- **Interspersed fillers** (meant to fall *between* the lead's sets) stay
  *inside* the block with a set count ≤ the lead's; they drop into the gaps.
  Sunday's Couch Stretch is 2 sets inside the 3-set RDL superset, so a stretch
  falls in each rest.

`back_rehab_jj.py` is the worked example of all three.

### SetDetails semantics

- `Primary` = reps, `Secondary` = weight (int). `0` weight = bodyweight /
  fill-in-later, and the builder sets `SecondaryFocusId` to 0 automatically.
- For `focus="time"` exercises, `Primary` is the set's duration in **seconds**
  (the builder sets `PrimaryFocusId` to 3); `back_rehab_two.py` is the worked
  example (a timed hip-rehab circuit). Verified against a real FitNotes import:
  the holds display as `M:SS`.
- Number of sets = number of items in the `SetDetails` list.
- **Per-side / unilateral moves count once.** `calculate_weekly_volume`
  (`common.calculations`) tallies *sets* (`len(SetDetails)`), never reps, so a
  per-side hold logged as two sets (left, then right) double-counts the muscle
  group. Encode it as **one** set of 2 reps × the hold instead:
  `SetConfig(reps=2, weight=seconds)` with `focus="reps", secondary_focus="time"`
  (Primary = 2 sides, `SecondaryFocusId` 3 carries the seconds). `back_rehab_two.py`
  does this for its hip holds; Copenhagen Plank in `Back Rehab 3.fnw` is the same
  pattern. The same caution applies to reps/weight unilateral lifts — decide up
  front whether a left+right pair is one group-set or two.

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

## Designing supersets to avoid interference

Superset partners must not compete for the same *limiter*, so one recovers while
the other works. The rules that came out of the back-rehab-JJ build:

- **Don't pair movements that share prime movers.** RDL + hyperextension are both
  hams / glutes / low-back — you'd be forced to rest between them and the
  superset buys nothing. A priority lift's fillers must avoid its muscles.
- **The limiter is a system, not just a muscle.** Grip / forearms, lumbar
  stabilizers, and CNS all count. A snatch-grip RDL is grip-limited, so its
  filler is grip-free (tibialis), never a single-dumbbell calf raise (which is
  itself forearm work). Two grip-heavy or two spine-loading moves in one block
  interfere even if their target muscles differ.
- **Same muscle, same session → different supersets, not the same block.** Put
  one early and one late (Copenhagen Plank in SS1; the side-lying adductor raise
  in SS2/SS3). They get rest between exposures, and the early movement warms up
  the later one.
- **If same-muscle pairing is unavoidable (time-forced), mix range/length.** Do
  the shortened/harder variant first, the lengthened/lighter one second (Nordic,
  then a light RDL in the stretched position). It's a compromise — separating
  them into different supersets is still better.
- **Order for safety inside a block:** the heaviest / least-stable / highest-skill
  movement goes first, while the stabilizers are fresh; never pre-fatigue the
  muscles that protect a riskier lift (side-lying hyper *before* the regular
  hyperextension). Matters most for rehab work.

Two budgeting heuristics from the same build:

- **Filler count = the lead's rest interval.** ~2–3 non-interfering fillers ≈
  3–4 min between heavy compound sets. Match filler *duration* to the rest you
  want: sub-second-rep work (calf, tibialis) adds volume almost free during rest
  you'd take anyway; long holds / stretches fill long rests productively.
- **Progress compounds by load, accessories by sets.** A +1 set on a priority
  lift multiplies across training days and lands on a fatiguing movement — easy
  to overshoot and bleed into recovery (or the athlete's sport). Add sets to the
  cheap, non-interfering accessories instead.

When a plan supplements a sport, let the sport cover what it covers and cut that
lifting volume (the JJ block drops pressing because grappling supplies pecs /
delts / forearms / back), and place the most DOMS-inducing eccentric work where
soreness lands on rest or sport-light days.

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
