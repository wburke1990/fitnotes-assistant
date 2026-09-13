#!/usr/bin/env python3
"""Generate the "CHI" 5-day/week plan as five .fnw files.

The first plan written for the CHICAGO home gym. Everything else under plans/ is
a travel gym: plans/wh/ is the machine gym, and plans/pit/ (with its duplicate
plans/pa/) plus plans/back_rehab/ and plans/back_rehab_jj/ are all Pittsburgh.

Context this plan is built for:
  * Lifting Monday-Friday, up to ~90 min a session. No weekends.
  * NO jujitsu for the first month back. That makes month one the highest-quality
    lifting window of the block: no grappling soreness, no recovery tax, and no
    delayed-soreness gate on the neck ramp.

TWO RECOVERY CONSTRAINTS SHAPE THE WHOLE WEEK, and they point the same way:
  * GRIP is a long-standing limiter -- heavy grip on back-to-back days does not
    recover. So every grip-heavy movement is CLUSTERED onto the same days:
    the snatch-grip RDL, the pulldown and row, and any loaded carry. (The 40 lb
    one-arm calf raise is the exception -- that weight doesn't tire the hands.)
  * The POSTERIOR CHAIN is the same story -- RDLs, hamstring work and the hypers
    cannot be spread across alternating days and recovered. So they cluster too.
    The front rack split squat joins them: it taxes the hamstrings hard.

The result is three big days and two light ones:
  * MON / WED / FRI -- the big pulling + posterior-chain days, structurally
    identical. RDL, split squat, hyper, Nordic curl and the pull all land here,
    so grip and hamstrings get a full day off between exposures and the low back
    is never trained on consecutive days. Wednesday is the reduced version: the
    RDL keeps its 155 and drops to two sets, and the split squat is the lighter
    paused one. Load is what maintains strength, so volume is what gets cut.
  * TUE / THU -- short, deliberately carrying NO hamstring work, NO spinal
    extension and nothing that has to be gripped hard. Side hypers, ring dips,
    the light one-arm calf raise, cable abduction, QL raises and neck.

Within a big day, the four heavy movements each get their OWN superset, so none
of them rests against another that taxes the same tissue. The one deliberate
pairing is NORDIC CURL with the PULLDOWN: Nordics tax neither grip nor low back,
so the pull can ride their rest for free.

Three progressions DRIVE the block (the user's own pick); everything else is held
at a maintenance dose:
  1. LOW BACK -- the hyperextension ladder, now on the one-legged CURVED-BACK
     variant, ramping reps toward 3 sets x 35 per side before any load goes on.
  2. ADDUCTORS -- side-lying hyperextension adductor raises, same reps-then-load
     structure, starting from 8 per side. These live on the LIGHT days: no grip,
     no hamstrings, no extension, so they don't belong on the big days.
  3. FRONT RACK SPLIT SQUAT -- a linear load ramp, +5 lb/week from 70 to 135
     (13 weeks). The goal is not the 135 itself: it is to earn a MAINTENANCE
     weight worth holding. Strength is kept by training at the same load, not
     the same volume, so a heavier maintenance weight preserves more ability.

The hamstring TENDON work is the Nordic curl -- a slow, heavy eccentric is
exactly the high-strain, ~3-second loading tendons adapt to, and it needs no
equipment this gym lacks. It stays at 4 sets: tendon adaptation saturates at a
low volume, so more buys nothing and costs recovery.

Volume model (see scripts/programs/README.md): a muscle needs >=12 sets/week
(secondaries at 0.5, pooled) to be PROGRESSED. Below 12 is maintenance.
Progression targets here: Back (Lower), Adductors, Quadriceps, Hamstrings,
Tibialis. Deliberately held at maintenance: Abductors (cable, load kept high),
Calves, Pectorals, Deltoids, Latissimus Dorsi, Hip Flexors.

Weights are starting targets -- adjust in FitNotes. The progression detail lives
in the companion note (a .fnw has no notes field):
plans/chi/CHI - progression notes.txt

Usage:
    uv --directory scripts run python -m programs.chi_block
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common import (
    build_exercise,
    build_superset,
    build_workout_from_supersets,
    load_exercise_mappings,
    write_workout_file,
)
from common.builders import SetConfig
from common.io import ExerciseMapping

PLAN_PREFIX = "CHI"


@dataclass
class Move:
    """One exercise within a block: its working sets, focus mode, and warm-ups."""

    name: str
    sets: list[SetConfig]
    focus: str = "reps"
    secondary_focus: str = "weight"
    warmups: list[SetConfig] = field(default_factory=list)


def _reps(name: str, reps: int, weight: float, count: int) -> Move:
    """A normal reps/weight lift repeated `count` sets."""
    return Move(name, [SetConfig(reps=reps, weight=weight) for _ in range(count)])


def _hold(name: str, seconds: int, count: int = 1) -> Move:
    """A whole-body timed hold (Primary = seconds)."""
    return Move(name, [SetConfig(reps=seconds) for _ in range(count)], focus="time")


# --- Per-side recording convention -------------------------------------------
# Sided moves are recorded as TOTAL reps across both sides, logged as ONE set per
# round. Two metrics stay honest that way: SET-count volume (the 12-set floor)
# counts sets, so one set per round keeps a per-side move from double-counting;
# TONNAGE (reps x weight x sets) needs the full rep count, so per-side reps would
# halve it. Weights stay per-side / what is actually on the bar.

# --- The big days: one superset per heavy movement ----------------------------

# Snatch-grip RDL, NO straps (grip trained raw). HELD STEADY at 155 while the
# hypers progress; the ceiling for this gym is 300 (past that means buying
# plates, and 300 is well past what the back needs). This is the single biggest
# grip stressor in the plan, which is why every other grip movement shares its
# days. Wednesday runs a lighter version of the same lift rather than dropping
# it -- alternating hinge days with non-hinge days is what does not recover.
_RDL = Move(
    "Snatch-Grip Stiff-Legged RDL",
    [SetConfig(reps=8, weight=155) for _ in range(4)],
    warmups=[
        SetConfig(reps=12, weight=45),
        SetConfig(reps=12, weight=45),
        SetConfig(reps=12, weight=95),
        SetConfig(reps=8, weight=135),
    ],
)
# Wednesday's hinge: the SAME 155, two sets instead of four. The RDL is already
# held steady -- it is a maintenance lift while the hypers drive -- and strength
# is maintained by training at the same LOAD, not the same volume. Dropping the
# weight instead of the sets would make it a stimulus that is neither heavy
# enough to hold anything nor light enough to be free. High-rep RDL is the other
# way to fill the day and is off the table: form degrades exactly where the back
# is being rehabbed.
_RDL_LIGHT = Move(
    "Snatch-Grip Stiff-Legged RDL",
    [SetConfig(reps=8, weight=155) for _ in range(2)],
    warmups=[
        SetConfig(reps=12, weight=45),
        SetConfig(reps=12, weight=95),
        SetConfig(reps=8, weight=135),
    ],
)

# DRIVER 3. Front rack split squat, +5 lb/week, 70 -> 135 over 13 weeks. The bar
# sits in the rack position, so this costs no grip -- but it taxes the hamstrings
# hard, which is why it belongs on the big days. 12 reps/side = 24 total.
# Warm-ups (bodyweight, then the empty bar) add session time, not volume.
_SPLIT_SQUAT = Move(
    "Front Rack Split Squat",
    [SetConfig(reps=24, weight=70) for _ in range(4)],
    warmups=[SetConfig(reps=24, weight=0), SetConfig(reps=24, weight=45)],
)
# Wednesday: the PAUSED exposure. Lighter load, 3-5 s held at full depth. The
# limiter on this lift is strength in the deep position, not the rack, so pause
# time and depth progress alongside the Mon/Fri load. Counted volume -- real work.
_SPLIT_SQUAT_PAUSED = Move(
    "Front Rack Split Squat",
    [SetConfig(reps=16, weight=50) for _ in range(3)],
    warmups=[SetConfig(reps=24, weight=0)],
)

# DRIVER 1. One-legged CURVED-BACK hyperextension on the 45-degree bench -- the
# rung above the one-legged work finished at the machine gym (whose bench is
# flat, and therefore harder: peak load lands at full extension rather than
# partway down, so that work transfers favourably here). Ramp reps to 35 PER SIDE
# for 3 sets before adding any load. Starting 5/side = 10 total.
_HYPER = _reps("Hyperextension", reps=10, weight=0, count=3)

# The hamstring TENDON slot. A slow heavy Nordic eccentric is the high-strain,
# ~3-second loading tendons adapt to, and it needs nothing this gym lacks. Stays
# at 4 sets -- tendon adaptation saturates at roughly a minute of high-strain
# time per session, so more volume buys nothing and costs recovery. It taxes
# NEITHER grip NOR the low back, which is why the pull rides its rest.
_NORDIC = _reps("Nordic Hamstring Curl", reps=8, weight=0, count=4)

# The pull. Grip-heavy, so it only ever appears on the big days, supersetted with
# the Nordic curl. Pulldown Mon/Fri, low row Wednesday, for a change of angle.
_PULLDOWN = _reps("Lat Pulldown", reps=10, weight=120, count=3)
_LOW_ROW = _reps("Low Row", reps=10, weight=120, count=3)

# Hip/quad mobility riding the RDL rest, warming the deep position the split
# squat is limited by -- done at the bar, so the platform is never abandoned.
# 2 sides x 120 s logged as one set.
_COUCH = Move(
    "Couch Stretch",
    [SetConfig(reps=2, weight=120) for _ in range(3)],
    secondary_focus="time",
)

# Big-day fillers. None may tax the HAMSTRINGS or the LOW BACK, or it would
# defeat the point of giving the heavy movements their own supersets. Grip is a
# different matter: these are the grip days, so a grip-taxing filler belongs here
# and nowhere else.
# Tibialis on the tib bar, one-legged (35/side = 70 total): 4 sets x 3 days =
# 12/wk, its progression floor. Handstand push-ups and the incline press are the
# grip-free pressing.
_TIB = _reps("Tibialis Raise", reps=70, weight=25, count=4)
_HSPU = _reps("Handstand Push-Up", reps=5, weight=0, count=3)
_INCLINE = _reps("Barbell Incline Bench Press", reps=8, weight=135, count=3)
_L_SIT = _hold("L-Sit", 30, count=3)

# --- The light days: no grip, no hamstrings, no spinal extension --------------

# DRIVER 2. Side-lying hyperextension adductor raise. Same bench as the hyper but
# a lateral movement, and it costs no grip and no hamstring -- so it lives here,
# off the big days. Currently 8 per side (= 16 total); ramp reps before load.
# 6 sets x 2 days = 12/wk, clearing the floor on its own.
_SIDE_HYPER = _reps("Side-Lying Hyperextension Adductor Raise", reps=16, weight=0, count=6)

# Abductors: MAINTENANCE, not a driver. Cable abduction with the ankle strap, so
# no grip. 3 sets x 2 days = 6/wk. Keep the LOAD high -- strength is maintained
# by training at the same weight, not the same volume.
_ABDUCTION = _reps("Cable Hip Abduction", reps=24, weight=60, count=3)

# QL raise -- lateral trunk, no grip, no hinge.
_QL_RAISE = _reps("QL Raise", reps=16, weight=0, count=3)

# Ring dips: support grip only, not the crush grip the RDL and the pulls tax.
_RING_DIP = _reps("Ring Dip", reps=8, weight=0, count=3)

# Calves: a 40 lb kettlebell held in ONE hand, 35 reps per side (70 total). It is
# a one-arm hold, but 40 lb is not enough to tire the hands, so it does not count
# against the grip cluster -- and putting it here keeps three sets off the big
# days, which are the ones under time pressure.
_CALF = _reps("Standing Calf Raise", reps=70, weight=40, count=3)

# Neck (harness on the cable). Front / back / sides, 20 reps @ 30, 4 sets each.
# PROGRESSION IS BY SETS: each direction is its own muscle, so each gets its own
# 12-set weekly floor -- ramp to 6 sets/session per direction. The gate is
# normally DELAYED soreness landing on a jujitsu day; with no jujitsu in month
# one that gate is gone, so this is the month to ramp it fast. Lateral is one set
# = BOTH sides, so its reps are the total (40).
_NECK_FLEXION = _reps("Neck Flexion", reps=20, weight=30, count=4)
_NECK_EXTENSION = _reps("Neck Extension", reps=20, weight=30, count=4)
_NECK_LATERAL = _reps("Neck Lateral Flexion", reps=40, weight=30, count=4)
_NECK_BLOCK = [_NECK_FLEXION, _NECK_EXTENSION, _NECK_LATERAL]


@dataclass
class Day:
    """One training day: a name suffix and its ordered list of blocks."""

    suffix: str
    blocks: list[list[Move]] = field(default_factory=list)

    @property
    def plan_name(self) -> str:
        """Full workout Name as shown in FitNotes."""
        return f"{PLAN_PREFIX} - {self.suffix}"


def _big_day(suffix: str, *, light: bool) -> Day:
    """A Mon/Wed/Fri day: one superset per heavy movement, plus the pull.

    The four heavy movements (RDL, split squat, hyper, Nordic) each get their own
    block so none of them rests against another taxing the same tissue. Only the
    Nordic is paired with a grip movement, because it costs neither grip nor back.

    Args:
        suffix: Weekday name.
        light: Wednesday runs the same shape at reduced VOLUME rather than
            dropping movements -- alternating hinge and non-hinge days is what
            does not recover. The RDL keeps its working weight and loses two
            sets; only the split squat, which is mid-ramp, goes lighter (and
            then only to run the paused version).
    """
    return Day(
        suffix,
        [
            # Hinge first, on the freshest back. The stretch rides its rest at
            # the bar, warming the hips for the split squat that follows.
            [_RDL_LIGHT if light else _RDL, _COUCH],
            # The front rack ramp, with grip-free pressing and the tib bar.
            [_SPLIT_SQUAT_PAUSED if light else _SPLIT_SQUAT, _INCLINE, _TIB],
            # Hypers on their own, resting against grip-free, hamstring-free work.
            [_HYPER, _HSPU, _L_SIT],
            # The one deliberate pairing: the pull rides the Nordic's rest.
            [_NORDIC, _LOW_ROW if light else _PULLDOWN],
        ],
    )


def _light_day(suffix: str) -> Day:
    """A Tue/Thu day: short, and carrying no grip, hamstring or extension work."""
    return Day(
        suffix,
        [
            [_SIDE_HYPER, _RING_DIP, _CALF],
            [_ABDUCTION, _QL_RAISE],
            list(_NECK_BLOCK),
        ],
    )


def _days() -> list[Day]:
    """Build the five-day program (Mon/Wed/Fri big, Tue/Thu light)."""
    friday = _big_day("Friday", light=False)
    # Posterior-chain decompression to finish the week.
    friday.blocks.append([_hold("Elephant Walk", 240)])
    return [
        _big_day("Monday", light=False),
        _light_day("Tuesday"),
        _big_day("Wednesday", light=True),
        _light_day("Thursday"),
        friday,
    ]


DAYS = _days()

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "chi"


def _build_move(move: Move, mappings: ExerciseMapping) -> dict[str, Any]:
    return build_exercise(
        move.name,
        move.sets,
        mappings,
        focus=move.focus,  # type: ignore[arg-type]
        secondary_focus=move.secondary_focus,  # type: ignore[arg-type]
        warmups=move.warmups,
    )


def build_day(day: Day, mappings: ExerciseMapping) -> dict[str, Any]:
    """Build one day's workout dict from its block definitions.

    Args:
        day: Day definition (suffix + ordered blocks of Moves).
        mappings: ExerciseMapping loaded from the exercises folder.

    Returns:
        Complete workout dict ready to write to a .fnw file.
    """
    supersets = [
        build_superset([_build_move(move, mappings) for move in block]) for block in day.blocks
    ]
    return build_workout_from_supersets(day.plan_name, supersets)


def build_all(mappings: ExerciseMapping) -> dict[str, dict[str, Any]]:
    """Build all five days, keyed by full plan name."""
    return {day.plan_name: build_day(day, mappings) for day in DAYS}


def main() -> None:
    """Generate the five CHI days and write them to plans/chi/."""
    parser = argparse.ArgumentParser(description="Generate the CHI plan")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory to write the .fnw files (default: {_DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    mappings = load_exercise_mappings()
    for name, workout in build_all(mappings).items():
        output_path = args.output_dir / f"{name}.fnw"
        write_workout_file(workout, output_path)
        print(f"Wrote {name} -> {output_path}")


if __name__ == "__main__":
    main()
