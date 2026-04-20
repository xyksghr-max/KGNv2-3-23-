# KGN-main Current Status

Last updated: 2026-04-21
Status commit at update: `0c32bdb docs: add agent memory pack`

## Current Repositories

- Local main workspace: `/home/xyk/KGN-main`.
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`.
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`.
- GitHub repository: `https://github.com/xyksghr-max/KGNv2-3-23-.git`.

## Current Git State

- Current local branch: `docs-agent-memory-pack`.
- Current upstream branch: `origin/docs-agent-memory-pack`.
- Current latest known commit: `0c32bdb docs: add agent memory pack`.
- Current local branch role: documentation memory/status branch.
- Current cloud running branch: `diag-t2-d4ff8ca-base-ablation @ d4ff8ca`.
- Current cloud running task: `d4ff8ca no-conf base b1/e5` attribution experiment.

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

Current interpretation:

- T2 is clearly better than the official `paper2-clean` b1/e5 baseline under the recorded fast attribution setting.
- `KGN-main internal kgnv2base` is a strong internal baseline, not the official paper2-clean baseline.
- T2 independent contribution still needs attribution against either `d4ff8ca no-conf base` or `paper2-clean + T2-only`.
- P3/conf_fusion contributes positively for the T2 checkpoint, because T2 P3-on exceeds T2 P3-off.

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
- current cloud branch: `diag-t2-d4ff8ca-base-ablation @ d4ff8ca`
- current screen session: `37818.d4ff8ca_base (Detached)`
- current running exp_id: `diag_t2_d4ff8ca_base_no_conf_b1_single_r512_e5_val1_p20`
- expected follow-up test exp_id: `diag_t2_d4ff8ca_base_no_conf_b1_best_test_d02_a30`

The cloud server may be powered off. Do not assume it is available until checked.

When the cloud server is available, the next default action is:

1. check whether `d4ff8ca no-conf base b1/e5` finished
2. recover/test `model_best.pth` if testing was not chained automatically
3. compare the result against `paper2-clean baseline`, `KGN-main internal kgnv2base`, and T2 repeat
4. decide whether a stricter `paper2-clean + T2-only` migration experiment is still needed

## Experiment Transfer Rule

Cloud experiment directory:

- `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`

Local extraction directory:

- `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`

Only compress and transfer one `<exp_id>` directory at a time. Never compress the whole cloud `exp/grasp_pose/`.

## Next Default Action

If the cloud server is available: recover the `d4ff8ca no-conf base` result and run the no-conf test if needed.
If the cloud server is not available: do local documentation, planning, or result analysis only.
