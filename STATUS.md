# KGN-main Current Status

Last updated: 2026-04-24
Status commit at update: `T3.5b docs branch created from 1fb0084`

## Current Snapshot

- Local main workspace: `/home/xyk/KGN-main`
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`
- Current local branch: `feat/t3.5b-inference-side-enhancement`
- Current upstream branch: `origin/feat/t3.5b-inference-side-enhancement` after push
- Current branch role: T3.5b mainline preparation branch for inference-side enhancement
- Branch base: documented T3.4 line `feat/t3.4-multigrasp-target-matching @ 1fb0084`

Known local untracked files remain user/local files and must not be deleted or submitted:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`
- `邢亚坤-中期报告.doc`

## Current Experiment Facts

All numbers below are `b1/e5` short-budget attribution results, not final thesis-scale results.

- `paper2-clean baseline`: `0.1013 / 0.0922 / 0.4920`
- `d4ff8ca no-conf base`: `0.1597 / 0.1585 / 0.6440`
- `old T2 best + P3 on`: `0.2021 / 0.2088 / 0.7270`
- `T2 cloud repeat model_last + P3 on`: `0.1837 / 0.1998 / 0.7530`
- `T2 cloud repeat model_last + P3 off`: `0.1618 / 0.1483 / 0.6840`
- `T2 local repeat model_best + P3 on`: `0.2090 / 0.2320 / 0.7430`
- `T3.4 nearest_cost best/last + P3 on`: `0.1954 / 0.2080 / 0.7480`
- `T3.5a nearest_conf best + P3 on`: `0.1960 / 0.2026 / 0.7080`
- `T3.5a nearest_conf last + P3 on`: `0.0978 / 0.0980 / 0.4750`
- `KGN-main internal kgnv2base`: `0.1995 / 0.2240 / 0.7670` as historical/internal reference

Candidate-level comparison against the main T2/T3 references:

| Experiment | GSR/GCR/OSR | decoded | score-filtered | PnP failed | accepted | successful preds | accepted reproj mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `old T2 best` | `0.2021 / 0.2088 / 0.7270` | 99972 | 59468 | 780 | 58688 | 11856 | 0.6825 |
| `T2 cloud repeat last + P3 on` | `0.1837 / 0.1998 / 0.7530` | 99382 | 64225 | 2245 | 61980 | 11383 | 1.0848 |
| `T2 local repeat best + P3 on` | `0.2090 / 0.2320 / 0.7430` | 99607 | 65963 | 1036 | 64927 | 13572 | 0.7236 |
| `T3.4 nearest_cost` | `0.1954 / 0.2080 / 0.7480` | 99819 | 61509 | 1081 | 60428 | 11805 | 0.6741 |
| `T3.5a nearest_conf best` | `0.1960 / 0.2026 / 0.7080` | 99997 | 54789 | 506 | 54283 | 10637 | 0.7667 |
| `T3.5a nearest_conf last` | `0.0978 / 0.0980 / 0.4750` | 99859 | 36711 | 770 | 35941 | 3514 | 1.2389 |

## Current Interpretation

- `T3.4 nearest_cost` remains the current best `KGN-Pro-inspired` training-side positive result.
- `T3.5a nearest_conf` is implemented, cloud-validated, and fully analyzed, but it does not enter the mainline.
- `T3.5a nearest_conf best` is only marginally above `T3.4 nearest_cost` on `GSR`, while it is lower on `GCR` and clearly lower on `OSR`.
- `T3.5a nearest_conf last` collapsed strongly and should not be treated as usable evidence for continuation.
- The current best interpretation of `T3.5a` is:
  - confidence-aware target selection is runnable,
  - but the current formulation over-favors easier/high-confidence matches,
  - reduces coverage and hurts object-level success.
- When comparing cloud-trained-model ability only, `T3.4 nearest_cost` is slightly stronger than the available `T2 cloud repeat model_last + P3 on` result in `GSR/GCR`, but this must be stated with a caveat:
  - the cloud-repeat run was interrupted by power loss,
  - only `model_last.pth` was preserved for the cloud-repeat reference,
  - so this is not a clean best-vs-best superiority claim.

## Current Baseline Policy

- Primary method comparison should use:
  - `paper2-clean baseline`
  - `d4ff8ca no-conf base`
  - `old T2 best + P3 on`
  - `T2 cloud repeat model_last + P3 on/off`
  - `T2 local repeat model_best + P3 on`
- `KGN-main internal kgnv2base` remains a historical/internal reference, not the main comparison axis.
- The main T3.4 claim is:
  - `nearest_cost` multi-grasp target matching brings the `KGN-Pro-inspired` training-side path into the T2 strong-baseline range.
- The main T3.5a claim is:
  - `nearest_conf` completed a full implementation/validation cycle, but it did not outperform `T3.4 nearest_cost` as a mainline method.

## Cloud State

The cloud server is the training/evaluation executor:

- workspace: `/root/autodl-tmp/KGN-main`
- conda environment: `kgnv2`
- GPU: RTX 4090 24GB
- trusted data: local-uploaded `data/ps_grasp_single_1k`
- latest completed cloud validation branch: `feat/t3.5-conf-aware-target-selection @ 06401fa`

Latest completed T3.5a cloud experiment ids:

- smoke:
  - `t35_nearest_cost_smoke_b1_single_r512_e1_noval_p20_g4`
  - `t35_nearest_conf_smoke_b1_single_r512_e1_noval_p20_g4`
- train:
  - `t35_nearest_conf_b1_single_r512_e5_val1_p20_g4`
- best/last test:
  - `t35_nearest_conf_best_test_a07_g03_d02_a30`
  - `t35_nearest_conf_last_test_a07_g03_d02_a30`

Cloud transfer rule remains:

- compress only one experiment directory per tarball
- do not compress the whole `exp/grasp_pose/`

## Next Default Action

- Keep `feat/t3.5-conf-aware-target-selection` as the T3.5a implementation/result archive branch.
- Continue the next main experiment on the current `feat/t3.5b-inference-side-enhancement` branch.
- Treat `feat/t3.5b-inference-side-enhancement` as opened from the documented T3.4 line:
  - `feat/t3.4-multigrasp-target-matching @ 1fb0084`
- T3.5b should treat training-side and inference-side attribution separately:
  - do not mix T3.5a training-side changes into the initial T3.5b inference-side baseline
  - only combine them later if a dedicated follow-up task decides to test that interaction
