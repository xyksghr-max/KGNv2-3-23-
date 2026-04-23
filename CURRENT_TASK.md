# Current Task

Last updated: 2026-04-23

## Task

Document completed T3.4 Multi-Grasp Target Matching results and reset the comparison baseline policy.

## Goal

Record that T3.4 has completed cloud smoke, b1/e5 training, best/last evaluation,
result transfer, and local analysis. The main comparison target is now the T2 strong
baseline family, not only T3.2b-fix.

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

- T3.4 code implementation is complete.
- Local static checks passed:
  - `python -m py_compile src/lib/opts.py src/lib/models/prob_pose_aux_loss.py src/lib/trains/grasp_pose.py`
  - `conda run -n kgnv2 python -m py_compile src/lib/opts.py src/lib/models/prob_pose_aux_loss.py src/lib/trains/grasp_pose.py`
- A small `kgnv2` target-selection smoke confirmed mode ids and selection counts for
  `first`, `random`, and `nearest_cost`.
- Cloud b1/e1 smoke completed for `first`, `random`, and `nearest_cost`.
- Cloud b1/e5 completed for `random` and `nearest_cost`.
- Best/last deterministic evaluations completed and were transferred back locally.

Main T3.4 metrics:

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

- `nearest_cost` validates the KGN-Pro-style multi-grasp target matching idea under b1/e5 short-budget attribution.
- It should be described as close to and partially competitive with T2, not as a new overall strongest result.
- `random` should be kept as a negative target-selection control.

## Next Step

Update documentation and commit the result record. The next method branch should build
from the T3.4 `nearest_cost` evidence toward a KGN-Pro-lite combined path, while keeping
the test/inference chain stable unless a dedicated probabilistic-inference task is opened.
