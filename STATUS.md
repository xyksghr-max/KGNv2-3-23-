# KGN-main Current Status

Last updated: 2026-04-25
Status commit at update: `97f9b22 feat: add post-pnp inference quality analysis`

## Current Snapshot

- Local main workspace: `/home/xyk/KGN-main`
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`
- Current local branch: `feat/t6-aigc-mesh-dataset-pilot`
- Current upstream branch: local-only at task start
- Current branch role: T6 geometry-enhanced mixed dataset pilot
- Branch base: closed T3.5b line `feat/t3.5b-inference-side-enhancement @ 97f9b22`

Known local untracked files remain user/local files and must not be deleted or submitted:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `T3.5b计划.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`
- `新对话提示词包.md`

## Current T6 Dataset Pilot State

T6 is a data-generation and loader-scope pilot, not another network/loss/post-process branch.

T6 v1 implemented direction:

- Add explicit PS dataset directory support through `--ps_data_dir`.
- Add geometry-enhanced dataset configs that do not overwrite existing primitive data.
- Keep geometry-enhanced object categories within the original PS shape taxonomy to preserve existing loader/evaluation behavior.

T6 v1 target comparison:

- `primitive-only`: existing `ps_grasp_single_1k`, 800 train scenes, about 4000 train images.
- `primitive + geom-enhanced`: `ps_grasp_single_mix_t6_1k`, 800 train scenes, about 4000 train images.
- First training budget: `batch_size=1`, `num_epochs=5`.
- First evaluation target: existing primitive single/multi test; optional geometry-enhanced held-out test for actual geometric generalization.

T6 v1 explicitly excludes:

- Stable Diffusion / ControlNet texture enhancement.
- Arbitrary Text-to-3D `.obj` automatic grasp annotation.
- Changes to model architecture, loss, decode, PnP, or post-processing.

T6 v1 conclusion:

- `ps_grasp_single_mix_t6_1k` can be generated, but the visible/geometric change is too limited.
- It is kept as a data-pipeline smoke result and is not the next b1/e5 main experiment.

T6.2 current direction:

- Switch from primitive parameter expansion to external mesh-labeled data.
- First source: official ACRONYM sample.
- First target: convert `ACRONYM .h5 + mesh` into PS-style `scene_info.json`, RGB/depth/seg, train/test split, then verify `PSGrasp` loader compatibility.

T6.2 completed local smoke:

- Installed `h5py` in local `kgnv2`.
- Cloned ACRONYM official repo sample under `data/external/acronym_repo/`.
- Added mesh conversion/generation/audit code.
- Generated `data/ps_grasp_single_mesh_t62_smoke`:
  - 50 scenes, 5 cameras each
  - 40 train scenes / 10 test scenes
  - 15000 total grasp labels
  - 6522 non-colliding grasp labels
  - sampled 2D keypoint projection: `3968 / 4000` inside image
- Ran loader/training smoke:
  - `exp_id=t62_mesh_loader_smoke`
  - 20 iterations completed
  - no NaN and no loader crash
- Added T6.2-A asset audit script:
  - `src/tools/audit_acronym_assets.py`
- Official sample audit completed:
  - `data/external/acronym/audit_sample/`
  - `Mug`: valid training candidate, `1290` valid successful grasps
  - `Table`: recognized but excluded as support category
- Full ACRONYM `.h5` labels downloaded and extracted:
  - archive: `data/external/acronym/downloads/acronym.tar.gz`
  - labels: `data/external/acronym/grasps/`
  - `.h5` file count: `8836`
- Full h5-only audit completed:
  - `data/external/acronym/audit_full_h5_only/`
  - target-category `.h5` files: `832`
  - `mesh_exists=0`
  - `training_candidates=0`
- Useful target label scale before mesh matching:
  - `Mug/Bottle/Bowl/Cup/WineBottle` all have many objects with `>=100` valid successful grasps
  - `Knife/Gun/Camera/Stapler/Pencil/CellPhone` also have strong label counts, useful as optional object-diversity categories

T6.2 current limitation:

- The completed smoke uses only the ACRONYM sample `Mug` object.
- Full ACRONYM label access is solved locally.
- ShapeNetSem mesh access is still required before constructing a meaningful 1k dataset or running b1/e5.
- Current hard blocker is mesh availability, not `.h5` grasp-label availability.

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
- `T3.5b reproj top50 on T3.4 best`: `0.2010 / 0.1851 / 0.7110`
- `T3.5b conf_reproj top50 on T3.4 best`: `0.2028 / 0.1866 / 0.7170`
- `T3.5b conf_reproj top50 + q0.05 on T3.4 best`: `0.2035 / 0.1859 / 0.7160`
- `T3.5b conf_reproj q0.05 no-topk on T3.4 best`: `0.1971 / 0.2067 / 0.7460`
- `T3.5b reproj top80 on T3.4 best`: `0.1994 / 0.2041 / 0.7440`
- `T3.5b reproj hard5 on T3.4 best`: `0.1965 / 0.2078 / 0.7480`
- `T3.5b reproj hard5 transfer on T2 local repeat best`: `0.2100 / 0.2320 / 0.7430`
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
- `T3.5b` inference-side ranking/filtering is implemented and locally validated with frozen checkpoints.
- `T3.5b` strong top-k / quality filtering improves candidate precision-style `GSR` slightly, but hurts `GCR` and `OSR`; it should not be treated as a mainline performance improvement.
- `T3.5b --reproj_error_th 5` is a stable quality-cleaning setting: it removes extreme reprojection outliers and lowers accepted reprojection error while preserving `OSR`, but it does not create new successful images.
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
- First close `feat/t3.5b-inference-side-enhancement` with code and documentation commits.
- If the next work continues algorithm/data work in `KGN-main`, branch from the closed T3.5b branch unless a strict T3.4-only attribution experiment is needed.
- For a strict clean algorithm attribution experiment, branch from `feat/t3.4-multigrasp-target-matching @ 1fb0084`.
- Do not branch from T3.5a for the next mainline.
- If the next work moves to simulation, use `/home/xyk/KGN_Sim` and its own branch lineage rather than mixing KGN-main branches.
