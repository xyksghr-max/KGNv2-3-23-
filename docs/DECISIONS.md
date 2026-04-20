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

## 2026-04-21 Official Clean Baseline And Internal Strong Baseline Are Different

Decision:

- `paper2-clean baseline` refers only to the official-clean KGN paper2 repository path, with the minimal NumPy compatibility fix.
- `KGN-main internal kgnv2base` refers to a strong internal baseline trained/evaluated in the KGN-main code state, with no `conf_branch`, no `conf_fusion`, and no `prob_pose_loss`.
- These two baselines must not be renamed into each other.

Why:

- The official-clean b1/e5 baseline is around `0.1013 / 0.0922 / 0.4920`.
- The KGN-main internal kgnv2base b1/e5 result is around `0.1995 / 0.2240 / 0.7670`.
- KGN-main includes historical data, test, detector, decode, analysis, and training-path changes that are not all controlled by `--conf_branch`.

Consequences:

- `paper2-clean` remains the official-clean baseline for comparison to the released paper2 code.
- `KGN-main internal kgnv2base` is a strong internal baseline and must be treated as an attribution target.
- Do not present paper2-clean vs KGN-main T2 as a strict single-variable T2 ablation without caveats.

Status:

- active

## 2026-04-21 Prioritize d4ff8ca No-Conf Attribution Before Paper2-Clean T2 Migration

Decision:

- First complete the `d4ff8ca no-conf base b1/e5` experiment in `/root/autodl-tmp/KGN-main`.
- Only after seeing that result decide whether to migrate T2 into `/root/autodl-tmp/KGN-paper2-clean` for a stricter `paper2-clean + T2-only` run.

Why:

- The no-conf run is cheaper and directly tests whether the strong baseline already exists at the T2 commit when T2/P3 runtime switches are off.
- If no-conf base is weak, T2 evidence against official clean is already much clearer.
- If no-conf base is strong, the strict T2-only migration becomes more important for thesis-grade attribution.

Consequences:

- Current cloud branch is `diag-t2-d4ff8ca-base-ablation @ d4ff8ca`.
- Current no-conf training exp_id is `diag_t2_d4ff8ca_base_no_conf_b1_single_r512_e5_val1_p20`.
- Expected no-conf test exp_id is `diag_t2_d4ff8ca_base_no_conf_b1_best_test_d02_a30`.

Status:

- active

## 2026-04-21 T3.2 Should Challenge The Strong Internal Baseline

Decision:

- Do not continue tuning T3.1 only against weak `ctrl_t2off` control results.
- The next T3 direction should preferentially test a cleaner `KGNv2-base + prob_pose_loss` design that does not depend on `conf_branch` or `conf_fusion`.

Why:

- T3.1 recovered performance relative to `ctrl_t2off`, but did not beat `KGN-main internal kgnv2base`.
- Removing `conf_fusion` did not rescue `ctrl_t2off` or `prob_on_signal`; the weaker behavior is not simply a P3 fusion artifact.

Consequences:

- T3.1 may be described as having a recovery-style positive signal, not as verified effective.
- T3.2 should be planned as a clean strong-baseline challenge rather than more conf-fusion parameter search.

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
- Later short-budget cloud control/prob runs found recovery-style signal relative to `ctrl_t2off`, but T3.1 still has not completed effectiveness validation against the strong internal baseline.

Why:

- The code exists and local/static/smoke-style probes were performed.
- Formal strong-baseline evidence is still missing.

Consequences:

- T3.1 can be described as an implemented prototype with recovery-style positive signal relative to `ctrl_t2off`.
- T3.1 must not be described as verified effective or as the new mainline.
- The next T3 direction should be a clean strong-baseline challenge, as recorded in the 2026-04-21 decision.

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
