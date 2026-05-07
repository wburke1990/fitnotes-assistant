# fitnotes-assistant

Personal tooling around FitNotes workout exports (`.fnw` files) — exercise
mappings, weekly volume analysis, program builders. Long-term aspiration:
polish enough to ship as an App Store companion or PR upstream into FitNotes.

## How to collaborate in this repo

Sessions in this repo are usually driven from the Claude mobile app in
remote-control mode. The phone does not see permission prompts, so the repo
pre-approves common actions in `.claude/settings.json`. Don't add tools or
network calls that require new prompts without flagging it first.

We are running a **no-code-review** workflow: changes go straight to `main`.
The safety net is tests, not review — so write tests generously, especially
when touching `scripts/`. Force-push to `main` is allowed (and sometimes
necessary) but should be a last resort.

### Prefer subagents — heavily

Claude session cost scales roughly **quadratically** with transcript length
(every turn re-reads the full history). The cheapest way to keep a long
remote session responsive is to push work into subagents via the `Agent`
tool, so the parent session stays short.

Defaults:
- **Codebase questions / file lookups** → `Explore` subagent
- **Multi-step research or refactors** → `general-purpose` subagent
- **Non-trivial implementation planning** → `Plan` subagent
- Run independent subagents **in parallel** (multiple `Agent` calls in one
  message) whenever the work doesn't depend on prior results

Rule of thumb: if a task needs more than ~3 tool calls of exploration,
delegate it. Have the subagent return a 1–2 sentence summary rather than
dumping raw output into the parent transcript.

## Repo layout

- `plans/` — self-contained workout plans for different gyms in different
  cities. Each subfolder (`pa/`, `pit/`, `wh/`, etc.) is one gym's program
  used while traveling.
- `exercises/` — exercise definitions and metadata
- `scripts/` — Python (uv-managed) tooling for parsing `.fnw` files and
  generating workout programs
- `*_Exercises.txt`, `Exercise_ideas.md`, `ATG_Standards.txt`, `big3.txt` —
  notes, brainstorms, standards
- `utilities` — jq one-liner notes for ad-hoc `.fnw` analysis
