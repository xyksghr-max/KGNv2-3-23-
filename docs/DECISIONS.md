# Project Decisions

This file records stable project decisions so future sessions do not reopen
settled questions after context compaction.

## 2026-04-23 T3.4 Result Interpretation Uses T2 Strong Baselines

Decision:

- T3.4 `nearest_cost` is a positive b1/e5 attribution result, but not a new overall strongest mainline.
- T3.4 `random` is a negative/control result and should not be carried forward as a main method.
- T3.4 should be compared primarily against `paper2-clean`, `d4ff8ca no-conf base`, and T2 strong baselines.
- `KGN-main internal kgnv2base` remains a historical/internal reference, not the dominant comparison target for T3.4 claims.

Why:

- T3.4 `nearest_cost` reached `0.1954 / 0.2080 / 0.7480`, close to the T2 strong-baseline range.
- The main T2 references are:
  - old T2 best + P3 on: `0.2021 / 0.2088 / 0.7270`
  - T2 cloud repeat model_last + P3 on: `0.1837 / 0.1998 / 0.7530`
  - T2 local repeat model_best + P3 on: `0.2090 / 0.2320 / 0.7430`
- Candidate-level analysis shows T3.4 `nearest_cost` has strong geometry quality (`accepted_reproj_mean = 0.6741`) but still does not dominate every T2 reference in every metric.
- The project goal is not to prove "prob_pose_loss alone beats T3.2b-fix"; it is to gradually build a KGN-Pro-lite path combining confidence/correspondence weighting, EPro-PnP/MC loss, probabilistic inference, x2d, and multi-grasp target matching where feasible.

Consequences:

- Future writeups should say: T3.4 validates `nearest_cost` multi-grasp target matching as a useful KGN-Pro-inspired training-side module under b1/e5 attribution.
- Do not write that T3.4 fully reproduces KGN-Pro or surpasses all T2 baselines.
- The next method branch should build from T3.4 `nearest_cost` evidence toward a combined KGN-Pro-lite route, while keeping the current deterministic test chain stable unless a dedicated inference task is opened.

Status:

- active

## 2026-04-23 T3.4 Starts From Clean T3.2b-Fix Lineage

Decision:

- T3.4 starts from `134cd27 fix: stabilize probabilistic pose auxiliary loss`.
- The T3.4 branch is `feat/t3.4-multigrasp-target-matching`.
- T3.4 implements only training-side target selection for `ProbPoseAuxLoss`.

Why:

- T3.3b and T3.3c were useful negative/diagnostic experiments but are not the best base for a new target-matching test.
- Starting from `134cd27` keeps the experiment closer to the stable T3.2b-fix line.
- Target matching is a smaller and cleaner KGN-Pro-inspired idea than migrating inference or pose-recovery chains.

Consequences:

- Do not stack T3.4 on top of T3.3c.
- Do not change `test.py`, `decode.py`, `keypoint_graspnet.py`, or `pose_recover/` for T3.4.
- Evaluate `first`, `random`, and `nearest_cost` as separate experiment modes.
- Treat all b1/e5 results as short-budget attribution until larger validation exists.

Status:

- completed for implementation and b1/e5 attribution

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
- `KGN-main internal kgnv2base` is a strong internal/historical reference and should not be confused with the official-clean baseline.
- For T3.4 and later KGN-Pro-inspired comparisons, the main practical baselines are `paper2-clean`, `d4ff8ca no-conf base`, and the T2 strong baselines; `KGN-main internal kgnv2base` is retained as a reference line rather than the dominant comparison target.
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
- The completed no-conf result is around `0.1597 / 0.1585 / 0.6440`, above paper2-clean but below the main T2 P3-on references.

Consequences:

- The no-conf result should be used as the main KGN-main no-confidence attribution baseline.
- It does not replace T2 P3-on as the strong mainline.
- It reduces the need to keep using `KGN-main internal kgnv2base` as the main comparison axis for T3.4.

Status:

- completed for b1/e5 attribution

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
