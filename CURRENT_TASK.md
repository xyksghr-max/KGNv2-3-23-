# Current Task

Last updated: 2026-04-23

## Current Task

Close T3.3c-lite documentation and prepare T3.4-lite multi-grasp target
matching.

## Current Code State

- Current branch: `feat/t3.3c-detached-per-kpt-w2d`.
- Current commit: `d3d548f feat: add detached per-keypoint pose weights`.
- T3.3c code has been committed and pushed.
- Known untracked local files remain user/local files and must not be cleaned:
  - `KGNv2-Sim PROJECT_PROGRESS.md`
  - `implementation_plan.md`
  - `src/lib/third_party/__init__.py`

## T3.3c Result Summary

T3.3c-lite added a training-side `kpt_conf` head, `KptConfLoss`, and detached
per-keypoint `w2d` source for `ProbPoseAuxLoss`.

Completed checks and experiments:

- Local static checks and tensor checks passed before commit.
- Cloud smoke b1/e1 completed successfully.
- Cloud b1/e5 train+val completed for:
  `t33c_kptw2d_detach_b1_single_r512_e5_val1_p20_g4_nowarm`.
- Local evaluation completed for `model_best.pth` and `model_last.pth`.

T3.3c b1/e5 test result:

- `model_best.pth`, epoch 5: `0.1232 / 0.1456 / 0.4910`.
- `model_last.pth`, epoch 5: `0.1232 / 0.1456 / 0.4910`.

Interpretation:

- Engineering link is stable.
- `prob_pose_invalid_raw_rate = 0` and `prob_pose_w2d_grad_rate = 0` confirm
  the detached per-keypoint `w2d` path behaved as intended.
- Performance is lower than T3.3a, T3.2b-fix, and T2 under the recorded b1/e5
  attribution setting.
- T3.3c must be recorded as a stable but negative ablation, not an effective
  improvement.

## Next Task

Create a new branch for T3.4-lite from the clean T3.2b-fix / T3 base point:

```bash
git switch -c feat/t3.4-multigrasp-target-matching 134cd27
```

Rationale:

- `134cd27` already contains the stable training-side EPro-PnP / Monte Carlo
  pose auxiliary loss base.
- It does not include T3.3a/T3.3b/T3.3c `w2d` changes, so T3.4 can isolate
  multi-grasp target matching without carrying the negative T3.3c head.
- T2 remains the strongest comparison baseline, but T2 is not the direct code
  base for T3.4 because it does not contain `prob_pose_loss`.

## T3.4-lite Intended Scope

- Training-side target selection only.
- Add a controlled target selection mode in `ProbPoseAuxLoss`, such as:
  - `first`: current fixed first-k behavior.
  - `random`: random valid GT grasp sampling.
  - `nearest_cost`: nearest-cost / nearest-neighbor style target selection.
- Keep `test.py`, `decode.py`, `keypoint_graspnet.py`, and `pose_recover/`
  unchanged.
- Do not migrate `KGN-Pro-main` as a whole.
- Do not submit `data/`, `exp/`, checkpoints, tarballs, or large logs.
