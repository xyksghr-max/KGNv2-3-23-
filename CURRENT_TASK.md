# Current Task

Last updated: 2026-04-23

## Task

Implement T3.5 Confidence-Aware Target Selection on top of the documented T3.4 nearest-cost branch.

## Goal

Add a low-risk KGN-Pro-lite combined training-side enhancement that keeps the current
deterministic test chain stable while making target selection use the existing
`conf_branch` signal.

## In Scope

- Branch: `feat/t3.5-conf-aware-target-selection`.
- Base commit: `1fb0084 docs: record t34 result interpretation against t2 baselines`.
- Files in scope:
  - `src/lib/opts.py`
  - `src/lib/models/prob_pose_aux_loss.py`
  - `src/lib/trains/grasp_pose.py`
- Target modes:
  - `first`: compatibility path, same flattened valid-grasp order as `134cd27`.
  - `random`: sample up to `prob_pose_max_grasps` valid grasps with PyTorch RNG.
  - `nearest_cost`: choose by detached 2D keypoint geometry cost.
  - `nearest_conf`: rerank a geometry-topk pool by detached confidence-aware selection score.
- Diagnostics:
  - `prob_pose_target_valid_total`
  - `prob_pose_target_selected_count`
  - `prob_pose_target_select_cost_mean`
  - `prob_pose_target_geom_cost_mean`
  - `prob_pose_target_conf_quality_mean`
  - `prob_pose_target_mode_id`

## Out Of Scope

- No changes to `test.py`, `decode.py`, `keypoint_graspnet.py`, or `pose_recover/`.
- No KGN-Pro-main directory migration.
- No `KGN-Pro-main/src/lib/trains/base_trainer.py` migration.
- No generated data, checkpoints, tarballs, or large logs.
- No formal effectiveness claim before T3.5 cloud smoke and b1/e5 runs complete.

## Current State

- T3.5 local code implementation is complete.
- Local static checks passed:
  - `python -m py_compile src/lib/opts.py src/lib/models/prob_pose_aux_loss.py src/lib/trains/grasp_pose.py`
  - `rg "nearest_conf|prob_pose_target_conf_min|prob_pose_target_geom_cost_mean|prob_pose_target_conf_quality_mean" src/lib`
- T3.4 remains the last completed cloud-validated branch.
- T3.5 has not yet been smoke-tested on the cloud.

Current upstream reference metrics:

| Mode | Best | Last | Interpretation |
| --- | --- | --- | --- |
| `random` | `0.1053 / 0.1229 / 0.4850` | `0.1096 / 0.1291 / 0.5060` | negative/control |
| `nearest_cost` | `0.1954 / 0.2080 / 0.7480` | `0.1954 / 0.2080 / 0.7480` | positive; near T2 strong-baseline range |

Primary comparison targets:

- `paper2-clean baseline`: `0.1013 / 0.0922 / 0.4920`.
- `d4ff8ca no-conf base`: `0.1597 / 0.1585 / 0.6440`.
- `old T2 best + P3 on`: `0.2021 / 0.2088 / 0.7270`.
- `T2 cloud repeat model_last + P3 on`: `0.1837 / 0.1998 / 0.7530`.
- `T2 local repeat model_best + P3 on`: `0.2090 / 0.2320 / 0.7430`.

Current conclusion:

- `nearest_cost` is the current positive T3.4 base to build from.
- `nearest_conf` is implemented as the next low-risk KGN-Pro-lite combined step.
- T3.5 still needs cloud smoke, b1/e5 training, and deterministic evaluation before any effectiveness conclusion.

## Next Step

Run cloud smoke for `nearest_cost` compatibility and `nearest_conf` validation, then run
the `nearest_conf` b1/e5 short-budget experiment and best/last deterministic evaluation.
