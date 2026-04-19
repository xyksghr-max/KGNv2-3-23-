# KGN-main Current Status

Last updated: 2026-04-19  
Status commit at update: `cc82c28 docs: switch to local dev and cloud experiment workflow`

## Current Repositories

- Local main workspace: `/home/xyk/KGN-main`.
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`.
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`.
- GitHub repository: `https://github.com/xyksghr-max/KGNv2-3-23-.git`.

## Current Git State

- Current local branch: `feat/t3-prob-pose-loss-clean`.
- Current upstream branch: `origin/feat/t3-prob-pose-loss-clean`.
- Current latest known commit: `cc82c28 docs: switch to local dev and cloud experiment workflow`.
- Current branch role: T3.1 prototype code and validation baseline branch.

Known local untracked files at the time this status was created:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`

These are treated as user/local files. Do not delete, overwrite, or submit them unless explicitly requested.

## Verified Mainline

The latest verified strong mainline is still T2, not T3.1.

- Weight: `exp/grasp_pose/p2_conf_single_r512_e5_800200/model_best.pth`.
- Inference:
  - `conf_fusion_alpha = 0.7`
  - `conf_fusion_min_conf = 0.3`
- Short name: `model_best.pth + a0.7/g0.3`.

Do not replace this with early P3 best, P4-lite-v2, or the historical "fine-tune 3 epochs without pose_reg" line.

## T3.1 Status

T3.1 is the current in-progress module:

- Name: training-side probabilistic pose auxiliary loss prototype.
- Prototype design: complete.
- Code integration: complete.
- Local commit: complete.
- GitHub push: complete.
- Cloud synchronization: previously completed.
- Formal cloud verification: not complete.

T3.1 must be described as:

- "prototype implemented and pending formal validation"

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

The cloud server may be powered off. Do not assume it is available until checked.

When the cloud server is available, the next default T3.1 action is:

1. pull the latest target branch
2. run Stage V0 structure/import checks
3. run smoke-off and smoke-on checks
4. only then run formal controlled training/evaluation

## Experiment Transfer Rule

Cloud experiment directory:

- `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`

Local extraction directory:

- `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`

Only compress and transfer one `<exp_id>` directory at a time. Never compress the whole cloud `exp/grasp_pose/`.

## Next Default Action

If the cloud server is available: run T3.1 Stage V0 and smoke checks.  
If the cloud server is not available: do local documentation, planning, or result analysis only.
