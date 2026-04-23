# Current Task

Last updated: 2026-04-23

## Task

Implement T3.4 Multi-Grasp Target Matching from clean code point `134cd27`.

## Goal

Add a minimal training-side target selection experiment for the probabilistic pose
auxiliary loss without changing the inference or evaluation chain.

T3.4 tests whether selecting different valid GT grasps for EPro-PnP supervision
helps the short-budget b1/e5 attribution setting.

## In Scope

- Branch: `feat/t3.4-multigrasp-target-matching`.
- Base commit: `134cd27 fix: stabilize probabilistic pose auxiliary loss`.
- Files in scope:
  - `src/lib/opts.py`
  - `src/lib/models/prob_pose_aux_loss.py`
  - `src/lib/trains/grasp_pose.py`
- Target modes:
  - `first`: compatibility path, same flattened valid-grasp order as `134cd27`.
  - `random`: sample up to `prob_pose_max_grasps` valid grasps with PyTorch RNG.
  - `nearest_cost`: choose by detached 2D keypoint geometry cost.
- Diagnostics:
  - `prob_pose_target_valid_total`
  - `prob_pose_target_selected_count`
  - `prob_pose_target_select_cost_mean`
  - `prob_pose_target_mode_id`

## Out Of Scope

- No changes to `test.py`, `decode.py`, `keypoint_graspnet.py`, or `pose_recover/`.
- No KGN-Pro-main directory migration.
- No `KGN-Pro-main/src/lib/trains/base_trainer.py` migration.
- No generated data, checkpoints, tarballs, or large logs.
- No formal effectiveness claim before cloud smoke and b1/e5 runs complete.

## Current State

- T3.4 code implementation is complete locally.
- Local static checks pass:
  - `python -m py_compile src/lib/opts.py src/lib/models/prob_pose_aux_loss.py src/lib/trains/grasp_pose.py`
  - `conda run -n kgnv2 python -m py_compile src/lib/opts.py src/lib/models/prob_pose_aux_loss.py src/lib/trains/grasp_pose.py`
- A small `kgnv2` target-selection smoke confirmed mode ids and selection counts for
  `first`, `random`, and `nearest_cost`.
- Cloud smoke training has not been run yet.

## Next Step

Commit and push T3.4, then on the cloud run b1/e1 smoke in this order:

1. `--prob_pose_target_mode first`
2. `--prob_pose_target_mode random`
3. `--prob_pose_target_mode nearest_cost`

If smoke is stable, run b1/e5 for `random` and `nearest_cost`, then evaluate best/last
with the existing deterministic test chain.
