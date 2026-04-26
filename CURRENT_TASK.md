# Current Task

Last updated: 2026-04-27

## Task

Implement and verify `T6.3 GraspNet-to-PS feasibility audit and smoke conversion`.

## Goal

Build a GraspNet object-level dataset feasibility path in `KGN-main`. T6 no longer continues network/loss/post-process tuning. T6.3 tests whether GraspNet object models and object-level 6D grasp labels can be converted into the current PS dataset format and read by the existing KGN training pipeline.

## Branch Context

- Current branch: `feat/t6.3-graspnet-to-ps-audit`
- Branch base: `feat/t6-aigc-mesh-dataset-pilot @ fbb1b6d`
- Branch role: GraspNet asset audit and PS-format conversion pilot

Known untracked local files remain user/local files and must not be deleted or submitted:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `T3.5b计划.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`
- `新对话提示词包.md`

## In Scope

- Audit GraspNet object models and object-level grasp labels.
- Use `models/` and `grasp_label/` first; do not download or require the full GraspNet RGB-D scene packages.
- Confirm mesh loadability, label loadability, score/width/collision filtering, and available valid grasp counts.
- Prepare and verify a small synthetic-render PS-format smoke dataset if the audit passes.
- Add explicit PS dataset directory support so experiments can read alternate datasets without overwriting `ps_grasp_single_1k` or `ps_grasp_multi_1k`.
- Add ACRONYM sample-level mesh grasp label conversion.
- Add a mesh-backed object wrapper that reuses existing rendering, collision filtering, keypoint projection, and training-label generation.
- Generate and audit a small mesh-only smoke dataset:
  - `data/ps_grasp_single_mesh_t62_smoke`
- Run `PSGrasp` loader/training smoke on the generated mesh dataset.
- Keep the output dataset format compatible with the existing PS grasp format:
  - `color_images/`
  - `depth_raw/`
  - `seg_labels/`
  - `scene_info.json`
  - `train.txt`
  - `test.txt`

## Out Of Scope

- No b1/e5 training during the asset-audit stage.
- No GraspNet 80GB+ RGB-D scene image download in the first pass.
- No use of scene-level `collision_label/` before the object-level route is proven.
- No Stable Diffusion / ControlNet texture generation.
- No arbitrary Text-to-3D `.obj` automatic grasp labeling in T6.2 first pass.
- No self-developed full mesh antipodal sampler in T6.2 first pass.
- No b1/e5 or b12/e400 training until the mesh conversion/loader smoke is accepted.
- No network, loss, decode, pose recovery, or post-process changes for this task.
- No generated datasets, checkpoints, experiment directories, or logs in Git.

## Current Implementation Decision

T6 v1 parameter-range geometry enhancement is kept only as a data-pipeline smoke result. It is not the next b1/e5 main experiment because the visual/geometric change is too limited.

T6.2 switches to an external mesh-label route:

- source: official ACRONYM sample first
- object type in PS annotations: `mesh`
- grasp labels: successful ACRONYM parallel-jaw grasp transforms converted into the current KGN gripper frame
- first generated dataset: `data/ps_grasp_single_mesh_t62_smoke`

Reason:

- It avoids copying primitive grasp labels onto combination objects.
- It keeps YCB as a held-out simulation generalization target instead of directly using YCB as training data.
- It lets us first verify `ACRONYM .h5 + mesh -> PS format -> PSGrasp loader` before spending training budget.

## Current T6.2 Smoke Result

- `h5py` installed in local `kgnv2`.
- ACRONYM official repo cloned locally under `data/external/acronym_repo/`.
- Sample source used: ACRONYM `Mug` example.
- Generated smoke dataset:
  - `data/ps_grasp_single_mesh_t62_smoke`
  - 50 scenes, 5 cameras per scene
  - 40 train scenes / 10 test scenes
- Dataset audit:
  - `scene_count=50`
  - `total_grasps=15000`
  - `noncolliding_grasps=6522`
  - width range `0.08 / 0.08`
  - sampled keypoint projection: `3968 / 4000` inside image
- Loader/training smoke:
  - `exp_id=t62_mesh_loader_smoke`
  - 20 iterations completed
  - no NaN and no loader crash after orientation wrapping fix

## Current T6.2-A Asset Audit Result

- Added read-only ACRONYM asset audit tool:
  - `src/tools/audit_acronym_assets.py`
- Sample audit command completed on official ACRONYM examples:
  - output: `data/external/acronym/audit_sample/`
  - `total_h5=2`
  - `mesh_exists=2`
  - `mesh_loadable=2`
  - `training_candidates=1`
  - `Mug` sample is a valid training candidate with `1290` valid successful grasps.
  - `Table` sample is recognized but excluded as a support category.
- ACRONYM full `.h5` archive has been downloaded and extracted:
  - archive: `data/external/acronym/downloads/acronym.tar.gz`
  - grasp labels: `data/external/acronym/grasps/`
  - `.h5` files: `8836`
- Full h5-only audit completed:
  - output: `data/external/acronym/audit_full_h5_only/`
  - target-category `.h5` files: `832`
  - `mesh_exists=0`
  - `training_candidates=0`
- Label-side scale is sufficient for the next stage:
  - `Mug`: 101 files, 101 objects with >=100 valid grasps
  - `Bottle`: 44 files, 44 objects with >=100 valid grasps
  - `Bowl`: 83 files, 83 objects with >=100 valid grasps
  - `Cup`: 62 files, 62 objects with >=100 valid grasps
  - additional useful categories include `WineBottle`, `Knife`, `Camera`, `Stapler`, `Pencil`, and `CellPhone`
- Current blocker:
  - ShapeNetSem meshes are not locally available.
  - ACRONYM full-data use requires matching ShapeNetSem meshes under paths like `meshes/Mug/<object_id>.obj`.
  - ShapeNet download requires user-side login/registration or an already downloaded local mesh path.

## Next Verification

Local light checks:

```bash
cd /home/xyk/KGN-main
python -m py_compile \
  src/main_mesh_data_generate.py \
  src/lib/data_generation/objects/MeshObject.py \
  src/lib/data_generation/mesh_grasp/acronym_loader.py \
  src/tools/audit_ps_dataset.py \
  src/lib/datasets/dataset/ps_grasp.py \
  src/lib/data_generation/dataLogger.py \
  src/lib/data_generation/__init__.py \
  src/lib/utils/keypoints.py
git diff --check
```

Current smoke generation:

```bash
cd /home/xyk/KGN-main/src
conda run -n kgnv2 python main_mesh_data_generate.py \
  --config_file lib/data_generation/ps_grasp_single_mesh_t62_smoke.yaml
```

Current smoke audit:

```bash
cd /home/xyk/KGN-main/src
conda run -n kgnv2 python tools/audit_ps_dataset.py \
  --data_dir ../data/ps_grasp_single_mesh_t62_smoke \
  --check_images \
  --check_grasps \
  --sample_vis 10
```

Next decision before b1/e5:

- obtain matching ShapeNetSem meshes for the audited `.h5` labels, then run a mesh-existence/loadability re-audit;
- if mesh access remains blocked, keep the work as sample-level conversion proof and do not run b1/e5.

## Current T6.3-B Asset Audit Result

GraspNet downloaded/extracted local assets:

- `data/external/graspnet/raw/models/`
- `data/external/graspnet/raw/grasp_label/`

Space-control decision:

- `data/external/graspnet/raw/collision_label/` was removed because it expanded to about 30GB and is scene-level.
- `data/external/graspnet/downloads/models.zip` and `data/external/graspnet/downloads/grasp_label.zip` were removed after extraction.
- `data/external/graspnet/downloads/collision_label.zip` remains compressed for possible future scene-level work.

Read-only audit:

- script: `src/tools/audit_graspnet_assets.py`
- quick output: `data/external/graspnet/audit_quick/`
- full output: `data/external/graspnet/audit/`

Full audit result:

- total objects: `88`
- mesh exists/loadable: `88 / 88`
- label exists/loadable: `88 / 88`
- labels with object-level collision arrays: `88 / 88`
- training candidates with `valid_grasps >= 100`: `88 / 88`
- total valid grasps after score, width, and object-level collision filtering: `8,419,024`

Next step:

- completed in T6.3-C; see the section below.

## Current T6.3-C Conversion Smoke Result

Implemented files:

- `src/lib/data_generation/mesh_grasp/graspnet_loader.py`
- `src/main_graspnet_data_generate.py`
- `src/lib/data_generation/ps_grasp_single_graspnet_t63_smoke.yaml`

Implementation notes:

- GraspNet labels are read from `grasp_label/*_labels.npz`.
- Valid grasps are filtered by score, width, and object-level collision.
- GraspNet viewpoint/angle/width labels are converted into object-frame 4x4 grasp poses.
- Poses are converted into the current KGN gripper frame before writing PS-style labels.
- Existing `MeshObject`, `SceneRender`, and `DataLogger` are reused.

Generation result:

- Initial directory `data/ps_grasp_single_graspnet_t63_smoke` wrote `48 / 50` scenes and is treated as partial diagnostic output only.
- Accepted smoke dataset:
  - `data/ps_grasp_single_graspnet_t63_smoke_v2`
  - 50 scenes
  - 5 cameras per scene
  - 40 train scenes / 10 test scenes
  - generated with at least 20 non-colliding grasps per scene

Audit result:

- `scene_count=50`
- `total_grasps=15000`
- `noncolliding_grasps=4675`
- keypoint projection inside image: `3995 / 4000`
- width range: `0.010016 / 0.084999`

Loader/training smoke:

- `exp_id=t63_graspnet_loader_smoke`
- 20 iterations completed
- no loader crash and no NaN observed

Next step:

- manually inspect `data/ps_grasp_single_graspnet_t63_smoke_v2/audit_vis/`;
- if visual geometry is acceptable, generate a 1k GraspNet-derived dataset;
- then build a primitive+GraspNet mixed dataset with the same 4000-image training budget before any b1/e5 comparison.

## Current T6.4 Real GraspNet RGB-D Eval Result

T6.4 extends the GraspNet work from object-level synthetic conversion to real RGB-D external evaluation.

Completed:

- Real subset exists under `data/external/graspnet/real_rgbd_subset/`.
- Subset scale:
  - `scene_0100` to `scene_0189`
  - `90` scenes
  - `16` RealSense views per scene
  - `1440` total frames
- Conversion/audit tooling exists:
  - `src/tools/audit_graspnet_real_subset.py`
  - `src/main_graspnet_real_eval_convert.py`
- Converted eval datasets exist:
  - `data/ps_grasp_real_graspnet_t64_smoke`
  - `data/ps_grasp_real_graspnet_t64_eval`
- Official KGNv2 checkpoint exists:
  - `exp/kgnv2.pth`

Strict smoke evaluation:

- exp: `t64_real_graspnet_smoke_kgnv2_official`
- metrics: `0.0000 / 0.0000 / 0.0000`
- diagnostics:
  - `decoded_candidates_total=4790`
  - `score_filtered_candidates_total=114`
  - `pnp_failed_total=0`
  - `accepted_candidates_total=114`
  - `images_with_any_prediction=32 / 48`

Relaxed smoke diagnosis:

- exp: `t64_real_graspnet_smoke_kgnv2_relaxed_c01_d05_a45_nosample`
- settings:
  - `center_thresh=0.1`
  - `vis_thresh=0.1`
  - `dist_th=0.05`
  - `angle_th=45`
  - no `rot_sample_num` or `trl_sample_num`
- metrics: `0.0190 / 0.0020 / 0.0540`
- diagnostics:
  - `accepted_candidates_total=4672`
  - `images_with_any_prediction=48 / 48`
  - `images_with_any_eval_success=17 / 48`
  - `eval_successful_prediction_total=89`

Scale-refined smoke diagnosis:

- exp: `t64_real_graspnet_smoke_kgnv2_relaxed_c01_d05_a45_refinescale`
- settings:
  - `center_thresh=0.1`
  - `vis_thresh=0.1`
  - `dist_th=0.05`
  - `angle_th=45`
  - `--refine_scale`
  - no `rot_sample_num` or `trl_sample_num`
- metrics: `0.3894 / 0.0371 / 0.5047`
- diagnostics:
  - `accepted_candidates_total=4181`
  - `images_with_any_prediction=48 / 48`
  - `images_with_any_eval_success=48 / 48`
  - `eval_successful_prediction_total=1628`

Full scale-refined eval diagnosis:

- exp: `t64_real_graspnet_eval_kgnv2_relaxed_c01_d05_a45_refinescale`
- dataset: `data/ps_grasp_real_graspnet_t64_eval`
- frames: `1440`
- settings:
  - `center_thresh=0.1`
  - `vis_thresh=0.1`
  - `dist_th=0.05`
  - `angle_th=45`
  - `--refine_scale`
  - no `rot_sample_num` or `trl_sample_num`
- metrics: `0.4751 / 0.0443 / 0.4876`
- diagnostics:
  - `accepted_candidates_total=126145`
  - `images_with_any_prediction=1440 / 1440`
  - `images_with_any_eval_success=1434 / 1440`
  - `eval_successful_prediction_total=59928`

Root-cause diagnosis:

- GraspNet RealSense intrinsics are being used in the converted PS-style scene info.
- `scene_0100/realsense/meta/0000.mat` has `factor_depth=1000`, matching the converted meter-depth convention.
- `cls_indexes = object_id + 1` mapping was verified on `scene_0100`.
- The smoke object-mask depth mean is about `0.412 m`, while no-refine accepted predicted scale mean is about `0.582 m`.
- Therefore the dominant low-score cause is missing real-depth scale refinement, not a basic intrinsics or depth-factor conversion failure.
- `center_thresh=0.3` remains too strict for the real-domain smoke set even with `--refine_scale`.

Current conclusion:

- The official primitive-trained `exp/kgnv2.pth` does produce grasp candidates on real GraspNet RGB-D frames.
- Strict zero metrics are mainly a strict-evaluation/domain-shift and scale-mismatch warning, not proof that the model cannot grasp real objects.
- With `--refine_scale`, the same 48-frame smoke set reaches `0.3894 / 0.0371 / 0.5047`, and the full 1440-frame set reaches `0.4751 / 0.0443 / 0.4876`, which is much more consistent with the real RGB-D Mayavi qualitative result.
- `--rot_sample_num` and `--trl_sample_num` must not be used for converted mesh/real GraspNet eval, because they trigger primitive-only scene reconstruction.

## T6.3 88-object single GraspNet synthetic eval generation protocol

Current target dataset:

- `data/ps_grasp_single_graspnet_t63_eval_88obj`
- `88` GraspNet object meshes, sequentially sampled as scene `0..87`
- `5` rendered camera views per scene, total `440` eval samples
- `train.txt` is empty, `test.txt` contains all `88` scenes
- This is a synthetic single-object mesh eval set, not a real-camera single-object GraspNet set.

Current generation policy:

- `min_noncolliding_grasps=20`
- `max_attempts_per_scene=40`
- `allow_best_effort=true`
- If a scene cannot reach `20` non-colliding grasps after `40` attempts, save the attempt with the largest non-colliding grasp count.

Local codecheck result:

- command used a temporary `scene_num=10` output directory.
- first 10 sequential objects generated successfully.
- `scene 9` did not reach the target threshold; best-effort fallback saved attempt `3` with `14` non-colliding grasps.
- audit result: `scene_count=10`, `train_count=0`, `test_count=10`, `missing_images=0`, `missing_scene_info=0`, `empty_grasp_objects=0`, `noncolliding_grasps=1305`.

Full 88-object audit result:

- generated in `32:23`
- `scene_count=88`
- `train_count=0`, `test_count=88`
- `440` RGB-D samples
- object ids are exactly sequential `000..087`
- each scene has one `mesh` object and `5` camera views
- `missing_images=0`, `missing_scene_info=0`, `empty_grasp_objects=0`
- total stored grasps: `26218`
- total non-colliding grasps: `7532`
- non-colliding grasps per scene:
  - min / p05 / p25 / median / p75 / p95 / max / mean =
    `2 / 20 / 42 / 74 / 124 / 185 / 232 / 85.59`
- scenes below target `20`:
  - scene `9`, object `009`: `14`
  - scene `40`, object `040`: `19`
  - scene `65`, object `065`: `2`
- `PSGrasp` loaded all `440` samples successfully, with no `__getitem__` errors.
- post-projection label count per sample has min / median / max / mean =
  `2 / 57 / 194 / 67.47`, and no sample has zero projected labels.

Interpretation:

- The full set is usable for synthetic single-object GraspNet mesh evaluation and keeps all `88` objects covered.
- Scene `65` is an extremely weak-label case and should be reported as a limitation of the all-object-coverage protocol, not silently hidden.
- This set is suitable for an external complex-mesh synthetic evaluation, not for claims about real-camera single-object GraspNet data.

First full evaluation with official `exp/kgnv2.pth`:

- protocol: KGNv2 no-refine, `--sep_scale_branch`, `--scale_kpts_mode 1`, `--scale_coeff_k 1`
- no confidence branch
- no `rot_sample_num` or `trl_sample_num`, because this is mesh-label eval
- strict threshold `dist_th=0.01`, `angle_th=20`:
  - metrics: `0.0249 / 0.0065 / 0.2318`
  - `accepted_candidates_total=11457`
  - `images_with_any_prediction=438 / 440`
  - `images_with_any_eval_success=102 / 440`
  - `eval_successful_prediction_total=285`
  - unique-object any-view success: `46 / 88`
  - unique-object all-5-view success: `4 / 88`
- standard threshold `dist_th=0.02`, `angle_th=30`:
  - metrics: `0.1685 / 0.0567 / 0.6409`
  - `accepted_candidates_total=11457`
  - `images_with_any_prediction=438 / 440`
  - `images_with_any_eval_success=282 / 440`
  - `eval_successful_prediction_total=1930`
  - unique-object any-view success: `79 / 88`
  - unique-object all-5-view success: `26 / 88`
- relaxed threshold `dist_th=0.03`, `angle_th=45`:
  - metrics: `0.4338 / 0.2189 / 0.8841`
  - `accepted_candidates_total=11457`
  - `images_with_any_prediction=438 / 440`
  - `images_with_any_eval_success=389 / 440`
  - `eval_successful_prediction_total=4970`
  - unique-object any-view success: `86 / 88`
  - unique-object all-5-view success: `62 / 88`

Filtered aggregation from analysis CSV:

- excluding the three scenes below `20` GT (`009`, `040`, `065`) changes:
  - standard: GSR/OSR from `0.1685 / 0.6409` to `0.1711 / 0.6541`
  - relaxed: GSR/OSR from `0.4338 / 0.8841` to `0.4419 / 0.8965`
- filtering by `GT >= mean 85.59` is not recommended:
  - standard OSR drops to `0.5730`
  - relaxed OSR is `0.8811`, essentially not better than full `0.8841`

Primitive GT density reference in the current local data:

- `ps_grasp_single_1k` test split:
  - stored non-colliding GT mean: `21.32`
  - eval resampled with `rot30 + trl10` mean: `71.54`
- `ps_grasp_multi_1k` current local test split:
  - stored non-colliding GT mean: `65.88`
  - eval resampled with `rot30 + trl10` mean: `191.88`

Interpretation:

- GraspNet88 full mean `85.59` is not globally sparse relative to primitive single eval (`71.54`), but it has a few sparse outliers.
- Main result should keep full `88` objects.
- An optional sensitivity result can exclude only scenes below `20` GT, but filtering by the mean would discard too many objects and create a biased subset.

Primitive per-class GSR statistic fix:

- issue found from `kgnV2_test_multi_single` primitive single-object eval:
  per-class successful predictions were divided by all predictions from the whole test set, so per-class GSR was artificially too low.
- fix location: `src/lib/datasets/dataset/ps_grasp.py`
- corrected logic:
  - `all` GSR still uses all accepted predictions as the denominator.
  - in single-object scenes, each class GSR uses predictions from images of that class as the denominator.
  - in multi-object scenes, class-level GSR is reported as `NA` because predictions are class-agnostic and cannot be assigned to one object type without extra target ownership.
- validation command:
  `kgnV2_test_multi_single_evalclassfix_d03_a45`, official `exp/kgnv2.pth`, primitive single test, `dist_th=0.03`, `angle_th=45`, `rot_sample_num=30`, `trl_sample_num=10`.
- validation result:
  - all: `0.9502 / 0.7817 / 1.0000`
  - cuboid: `0.9734 / 0.9600 / 1.0000`
  - cylinder: `0.8857 / 0.7447 / 1.0000`
  - sphere: `0.9967 / 0.5000 / 1.0000`
  - semi_sphere: `0.9978 / 0.9950 / 1.0000`
  - stick: `0.9466 / 0.8548 / 1.0000`
  - ring: `0.9831 / 0.9768 / 1.0000`
- interpretation:
  this is an evaluation-reporting bug fix only; it does not change model inference, PnP, pose matching, or the all-class aggregate metric definition.

GraspNet88 `refine_scale` diagnostic evaluation with official `exp/kgnv2.pth`:

- protocol:
  KGNv2 model + `--sep_scale_branch` + `--scale_kpts_mode 1` + extra `--refine_scale`
- role:
  diagnostic RGB-D depth scale correction, not the pure original KGNv2 inference protocol.
- audit:
  all three refine-scale runs loaded `440` samples and had the same candidate counts as no-refine:
  `decoded_candidates_total=42506`, `score_filtered_candidates_total=11492`,
  `accepted_candidates_total=11457`, `images_with_any_prediction=438 / 440`.
- `scale_refine_failed_total=0` for all three thresholds.
- strict threshold `dist_th=0.01`, `angle_th=20`:
  - metrics: `0.0614 / 0.0135 / 0.3750`
  - `images_with_any_eval_success=165 / 440`
  - `eval_successful_prediction_total=704`
  - unique-object any-view success: `67 / 88`
  - unique-object all-5-view success: `9 / 88`
- standard threshold `dist_th=0.02`, `angle_th=30`:
  - metrics: `0.2868 / 0.0864 / 0.8136`
  - `images_with_any_eval_success=358 / 440`
  - `eval_successful_prediction_total=3286`
  - unique-object any-view success: `86 / 88`
  - unique-object all-5-view success: `43 / 88`
- relaxed threshold `dist_th=0.03`, `angle_th=45`:
  - metrics: `0.5424 / 0.2696 / 0.9364`
  - `images_with_any_eval_success=412 / 440`
  - `eval_successful_prediction_total=6214`
  - unique-object any-view success: `87 / 88`
  - unique-object all-5-view success: `70 / 88`
- interpretation:
  depth-based scale refinement consistently improves external GraspNet88 mesh eval metrics, but it must be reported as an additional diagnostic protocol rather than the pure paper-2 KGNv2 inference setting.

Object-level notes for GraspNet88 `refine_scale` relaxed eval:

- local GraspNet assets provide object ids `000..087` and mesh files, but no semantic object-name table was found in `data/external/graspnet/raw/models/`.
- dataset composition by mesh bbox max dimension:
  - small `<0.10 m`: `30` objects
  - medium `0.10..0.18 m`: `38` objects
  - large `>=0.18 m`: `20` objects
- geometry composition by simple bbox heuristics:
  - compact `aspect < 2`: `33` objects
  - elongated `aspect >= 3`: `30` objects
  - thin/flat `min_dim < 0.035 m`: `18` objects
- relaxed `3cm + 45deg` no-success object:
  - object `065`: `0 / 5` successful views, `0 / 49` successful predictions, bbox approx `(0.086, 0.200, 0.044) m`, aspect `4.52`, non-colliding GT only `2`.
- standard `2cm + 30deg` no-success objects:
  - object `049`
  - object `065`
- strict `1cm + 20deg` no-success objects:
  - `000, 004, 008, 009, 010, 015, 020, 021, 031, 032, 046, 049, 051, 055, 057, 062, 064, 065, 072, 079, 081`
- size-group relaxed performance:
  - small `<0.10 m`: image success `149 / 150 = 99.3%`, object any-view success `30 / 30`, group GSR `0.656`
  - medium `0.10..0.18 m`: image success `179 / 190 = 94.2%`, object any-view success `38 / 38`, group GSR `0.560`
  - large `>=0.18 m`: image success `84 / 100 = 84.0%`, object any-view success `19 / 20`, group GSR `0.355`
- interpretation:
  in the single-object synthetic mesh setting, the model does not mainly fail on small objects. Small and compact objects are handled well; larger, elongated, and sparse-label objects are harder. This should not be overgeneralized to real cluttered small-object scenes.

Current GraspNet88 close-out status:

- GraspNet88 single-object synthetic mesh eval is complete.
- Main quantitative evidence:
  - KGNv2 no-refine three-threshold table.
  - KGNv2 + Refine-Scale three-threshold table.
- Main qualitative evidence:
  - selected atypical-object box/keypoint prediction panels.
  - selected atypical-object two-finger gripper panels.
  - selected atypical-object Refine-Scale two-finger gripper panels.
- Thesis positioning:
  - no-refine = paper-2/KGNv2 original-style external-eval protocol.
  - Refine-Scale = inference-side RGB-D scale refinement improvement.
  - GraspNet88 synthetic single-object mesh eval = complex-object geometry generalization evidence.
  - GraspNet real RGB-D eval = real-domain exploratory/diagnostic evidence.

GraspNet88 qualitative two-finger gripper visualization:

- purpose:
  create presentation-friendly qualitative figures for several atypical GraspNet objects whose shapes differ strongly from the six primitive training classes.
- tool:
  `src/tools/render_selected_graspnet88_grippers.py`
- source analysis:
  `exp/grasp_pose/t63_graspnet88_single_kgnv2_official_relaxed_d03_a45_visall/analysis_analysis_t63_graspnet88_single_kgnv2_relaxed_d03_a45_visall`
- output:
  `presentation/two_finger_gripper_panels_top3/`
- additional output:
  `presentation/two_finger_gripper_panels_top10/`
- refine-scale output:
  `exp/grasp_pose/t63_graspnet88_single_kgnv2_refinescale_relaxed_d03_a45/analysis_analysis_t63_graspnet88_single_kgnv2_refinescale_relaxed_d03_a45/presentation/two_finger_gripper_panels_top10_refinescale/`
- recommended montage:
  `presentation/two_finger_gripper_panels_top10/graspnet88_selected_two_finger_gripper_montage.jpg`
- recommended refine-scale montage:
  `presentation/two_finger_gripper_panels_top10_refinescale/graspnet88_selected_two_finger_gripper_montage.jpg`
- backup clean montage:
  `presentation/two_finger_gripper_panels_top3/graspnet88_selected_two_finger_gripper_montage.jpg`
- selected object ids:
  `024, 029, 030, 031, 033, 050, 056, 072, 078, 081, 083, 085`
- visualization policy:
  for each selected image, rerun official `exp/kgnv2.pth` inference, evaluate with the relaxed `3cm + 45deg` mesh-label protocol, choose up to the top 10 successful predictions by score, and render them as green two-finger / parallel-jaw gripper meshes. A top-3 version is retained as a cleaner backup for dense slide layouts.
- interpretation:
  this is qualitative evidence only. It should be used to show that a primitive-trained KGNv2 model can generate plausible 6D gripper candidates on complex GraspNet mesh objects. It is not a replacement for the quantitative GraspNet88 standard/relaxed metrics.
- refine-scale note:
  the `--refine_scale` qualitative montage is best described as an inference-side RGB-D scale refinement visualization. It should not be merged with the no-refine montage under one protocol label.
