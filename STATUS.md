# KGN-main Current Status

Last updated: 2026-04-23
Status commit at update: `d3d548f feat: add detached per-keypoint pose weights`

## Current Repositories

- Local main workspace: `/home/xyk/KGN-main`.
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`.
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`.
- GitHub repository: `https://github.com/xyksghr-max/KGNv2-3-23-.git`.

## Current Git State

- Current local branch: `feat/t3.3c-detached-per-kpt-w2d`.
- Current upstream branch: `origin/feat/t3.3c-detached-per-kpt-w2d`.
- Current latest known commit: `d3d548f feat: add detached per-keypoint pose weights`.
- Current local branch role: T3.3c result documentation and handoff to T3.4.
- Latest cloud-completed task: T3.3c detached per-keypoint w2d b1/e5 train+val.
- Next intended branch: `feat/t3.4-multigrasp-target-matching`, created from `134cd27`.

Known local untracked files at the time this status was created:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`

These are treated as user/local files. Do not delete, overwrite, or submit them unless explicitly requested.

## Current Experiment Facts

All b1/e5 results below are short-budget attribution results, not final thesis-scale results.

- `paper2-clean baseline b1/e5`: `0.1013 / 0.0922 / 0.4920`.
- `KGN-main internal kgnv2base b1/e5`: `0.1995 / 0.2240 / 0.7670`.
- `T2 cloud repeat model_last + P3 on`: `0.1837 / 0.1998 / 0.7530`.
- `T2 cloud repeat model_last + P3 off`: `0.1618 / 0.1483 / 0.6840`.
- `T2 local repeat model_best + P3 on`: `0.2090 / 0.2320 / 0.7430`.
- `T3.2b-fix model_last + P3 on`: `0.1673 / 0.2011 / 0.7400`.
- `T3.3a detached scalar w2d model_best/model_last + P3 on`: `0.1717 / 0.1953 / 0.6590`.
- `T3.3b gradient-enabled scalar w2d model_best + P3 on`: `0.1164 / 0.1427 / 0.5630`.
- `T3.3b gradient-enabled scalar w2d model_last + P3 on`: `0.0972 / 0.1385 / 0.5210`.
- `T3.3c detached per-keypoint w2d model_best/model_last + P3 on`: `0.1232 / 0.1456 / 0.4910`.

Current interpretation:

- T2 is clearly better than the official `paper2-clean` b1/e5 baseline under the recorded fast attribution setting.
- `KGN-main internal kgnv2base` is a strong internal baseline, not the official paper2-clean baseline.
- T2 independent contribution still needs attribution against either `d4ff8ca no-conf base` or `paper2-clean + T2-only`.
- P3/conf_fusion contributes positively for the T2 checkpoint, because T2 P3-on exceeds T2 P3-off.
- T3.3a is the best T3.3 variant so far, but still below T2 and T3.2b-fix object success.
- T3.3b and T3.3c are negative ablations: they verified their engineering paths but should not be described as effective improvements.

## T3.3 Series Status

T3.3 explored KGN-Pro-style correspondence weighting inside the training-side
probabilistic pose auxiliary loss.

- T3.3a: detached scalar `w2d`; stable, but not better than T2.
- T3.3b: gradient-enabled scalar `w2d`; gradient path verified, b1/e5 degraded.
- T3.3c: detached per-keypoint `w2d` with `kpt_conf`; cloud smoke and b1/e5
  completed, but performance degraded to `0.1232 / 0.1456 / 0.4910`.

Conclusion:

- T3.3c is complete as an engineering and ablation experiment.
- It should be written as stable but negative.
- Do not continue from T3.3c for the next feature branch.

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

## T3.4 Next Direction

T3.4-lite should test multi-grasp target matching / target selection without
carrying T3.3c's per-keypoint confidence head.

Branching decision:

- Create `feat/t3.4-multigrasp-target-matching` from `134cd27`.
- Use T2 as the strongest comparison baseline, not as the direct code base.
- Keep the test/inference chain unchanged.

Initial T3.4 experiment design:

- Add target selection modes inside `ProbPoseAuxLoss`.
- Start with a low-risk `random` valid-GT sampling mode.
- Optionally add `nearest_cost` after `random` is stable.
- Run b1/e1 smoke before b1/e5.

## Cloud State

The cloud server is the training/evaluation executor:

- workspace: `/root/autodl-tmp/KGN-main`
- conda environment: `kgnv2`
- GPU: RTX 4090 24GB
- trusted data: local-uploaded `data/ps_grasp_single_1k`
- latest known T3.3c branch pulled on cloud:
  `feat/t3.3c-detached-per-kpt-w2d @ d3d548f`
- latest completed T3.3c train exp_id:
  `t33c_kptw2d_detach_b1_single_r512_e5_val1_p20_g4_nowarm`
- latest completed T3.3c test exp_ids:
  `t33c_kptw2d_b1_best_test_a07_g03_d02_a30`
  and `t33c_kptw2d_b1_last_test_a07_g03_d02_a30`

The cloud server may be powered off. Do not assume it is available until checked.

When the cloud server is available, the next default action is:

1. pull the upcoming T3.4 branch after it is pushed from local
2. run T3.4 b1/e1 smoke
3. if smoke is stable, run T3.4 b1/e5
4. compare against T2, T3.2b-fix, T3.3a, T3.3b, and T3.3c under the same b1/e5 attribution setting

## Experiment Transfer Rule

Cloud experiment directory:

- `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`

Local extraction directory:

- `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`

Only compress and transfer one `<exp_id>` directory at a time. Never compress the whole cloud `exp/grasp_pose/`.

## Next Default Action

Do local documentation commit for T3.3c result closure, then create
`feat/t3.4-multigrasp-target-matching` from `134cd27`.
