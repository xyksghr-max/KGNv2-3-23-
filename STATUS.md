# KGN-main Current Status

Last updated: 2026-04-27
Status commit at update: `fbb1b6d feat: add t62 acronym mesh dataset smoke pipeline`

## Current Snapshot

- Local main workspace: `/home/xyk/KGN-main`
- Local reference repository: `/home/xyk/KGN-main/KGN-Pro-main`
- Cloud training/evaluation workspace: `/root/autodl-tmp/KGN-main`
- Current local branch: `feat/t6.3-graspnet-to-ps-audit`
- Current upstream branch: local-only at task start
- Current branch role: T6.3/T6.4/T6.5 GraspNet external-evaluation and PS-format conversion audit
- Branch base: `feat/t6-aigc-mesh-dataset-pilot @ fbb1b6d`

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

## Current T6.3 GraspNet-to-PS Audit State

T6.3 is the fallback/parallel dataset route after ShapeNetSem access became uncertain. It uses GraspNet object models and object-level grasp labels, not the 80GB+ RGB-D scene image packages.

Local GraspNet assets:

- downloaded and extracted:
  - `data/external/graspnet/raw/models/`
  - `data/external/graspnet/raw/grasp_label/`
- retained but not extracted:
  - `data/external/graspnet/downloads/collision_label.zip`
- deleted to recover disk space after extraction:
  - `data/external/graspnet/downloads/models.zip`
  - `data/external/graspnet/downloads/grasp_label.zip`
  - `data/external/graspnet/raw/collision_label/`

Reason for deleting `raw/collision_label/`:

- T6.3 first pass is object-level synthetic rendering.
- `grasp_label/*.npz` already contains object-level `collision` arrays together with `points`, `offsets`, and `scores`.
- Scene-level collision labels are not required before we use official GraspNet scene RGB-D data.

T6.3-B asset audit result:

- added script: `src/tools/audit_graspnet_assets.py`
- output directory: `data/external/graspnet/audit/` (not submitted to Git)
- total objects: `88`
- mesh exists/loadable: `88 / 88`
- label exists/loadable: `88 / 88`
- labels with object-level collision: `88 / 88`
- training candidates with `valid_grasps >= 100`: `88 / 88`
- total valid grasps after score, width, and object-collision filtering: `8,419,024`
- smallest valid object in this audit: object `006`, `358` valid grasps
- largest valid object in this audit: object `005`, `439,318` valid grasps

Current T6.3 conclusion:

- GraspNet object-level assets pass the first feasibility gate.
- T6.3-C conversion smoke also passes the second feasibility gate.
- Implemented GraspNet object mesh + object-level grasp labels -> PS-style RGB-D render + `scene_info.json`.
- The first `data/ps_grasp_single_graspnet_t63_smoke` generation wrote `48 / 50` scenes and is kept only as a partial diagnostic artifact.
- The accepted smoke dataset is `data/ps_grasp_single_graspnet_t63_smoke_v2`.
- `ps_grasp_single_graspnet_t63_smoke_v2` audit result:
  - `scene_count=50`
  - `train_count=40`
  - `test_count=10`
  - `total_grasps=15000`
  - `noncolliding_grasps=4675`
  - keypoint projection inside image: `3995 / 4000`
  - width range: `0.010016 / 0.084999`
  - `obj_types={"mesh": 50}`
- Loader/training smoke completed:
  - `exp_id=t63_graspnet_loader_smoke`
  - `PSGrasp` loaded `ps_grasp_single_graspnet_t63_smoke_v2`
  - 20 iterations completed
  - no loader crash and no NaN observed
- The next step is visual acceptance of `data/ps_grasp_single_graspnet_t63_smoke_v2/audit_vis/`, then optionally generate a 1k GraspNet-derived dataset and primitive+GraspNet mixed dataset.

## Current T6.4 GraspNet Real RGB-D Eval State

T6.4 is an external real-domain evaluation route, not a new training-data route.
Its purpose is to test the official KGNv2 multi-object primitive-trained checkpoint
`exp/kgnv2.pth` on real GraspNet RealSense RGB-D frames converted into PS-style eval format.

Local real GraspNet subset:

- extracted under `data/external/graspnet/real_rgbd_subset/`
- `90` scenes: `scene_0100` to `scene_0189`
- each scene has `realsense` data only
- each scene has `16` selected views
- total eval frames: `1440`
- `train_4.zip` is retained but not used for the main evaluation, because it belongs to GraspNet train split.

Implemented/effective T6.4 files:

- `src/tools/audit_graspnet_real_subset.py`
- `src/main_graspnet_real_eval_convert.py`

Generated PS-style real eval datasets:

- `data/ps_grasp_real_graspnet_t64_smoke`
  - `48` frames
  - smoke split from representative `seen/similar/novel` scenes
- `data/ps_grasp_real_graspnet_t64_eval`
  - `1440` frames
  - `test.txt` has `1440` entries
  - `train.txt` is empty by design

Official KGNv2 checkpoint smoke result:

- checkpoint: `exp/kgnv2.pth`
- strict smoke exp: `t64_real_graspnet_smoke_kgnv2_official`
- strict metrics: `0.0000 / 0.0000 / 0.0000`
- strict diagnostics:
  - `decoded_candidates_total=4790`
  - `score_filtered_candidates_total=114`
  - `pnp_failed_total=0`
  - `accepted_candidates_total=114`
  - `images_with_any_prediction=32 / 48`
  - `accepted_reprojection_error_mean=9.7239`

Relaxed diagnostic result:

- exp: `t64_real_graspnet_smoke_kgnv2_relaxed_c01_d05_a45_nosample`
- settings: `center_thresh=0.1`, `vis_thresh=0.1`, `dist_th=0.05`, `angle_th=45`
- important: no `rot_sample_num` or `trl_sample_num`; mesh/real GraspNet eval must use converted GT labels directly.
- metrics: `0.0190 / 0.0020 / 0.0540`
- diagnostics:
  - `decoded_candidates_total=4781`
  - `accepted_candidates_total=4672`
  - `images_with_any_prediction=48 / 48`
  - `images_with_any_eval_success=17 / 48`
  - `eval_successful_prediction_total=89`
  - `accepted_reprojection_error_mean=3.2640`

Scale-refined diagnostic result:

- exp: `t64_real_graspnet_smoke_kgnv2_relaxed_c01_d05_a45_refinescale`
- settings: same as the relaxed diagnostic result, plus `--refine_scale`
- metrics: `0.3894 / 0.0371 / 0.5047`
- diagnostics:
  - `decoded_candidates_total=4781`
  - `accepted_candidates_total=4181`
  - `images_with_any_prediction=48 / 48`
  - `images_with_any_eval_success=48 / 48`
  - `eval_successful_prediction_total=1628`
  - `accepted_reprojection_error_mean=3.2184`
- camera/depth audit:
  - converted smoke set uses GraspNet RealSense intrinsics:
    `[[927.17, 0, 651.32], [0, 927.37, 349.62], [0, 0, 1]]`
  - GraspNet `factor_depth=1000` is consistent with converted depth in meters.
  - smoke object-mask depth mean is about `0.412 m`; the no-refine accepted scale mean is about `0.582 m`.
  - this scale gap is large enough to fail `dist_th=0.02/0.03/0.05` even when 2D keypoints and PnP are otherwise valid.

High-confidence threshold check:

- exp: `t64_real_graspnet_smoke_kgnv2_refinescale_c03_d02_a30`
  - settings: `center_thresh=0.3`, `dist_th=0.02`, `angle_th=30`, `--refine_scale`
  - metrics: `0.0000 / 0.0000 / 0.0000`
- exp: `t64_real_graspnet_smoke_kgnv2_refinescale_c03_d03_a45`
  - settings: `center_thresh=0.3`, `dist_th=0.03`, `angle_th=45`, `--refine_scale`
  - metrics: `0.1173 / 0.0009 / 0.0258`
- conclusion: `center_thresh=0.3` is too conservative for this real-domain converted GraspNet evaluation.

Full real-eval diagnostic result:

- exp: `t64_real_graspnet_eval_kgnv2_relaxed_c01_d05_a45_refinescale`
- dataset: `data/ps_grasp_real_graspnet_t64_eval`
- frames: `1440`
- settings: `center_thresh=0.1`, `vis_thresh=0.1`, `dist_th=0.05`, `angle_th=45`, `--refine_scale`
- metrics: `0.4751 / 0.0443 / 0.4876`
- diagnostics:
  - `decoded_candidates_total=143640`
  - `accepted_candidates_total=126145`
  - `images_with_any_prediction=1440 / 1440`
  - `images_with_any_eval_success=1434 / 1440`
  - `eval_successful_prediction_total=59928`
  - `avg_time_spf=0.1537`

Current interpretation:

- The official KGNv2 primitive-trained model is not silent on real GraspNet RGB-D frames.
- The strict `0 / 0 / 0` result should not be written as "the model cannot grasp real objects".
- The main cause of the very low no-refine relaxed score is translation-scale mismatch under real-depth domain shift, not an obvious GraspNet camera-intrinsic conversion error.
- A more accurate conclusion is: the model produces real-scene grasp candidates, and with real-depth scale refinement it obtains substantial nonzero matches on the full converted GraspNet real subset; however strict GraspNet-converted GT matching and GCR remain hard because the GT set is dense and the metric was designed around PS-style primitive labels.
- T6.4 should currently be written as external real-domain generalization exploration and qualitative/diagnostic evidence, not as the main thesis quantitative table.

## Current T6.5 GraspNet88 Single-Object Synthetic Mesh Eval State

T6.5 is the current completed GraspNet object-level single-object synthetic evaluation. It uses all `88` GraspNet object meshes and object-level grasp labels, rendered into PS-style RGB-D single-object scenes.

Generated dataset:

- dataset: `data/ps_grasp_single_graspnet_t63_eval_88obj`
- scenes: `88`
- views per scene: `5`
- total RGB-D samples: `440`
- split: `train.txt` empty, `test.txt` contains `0..87`
- object coverage: exactly `000..087`
- object type: `mesh`
- non-colliding GT per scene:
  - min / p05 / p25 / median / p75 / p95 / max / mean =
    `2 / 20 / 42 / 74 / 124 / 185 / 232 / 85.59`
- sparse-label outliers:
  - object `009`: `14` non-colliding GT
  - object `040`: `19` non-colliding GT
  - object `065`: `2` non-colliding GT

Official KGNv2 no-refine protocol:

- checkpoint: `exp/kgnv2.pth`
- inference: `--sep_scale_branch`, `--scale_kpts_mode 1`, `--scale_coeff_k 1`
- no `--refine_scale`
- no primitive GT resampling options

No-refine results:

| Threshold | GSR / GCR / OSR | Image Success | Successful Predictions | Object Any-View Success |
| --- | --- | ---: | ---: | ---: |
| `1cm + 20deg` | `0.0249 / 0.0065 / 0.2318` | `102 / 440` | `285` | `46 / 88` |
| `2cm + 30deg` | `0.1685 / 0.0567 / 0.6409` | `282 / 440` | `1930` | `79 / 88` |
| `3cm + 45deg` | `0.4338 / 0.2189 / 0.8841` | `389 / 440` | `4970` | `86 / 88` |

KGNv2 + Refine-Scale inference-side improvement:

- protocol: KGNv2 official model plus `--refine_scale`
- role: inference-side RGB-D depth scale refinement, not pure paper-2 original inference
- candidate counts match no-refine:
  - `decoded_candidates_total=42506`
  - `score_filtered_candidates_total=11492`
  - `accepted_candidates_total=11457`
  - `images_with_any_prediction=438 / 440`
  - `scale_refine_failed_total=0`

Refine-Scale results:

| Threshold | GSR / GCR / OSR | Image Success | Successful Predictions | Object Any-View Success |
| --- | --- | ---: | ---: | ---: |
| `1cm + 20deg` | `0.0614 / 0.0135 / 0.3750` | `165 / 440` | `704` | `67 / 88` |
| `2cm + 30deg` | `0.2868 / 0.0864 / 0.8136` | `358 / 440` | `3286` | `86 / 88` |
| `3cm + 45deg` | `0.5424 / 0.2696 / 0.9364` | `412 / 440` | `6214` | `87 / 88` |

Object-level interpretation:

- local GraspNet assets provide ids `000..087`, but no semantic object-name table was found.
- relaxed Refine-Scale no-success object:
  - object `065`: `0 / 5` successful views, `0 / 49` successful predictions, bbox approx `(0.086, 0.200, 0.044) m`, aspect `4.52`, non-colliding GT only `2`.
- standard Refine-Scale no-success objects:
  - objects `049` and `065`
- relaxed Refine-Scale size grouping:
  - small `<0.10 m`: image success `149 / 150 = 99.3%`, object any-view success `30 / 30`, group GSR `0.656`
  - medium `0.10..0.18 m`: image success `179 / 190 = 94.2%`, object any-view success `38 / 38`, group GSR `0.560`
  - large `>=0.18 m`: image success `84 / 100 = 84.0%`, object any-view success `19 / 20`, group GSR `0.355`
- in this single-object synthetic mesh setting, small objects are not the main failure source; larger, elongated, high-aspect-ratio, or sparse-label objects are harder.

Qualitative materials:

- 2D/3D box keypoint visualizations remain useful for explaining the KGNv2 keypoint-to-PnP pipeline.
- Two-finger gripper visualizations were generated for selected atypical objects under both no-refine and Refine-Scale protocols.
- Recommended Refine-Scale montage:
  `exp/grasp_pose/t63_graspnet88_single_kgnv2_refinescale_relaxed_d03_a45/analysis_analysis_t63_graspnet88_single_kgnv2_refinescale_relaxed_d03_a45/presentation/two_finger_gripper_panels_top10_refinescale/graspnet88_selected_two_finger_gripper_montage.jpg`

Current interpretation:

- GraspNet88 single-object synthetic mesh eval is completed and suitable as a thesis external complex-geometry generalization table.
- No-refine should be described as the paper-2/KGNv2 original-style inference protocol.
- Refine-Scale should be described as an inference-side RGB-D scale refinement improvement.
- The GraspNet88 table should not be mixed directly with primitive benchmark results as a same-distribution comparison.

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

- Close the current GraspNet88 single-object synthetic eval work with a small documentation/code commit.
- Commit only explicit source and documentation files; do not submit `data/`, `exp/`, checkpoints, logs, or generated images.
- Use GraspNet88 results as a thesis external complex-object generalization section.
- Use GraspNet real RGB-D T6.4 results only as real-domain exploratory/diagnostic evidence.
- If continuing KGN-main after this close-out, open the next branch from the committed `feat/t6.3-graspnet-to-ps-audit` state unless a strict older-baseline attribution task requires a documented earlier branch.
