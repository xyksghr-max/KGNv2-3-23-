# KGN-main Agent Rules

This file is the first project memory file every Codex/agent should read.
It records stable rules only. Do not use it as a session log.

## Project Identity

- Thesis topic: Research on 6D Grasp Detection Based on Monocular RGB-D Keypoints.
- Main technical line: keypoint-based RGB-D grasp prediction, 2D keypoint prediction, geometric pose recovery, and controlled experiments.
- Current main codebase: KGN-main, based on KGNv2 with local improvements.
- KGN-Pro is a theoretical and code reference, not the current main implementation.

## Workspaces

- Local main workspace: `/home/xyk/KGN-main`.
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`.
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`.
- GitHub repository: `https://github.com/xyksghr-max/KGNv2-3-23-.git`.

## Current Workflow

Default workflow:

1. Modify, audit, document, and run light checks locally in `/home/xyk/KGN-main`.
2. Commit and push through GitHub.
3. Pull the target branch on the cloud server.
4. Run GPU smoke training, formal training, and `test.py` evaluation on the cloud server.
5. Compress only one experiment directory on the cloud:
   `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`.
6. Download the tarball with FileZilla.
7. Extract locally to `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`.
8. Analyze logs, metrics, analysis files, and visualizations locally.

Remote Codex on the cloud is only a backup for environment checks, short commands,
and log inspection. It is not the main code modification entry.

## Absolute Rules

- Do not delete, overwrite, or clean untracked files unless the user explicitly asks.
- Do not delete or submit `data/`, `exp/`, `pretrained_weights/`, or `KGN-Pro-main/`.
- Do not submit checkpoints, tarballs, large logs, generated datasets, PDFs, local caches, or credential files.
- Do not use `git add .`; always add explicit files.
- Do not treat `KGN-Pro-main` as a complete KGN-Pro implementation.
- Do not migrate `KGN-Pro-main` as a whole.
- Do not replace the current KGN-main test, inference, or pose-recovery main chains with KGN-Pro-main files.
- Do not write T3.1 as a verified effective module until formal cloud training, testing, and controlled experiments are complete.
- Do not mix smoke results with formal effectiveness conclusions.
- Do not compare experiments with different data sources, training budgets, or inference parameters in one main conclusion table.
- Do not record tokens, passwords, SSH private keys, Codex auth files, cookies, or GitHub credentials in project files.

## Branch And Commit Rules

- Start new feature, fix, validation, or documentation work from the latest confirmed branch.
- Use one branch for one clear task.
- Keep changes small, reviewable, and reversible.
- Use commit prefixes:
  - `feat:` for new functionality.
  - `fix:` for fixes.
  - `docs:` for documentation.
  - `chore:` for config or ignore-rule maintenance.
- After each meaningful task, record the resulting state in the appropriate status or documentation file.

## Startup Reading Order

For every new conversation or after context compaction, read:

1. `AGENTS.md`
2. `STATUS.md`
3. `CURRENT_TASK.md`
4. `BUGS_AND_RISKS.md`
5. `docs/DECISIONS.md`

Then read task-specific long documents:

- `已完成工作.md` for full project history and module status.
- `新阶段继续改进计划.md` for the forward roadmap.
- `docs/T1-KGNPro资产接入准备.md` for KGN-Pro-main migration boundaries.
- `docs/实验命令记录.md` for experiment commands and protocols.
- `docs/云服务器现状.md` and `docs/云服务器实验命令记录.md` for cloud environment and execution state.
- `docs/SSH免密和远程Codex.md` for SSH and remote Codex notes.

## Required First Checks

Before editing or running a meaningful task, check:

- `pwd`
- `git status --short --branch`
- `git log --oneline -5`
- current branch and upstream
- whether user/untracked changes exist
- whether the task touches protected directories or generated outputs

If the working tree is dirty, work with the existing changes and do not clean them.
