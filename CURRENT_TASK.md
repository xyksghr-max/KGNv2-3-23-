# Current Task

Last updated: 2026-04-19

## Task

Build the minimal persistent memory pack for KGN-main to reduce context-compaction forgetting.

## Goal

Add lightweight project memory files that future Codex/agent sessions can read first:

- `AGENTS.md`
- `STATUS.md`
- `CURRENT_TASK.md`
- `BUGS_AND_RISKS.md`
- `docs/DECISIONS.md`

These files should prevent repeated audits, wrong status assumptions, unsafe Git actions,
incorrect experiment comparisons, and claims that unverified work is verified.

## In Scope

- Add documentation-only memory files.
- Record stable rules, current state, current task, known risks, and project decisions.
- Keep the content short enough to be useful after context compaction.

## Out Of Scope

- No algorithm code changes.
- No training or testing.
- No cloud execution.
- No hook, MCP, skill, or Claude setup.
- No changes to `data/`, `exp/`, `pretrained_weights/`, or `KGN-Pro-main/`.
- No handling of the ignored zero-byte `.codex` file.

## Current Blocker

Cloud verification is paused because the cloud server is not currently powered on.

## Completion Criteria

- The five memory files exist.
- The files reflect the current true project state:
  - T2 is the latest verified strong mainline.
  - T3.1 is implemented but not formally verified.
  - `KGN-Pro-main` is reference-only.
  - local development plus GitHub plus cloud training/evaluation is the default workflow.
- A light documentation check confirms the expected files exist.
- Git status shows only the intended new documentation files plus pre-existing untracked files.

## After Completion

If these files are accepted, update this task to the next active item, likely:

- `T3.1 cloud Stage V0 and smoke validation`, once the cloud server is available.
