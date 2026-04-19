# Project Decisions

This file records stable project decisions so future sessions do not reopen
settled questions after context compaction.

## 2026-04-19 Main Workspace And Workflow

Decision:

- The main development workspace is `/home/xyk/KGN-main`.
- GitHub is the version transfer, branch archive, and rollback anchor.
- The cloud workspace `/root/autodl-tmp/KGN-main` is for training and evaluation.
- Remote Codex on the cloud is only a backup for environment checks and logs.

Why:

- Local Codex is more stable for code modification and documentation.
- Cloud resources are best used for GPU training and evaluation.
- GitHub provides a clean synchronization and rollback boundary.

Consequences:

- Code changes should be made locally first.
- Cloud training starts after pulling the target branch.
- Cloud results are returned as single experiment directories.

Status:

- active

## 2026-04-19 KGN-main Remains The Main Repository

Decision:

- `KGN-main` remains the main development, training, testing, and evaluation repository.
- `KGN-Pro-main` is a local and cloud reference directory only.

Why:

- KGN-main has the working KGNv2-based pipeline and local improvements.
- KGN-Pro-main is incomplete as an implementation of the KGN-Pro paper.
- KGN-Pro-main training side has useful ideas, but its testing and inference chains largely retain KGNv2 logic.

Consequences:

- Do not migrate KGN-Pro-main as a whole.
- Do not submit KGN-Pro-main.
- Only migrate audited, local, useful assets with new KGN-main-compatible integration.

Status:

- active

## 2026-04-19 T2 Is The Latest Verified Strong Mainline

Decision:

- The latest verified strong mainline is T2:
  `exp/grasp_pose/p2_conf_single_r512_e5_800200/model_best.pth`
  with `conf_fusion_alpha = 0.7` and `conf_fusion_min_conf = 0.3`.

Why:

- This is the current confirmed standard baseline after geometry-aware confidence and inference-side calibration.
- Earlier P3 best, P4-lite-v2, and the "fine-tune 3 epochs without pose_reg" line have different roles and must not replace this baseline.

Consequences:

- New method comparisons should default to T2 `model_best.pth + a0.7/g0.3`.
- Historical strong references can be cited for attribution, not as the default baseline.

Status:

- active

## 2026-04-19 T3.1 Is Implemented But Not Verified

Decision:

- T3.1 is a training-side probabilistic pose auxiliary loss prototype.
- T3.1 has been implemented, committed, pushed, and synchronized to the cloud.
- T3.1 has not completed formal cloud training, testing, controlled comparison, or conclusion validation.

Why:

- The code exists and local/static/smoke-style probes were performed.
- Formal evidence is still missing.

Consequences:

- T3.1 can be described as an implemented prototype pending validation.
- T3.1 must not be described as verified effective or as the new mainline.
- The next T3.1 step is cloud Stage V0 plus smoke-off/smoke-on once the cloud server is available.

Status:

- active

## 2026-04-19 Single Experiment Directory Transfer

Decision:

- Cloud experiment results must be transferred one experiment directory at a time.

Why:

- Compressing all of `exp/grasp_pose/` is slow, risky, and mixes unrelated experiments.
- Single-directory transfer preserves experiment identity and avoids accidental large transfers.

Consequences:

- Cloud source: `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`.
- Local target: `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`.
- Do not submit `exp/` to GitHub.

Status:

- active

## 2026-04-19 Branching Discipline

Decision:

- New features, fixes, validation adjustments, and documentation tasks should start from the latest confirmed branch.
- Each branch should contain one clear task.

Why:

- The project needs reversible, auditable progress.
- Training and evaluation are expensive enough that mixed changes make attribution difficult.

Consequences:

- Do not keep adding unrelated changes directly to the T3.1 baseline branch.
- Use explicit `git add <file>` only.
- Do not use `git add .`.

Status:

- active
