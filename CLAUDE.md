# fitnotes-assistant

Personal tooling around FitNotes workout exports (`.fnw` files) — exercise
mappings, weekly volume analysis, program builders.

## How to collaborate

Sessions are usually driven from the Claude mobile app, which doesn't see
permission prompts. `.claude/settings.json` pre-approves `Edit`, `Write`,
and a wide list of Bash commands — just edit freely. Flag before adding
tools or network calls that would need *new* prompts.

**Never use `cd`** — the sandbox blocks it. Use absolute paths or
tool-native flags:
- `uv --directory /Users/wcb/personal/workouts/scripts run <cmd>`
- `pytest /Users/wcb/personal/workouts/scripts`

The Bash working directory stays at the project root for the whole session.

**No code review** — changes go straight to `main`. Tests are the safety
net, so write them generously when touching `scripts/`. Force-push is
allowed but a last resort.

**Commit and push proactively** once a change is working. Split by concern
(a fix and its tests are two commits). Deviate only when a change feels
risky or unfinished.

### Prefer subagents — heavily

Session cost scales **quadratically** with transcript length, so push work
into subagents via `Agent` to keep the parent short:
- Codebase questions / file lookups → `Explore`
- Multi-step research or refactors → `general-purpose`
- Non-trivial implementation planning → `Plan`
- Run independent subagents **in parallel**

**First move for any codebase question is `Agent(Explore, …)`, not `grep`
or `Read`** — even when one lookup feels like overkill. The trap is "just
one quick grep" turning into five, all of which the parent re-reads every
turn for the rest of the session. Ask the subagent for a 1–2 sentence
summary, not raw output.

**Don't `Read` `.fnw` files** — they're large and bloat the transcript.
Query with `jq`/`grep` via Bash and surface only the result.

## Repo layout

- `plans/` — per-gym workout plans (`pa/`, `pit/`, `wh/`, …) used while
  traveling
- `exercises/` — exercise definitions and metadata
- `scripts/` — uv-managed Python for parsing `.fnw` and generating programs
- `*_Exercises.txt`, `Exercise_ideas.md`, `ATG_Standards.txt`, `big3.txt` —
  notes, brainstorms, standards
- `utilities` — jq one-liners for ad-hoc `.fnw` analysis
