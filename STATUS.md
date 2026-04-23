# KGN-main Current Status

Last updated: 2026-04-23
Status commit at update: working tree on T3.5 local implementation

## Branch-Local T3.5 Status

- Current local branch: `feat/t3.5-conf-aware-target-selection`.
- Branch base: `1fb0084 docs: record t34 result interpretation against t2 baselines`.
- Branch role: T3.5 confidence-aware target selection training-side combined experiment.
- Code status: local implementation complete and static checks passed.
- Cloud status: not started yet for T3.5.
- Scope guard: this branch keeps the T3.4 deterministic test/inference chain unchanged.

T3.5 local implementation scope:

- extends `prob_pose_target_mode` with `nearest_conf`
- adds `--prob_pose_target_conf_min`
- keeps `first/random/nearest_cost` behavior compatible
- adds confidence-aware target selection inside `ProbPoseAuxLoss`
- keeps `w2d = ones_like(...)` and does not reopen the T3.3 `w2d` line
- adds diagnostics:
  - `prob_pose_target_geom_cost_mean`
  - `prob_pose_target_conf_quality_mean`
- threads `output.get('conf', None)` from the trainer into `ProbPoseAuxLoss`

T3.5 local verification completed:

- `python -m py_compile src/lib/opts.py src/lib/models/prob_pose_aux_loss.py src/lib/trains/grasp_pose.py`
- `rg "nearest_conf|prob_pose_target_conf_min|prob_pose_target_geom_cost_mean|prob_pose_target_conf_quality_mean" src/lib`

T3.5 next validation steps:

- cloud `nearest_cost` b1/e1 smoke for compatibility
- cloud `nearest_conf` b1/e1 smoke for new-mode validation
- cloud `nearest_conf` b1/e5 + best/last deterministic evaluation

## Branch-Local T3.4 Status

T3.4 cloud results, all b1/e5 short-budget attribution:

- `t34_random_b1_single_r512_e5_val1_p20_g4`
  - best: `0.1053 / 0.1229 / 0.4850`
  - last: `0.1096 / 0.1291 / 0.5060`
  - interpretation: negative/control result; random GT grasp selection injects noisy supervision.
- `t34_nearest_b1_single_r512_e5_val1_p20_g4`
  - best: `0.1954 / 0.2080 / 0.7480`
  - last: `0.1954 / 0.2080 / 0.7480`
  - interpretation: positive KGN-Pro-inspired target-matching result; close to T2 strong baselines but not a new overall champion.

Candidate-level comparison against the main T2 strong baselines:

| Experiment | GSR/GCR/OSR | decoded | score-filtered | PnP failed | accepted | successful preds | accepted reproj mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `old T2 best` | `0.2021 / 0.2088 / 0.7270` | 99972 | 59468 | 780 | 58688 | 11856 | 0.6825 |
| `T2 cloud repeat last + P3 on` | `0.1837 / 0.1998 / 0.7530` | 99382 | 64225 | 2245 | 61980 | 11383 | 1.0848 |
| `T2 local repeat best + P3 on` | `0.2090 / 0.2320 / 0.7430` | 99607 | 65963 | 1036 | 64927 | 13572 | 0.7236 |
| `T3.4 nearest_cost` | `0.1954 / 0.2080 / 0.7480` | 99819 | 61509 | 1081 | 60428 | 11805 | 0.6741 |

Current baseline policy:

- Primary method comparison should use `paper2-clean`, `d4ff8ca no-conf base`, and the T2 strong baselines.
- `KGN-main internal kgnv2base` remains a historical/internal reference, not the main baseline for T3.4 claims.
- The main T3.4 claim is not "better than T3.2b-fix"; it is "nearest-cost multi-grasp target matching brings the KGN-Pro-inspired training-side path into the T2 strong-baseline range."

Known local untracked files remain user/local files and must not be deleted or submitted:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`
- `邢亚坤-中期报告.doc`

T3.4 touched only:

- `src/lib/opts.py`
- `src/lib/models/prob_pose_aux_loss.py`
- `src/lib/trains/grasp_pose.py`

The older status below is retained as historical context from the `134cd27` lineage.

## Current Repositories

- Local main workspace: `/home/xyk/KGN-main`.
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`.
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`.
- GitHub repository: `https://github.com/xyksghr-max/KGNv2-3-23-.git`.

## Current Git State

- Current local branch: `feat/t3.5-conf-aware-target-selection`.
- Current upstream branch: none yet.
- Current latest known committed code base under this branch: `1fb0084 docs: record t34 result interpretation against t2 baselines`.
- Current local branch role: T3.5 confidence-aware target selection implementation and upcoming cloud validation.
- Current cloud T3.4 task: completed; T3.5 has not been pulled or run on the cloud yet.

Known local untracked files at the time this status was created:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`

These are treated as user/local files. Do not delete, overwrite, or submit them unless explicitly requested.

## Current Experiment Facts

All b1/e5 results below are short-budget attribution results, not final thesis-scale results.

- `paper2-clean baseline b1/e5`: `0.1013 / 0.0922 / 0.4920`.
- `d4ff8ca no-conf base b1/e5`: `0.1597 / 0.1585 / 0.6440`.
- `old T2 best local-train/cloud-test + P3 on`: `0.2021 / 0.2088 / 0.7270`.
- `T2 cloud repeat model_last + P3 on`: `0.1837 / 0.1998 / 0.7530`.
- `T2 cloud repeat model_last + P3 off`: `0.1618 / 0.1483 / 0.6840`.
- `T2 local repeat model_best + P3 on`: `0.2090 / 0.2320 / 0.7430`.
- `T3.4 nearest_cost best/last + P3 on`: `0.1954 / 0.2080 / 0.7480`.
- `KGN-main internal kgnv2base b1/e5`: `0.1995 / 0.2240 / 0.7670` as historical/internal reference.

Current interpretation:

- T2 remains the strongest verified mainline family under the b1/e5 attribution setting.
- `T3.4 nearest_cost` is a positive KGN-Pro-inspired result and should be compared mainly with T2 strong baselines, not only with T3.2b-fix.
- `T3.4 random` is a negative/control result and should not be continued as a main path.
- `KGN-main internal kgnv2base` is not the official paper2-clean baseline and should not dominate the current T3.4 comparison story.

## T3.1 Status

T3.1 is implemented but not verified as an effective module.

- Name: training-side probabilistic pose auxiliary loss prototype.
- Prototype design: complete.
- Code integration: complete.
- Local commit: complete.
- GitHub push: complete.
- Cloud control/prob runs: completed for short-budget attribution.
- Formal effectiveness validation: not complete.

Latest short-budget attribution results:

- `ctrl_t2off + fusion`: `0.0929 / 0.1138 / 0.4050`.
- `ctrl_t2off + nofusion`: `0.0729 / 0.0629 / 0.2850`.
- `prob_on_signal + fusion`: `0.1216 / 0.1497 / 0.5870`.
- `prob_on_signal + nofusion`: `0.1185 / 0.1336 / 0.5580`.

T3.1 must be described as:

- "prototype implemented, with recovery-style positive signal relative to `ctrl_t2off`, but not verified effective against the strong internal baseline"

It must not be described as:

- "verified effective"
- "completed successful improvement"
- "new default mainline"

Key files:

- `src/lib/models/prob_pose_aux_loss.py`
- `src/lib/models/monte_carlo_pose_loss.py`
- `src/lib/third_party/epropnp/pnp/`
- `src/lib/datasets/sample/grasp_pose.py`
- `src/lib/opts.py`
- `src/lib/trains/grasp_pose.py`

## Cloud State

The cloud server is the training/evaluation executor:

- workspace: `/root/autodl-tmp/KGN-main`
- conda environment: `kgnv2`
- GPU: RTX 4090 24GB
- trusted data: local-uploaded `data/ps_grasp_single_1k`
- latest completed T3.4 cloud branch: `feat/t3.4-multigrasp-target-matching @ 468cd48`
- latest completed T3.4 train exp_ids:
  - `t34_random_b1_single_r512_e5_val1_p20_g4`
  - `t34_nearest_b1_single_r512_e5_val1_p20_g4`
- latest completed T3.4 test exp_ids:
  - `t34_random_best_test_a07_g03_d02_a30`
  - `t34_random_last_test_a07_g03_d02_a30`
  - `t34_nearest_best_test_a07_g03_d02_a30`
  - `t34_nearest_last_test_a07_g03_d02_a30`

The cloud server may be powered off. Do not assume it is available until checked.

When the cloud server is available, the next default action is:

1. verify no leftover T3.4 process is running before starting new jobs
2. only run a new job from a newly agreed branch/plan
3. if continuing from T3.4, prefer `nearest_cost` as the base and keep `random` as a negative control only

## Experiment Transfer Rule

Cloud experiment directory:

- `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`

Local extraction directory:

- `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`

Only compress and transfer one `<exp_id>` directory at a time. Never compress the whole cloud `exp/grasp_pose/`.

## Next Default Action

If the cloud server is available: recover the `d4ff8ca no-conf base` result and run the no-conf test if needed.
If the cloud server is not available: do local documentation, planning, or result analysis only.
