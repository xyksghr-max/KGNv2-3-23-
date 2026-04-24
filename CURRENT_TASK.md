# Current Task

Last updated: 2026-04-24

## Task

Close `T3.5b inference-side enhancement` and decide the next branch base.

## Goal

Record the frozen-checkpoint inference-side result clearly, keep the current positive
`T3.4 nearest_cost` training-side result stable, and avoid starting the next branch from stale
or negative-result documentation.

## Branch Context

- Current task branch: `feat/t3.5b-inference-side-enhancement`
- Branch base branch: `feat/t3.4-multigrasp-target-matching`
- Branch base commit: `1fb0084 docs: record t34 result interpretation against t2 baselines`
- Archived sibling branch: `feat/t3.5-conf-aware-target-selection`

Why:

- `T3.5a nearest_conf` completed a full cloud validation cycle and did not become a mainline improvement
- `T3.5b` is intended to isolate inference-side gains
- mixing `T3.5a` training-side changes into the initial T3.5b baseline would blur attribution

## In Scope

- deterministic inference-side enhancement only
- candidate ranking and post-process logic based on signals already available in the current chain
- reading and comparing:
  - candidate score
  - confidence
  - reprojection error
  - PnP success/failure
  - failure-reason and shape-level analysis outputs
- updating documents after the new branch/task is opened

## Out Of Scope

- no continuation of `T3.5a nearest_conf` as the mainline branch
- no immediate new training-side combined retry unless a dedicated follow-up task decides to reopen it
- no KGN-Pro-main directory migration
- no replacement of `test.py`, `decode.py`, `keypoint_graspnet.py`, or `pose_recover/` with KGN-Pro-main files
- no generated data, checkpoints, tarballs, or large logs in Git

## Current State

- `T3.4 nearest_cost` remains the current best `KGN-Pro-inspired` training-side positive result:
  - `0.1954 / 0.2080 / 0.7480`
- `T3.5a nearest_conf` is implemented and fully validated:
  - best: `0.1960 / 0.2026 / 0.7080`
  - last: `0.0978 / 0.0980 / 0.4750`
- T3.5a conclusion:
  - runnable and analyzable
  - not strong enough to replace T3.4 nearest_cost
  - likely over-favors easier / high-confidence matches and reduces coverage
- T3.5b conclusion:
  - implemented and locally validated
  - `post_pnp_score_type=none` reproduces T3.4 metrics
  - top-k / quality-filter variants are not mainline improvements because they reduce `GCR` and `OSR`
  - `--reproj_error_th 5` is a stable reprojection-outlier cleaning option, not a new success-generating module

Primary comparison targets remain:

- `paper2-clean baseline`: `0.1013 / 0.0922 / 0.4920`
- `d4ff8ca no-conf base`: `0.1597 / 0.1585 / 0.6440`
- `old T2 best + P3 on`: `0.2021 / 0.2088 / 0.7270`
- `T2 cloud repeat model_last + P3 on`: `0.1837 / 0.1998 / 0.7530`
- `T2 local repeat model_best + P3 on`: `0.2090 / 0.2320 / 0.7430`

## Next Step

Commit and push the T3.5b source/docs after review. For the next `KGN-main` branch:

- default: branch from closed `feat/t3.5b-inference-side-enhancement`
- strict T3.4-only attribution: branch from `feat/t3.4-multigrasp-target-matching @ 1fb0084`
- do not branch from T3.5a
