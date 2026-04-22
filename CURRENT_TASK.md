# Current Task

Last updated: 2026-04-23

## Task

Implement T3.3c-lite: detached per-keypoint w2d for the probabilistic pose
auxiliary loss.

## Goal

Move from T3.3a/T3.3b scalar confidence w2d to a KGN-Pro-inspired but
KGN-main-compatible per-keypoint correspondence weighting path. The first
version must keep pose-loss gradients detached from the new keypoint confidence
head by default.

## In Scope

- Create branch `feat/t3.3c-detached-per-kpt-w2d` from
  `feat/t3.3b-gated-gradient-w2d @ 99f1e6d`.
- Add optional `kpt_conf` head controlled by `--kpt_conf_branch`.
- Add `KptConfLoss` with detached per-keypoint geometry proxy supervision.
- Add `--prob_pose_w2d_source scalar_conf|kpt_conf`.
- Allow `ProbPoseAuxLoss` to build detached per-keypoint w2d from `kpt_conf`.
- Keep `src/test.py`, `src/keypoint_graspnet.py`, `decode.py`, and
  `pose_recover/` unchanged.

## Out Of Scope

- No wholesale migration from `KGN-Pro-main`.
- No KGN-Pro-main `base_trainer.py`, `test.py`, or `pose_recover/` replacement.
- No test/inference-chain change.
- No claim that T3.3c-lite is effective before cloud smoke/formal evaluation.
- No submission of `data/`, `exp/`, checkpoints, tarballs, or large logs.

## Completion Criteria

- Local static checks pass:
  - `python -m py_compile src/lib/opts.py src/lib/trains/grasp_pose.py src/lib/models/prob_pose_aux_loss.py`
  - grep confirms new switches and diagnostics.
- Local lightweight tensor checks pass in the `kgnv2` environment.
- Git diff only touches intended source/doc files.
- User receives cloud smoke and b1/e5 follow-up commands after commit/push.

## Current Interpretation

T3.3b proved that gradient-enabled scalar w2d is a useful diagnostic path but
hurts b1/e5 performance. T3.3c-lite should therefore be treated as a safer
detached per-keypoint correspondence-weighting experiment, not as an already
verified improvement.
