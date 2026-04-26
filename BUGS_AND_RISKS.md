# Bugs And Risks

This file records known project risks and deferred issues. It is not a bug tracker
for every experiment failure; keep it focused on risks that future Codex/agent
sessions must not forget.

Last updated: 2026-04-25

## Current High-Risk Misstatements

- Do not describe T6 v1 as arbitrary AIGC mesh automatic grasp annotation; it is controlled geometry distribution augmentation.
- Do not describe T3.4 `random` as effective; it is a negative/control result.
- Do not describe T3.4 `nearest_cost` as a new overall strongest model; it is a positive b1/e5 attribution result close to the T2 strong-baseline range.
- Do not describe T3.5a `nearest_conf` as effective or as the new mainline; it completed the full train/test cycle but did not beat `T3.4 nearest_cost` in a useful overall sense.
- Do not frame T3.4 mainly as "better than T3.2b-fix"; the main comparison should be against `paper2-clean`, `d4ff8ca no-conf base`, and T2 strong baselines.
- Do not compare T3.4 `random` and `nearest_cost` runs against older results unless the data source, training budget, model checkpoint type, and inference settings match.
- Do not say T3.1 is verified effective. It is implemented and shows recovery-style positive signal relative to `ctrl_t2off`, but it has not beaten the strong internal baseline.
- Do not call `KGN-main internal kgnv2base` the official `paper2-clean` baseline.
- Do not describe `paper2-clean baseline` vs `KGN-main T2` as a strict single-variable T2 ablation.
- Do not use the cloud T2 repeat `model_last.pth` as the final main thesis conclusion without noting it is a short-budget b1/e5 attribution checkpoint and may not have the cleanest training closure.
- Do not say KGN-Pro-main is a complete implementation of the KGN-Pro paper.
- Do not call smoke training an effectiveness result.
- Do not treat early P3 best, P4-lite-v2, or "fine-tune 3 epochs without pose_reg" as the latest verified mainline.
- Do not mix `model_best.pth` and `model_last.pth` as strict same-class evidence without explicitly saying which one was used.
- Do not write b1/e5 quick attribution numbers as final full-budget thesis results.
- Do not write that `T3.4 nearest_cost` has cleanly beaten `T2 cloud repeat + P3 on` without noting that the cloud-repeat reference only preserved `model_last.pth` because the run was interrupted by power loss.
- Do not describe `T3.5b` top-k / quality-filter variants as effective mainline improvements; they improve precision-like `GSR` slightly but reduce `GCR` and `OSR`.
- Do not overstate `T3.5b --reproj_error_th 5`; it is a stable outlier-cleaning / analysis setting, not a new success-generating module.

## Engineering Risks

### T6 geometry enhancement keeps original object labels

Observation:

- `PSGrasp` evaluation and scene reconstruction currently assume the original primitive object categories.
- Introducing new `obj_types` directly would require changing loader, reconstruction, evaluation, analysis, and visualization paths.

Current decision:

- T6 v1 keeps geometry-enhanced objects under the existing labels such as `cuboid`, `cylinder`, `ring`, and `stick`.
- The first T6 change is broader and more extreme dimension sampling, not a new arbitrary mesh object taxonomy.
- If T6 later introduces new mesh classes, it needs a dedicated schema/evaluation update rather than silently adding labels to `scene_info.json`.

### T6.2 ACRONYM labels are available but ShapeNetSem meshes are still a blocker

Observation:

- Full ACRONYM `.h5` labels have been downloaded and extracted locally under `data/external/acronym/grasps/`.
- The h5-only audit found `8836` grasp files and `832` target-category files.
- Target categories such as `Mug`, `Bottle`, `Bowl`, `Cup`, `WineBottle`, `Knife`, `Camera`, `Stapler`, `Pencil`, and `CellPhone` have enough successful width-valid grasps for dataset construction.
- Current local mesh count is `0`; therefore there are still no full-data training candidates.

Current decision:

- Do not generate `ps_grasp_single_mesh_t62_1k` or run b1/e5 until matching ShapeNetSem meshes are present and loadable.
- Do not claim full ACRONYM training data has been integrated; only the label side is locally available.
- ShapeNetSem mesh download requires user-side account/registration or an already downloaded local mesh path.

### T6.3 GraspNet object-level data is promising but not yet full-experiment ready

Observation:

- GraspNet object-level `models/` and `grasp_label/` have been extracted locally.
- The first full asset audit found `88 / 88` loadable meshes and `88 / 88` loadable label files.
- `grasp_label/*.npz` contains `points`, `offsets`, `scores`, and object-level `collision`.
- After score, width, and object-level collision filtering, the audit found `8,419,024` valid grasps.
- T6.3-C generated an accepted PS-style smoke dataset:
  - `data/ps_grasp_single_graspnet_t63_smoke_v2`
  - 50 scenes
  - 15000 total grasps
  - 4675 non-colliding grasps
  - 3995 / 4000 sampled projected keypoints inside the image
- `PSGrasp` loader/training smoke completed 20 iterations on this dataset.

Current decision:

- Treat GraspNet as the most promising current external-mesh data route while ShapeNetSem access is pending.
- Do not use the scene-level `collision_label/` package in the first pass; it is large and not required for object-level synthetic rendering.
- It is now fair to claim that a GraspNet object-level PS-style smoke conversion has been implemented and loader-verified.
- Do not claim GraspNet has produced an effective training improvement yet.
- Do not run b1/e5 until the smoke visualizations are manually inspected and a 1k GraspNet/mixed dataset is generated with a fixed comparison protocol.

Risk:

- GraspNet frame conventions, score semantics, and grasp-parameter-to-4x4 conversion still need careful verification before training.
- Synthetic rendering with GraspNet object meshes will not be identical to official GraspNet scene RGB-D images, so thesis wording must describe it as object-level GraspNet-label adaptation, not full GraspNet training.
- The partial first directory `data/ps_grasp_single_graspnet_t63_smoke` has only `48 / 50` scenes and must not be used as the accepted smoke dataset.

### T6.4 real GraspNet RGB-D evaluation is diagnostic, not a main quantitative claim yet

Observation:

- `data/external/graspnet/real_rgbd_subset/` contains `90` real GraspNet RealSense scenes and `1440` converted frames.
- `data/ps_grasp_real_graspnet_t64_smoke` and `data/ps_grasp_real_graspnet_t64_eval` have been generated.
- Strict smoke evaluation with official `exp/kgnv2.pth` gave `0.0000 / 0.0000 / 0.0000`.
- This strict zero is not a silent-model failure:
  - `decoded_candidates_total=4790`
  - `score_filtered_candidates_total=114`
  - `pnp_failed_total=0`
  - `images_with_any_prediction=32 / 48`
- Relaxed evaluation with `center_thresh=0.1`, `dist_th=0.05`, and `angle_th=45` gave `0.0190 / 0.0020 / 0.0540`.
- Relaxed diagnostics found `17 / 48` images with at least one eval success and `89` successful prediction candidates.
- Adding `--refine_scale` under the same relaxed setting gave `0.3894 / 0.0371 / 0.5047`.
- With `--refine_scale`, all `48 / 48` smoke images had at least one eval success and there were `1628` successful prediction candidates.
- Full 1440-frame evaluation with the same `--refine_scale` protocol gave `0.4751 / 0.0443 / 0.4876`, with `1434 / 1440` images having at least one eval success.
- The converted GraspNet smoke data uses the RealSense intrinsic matrix from GraspNet metadata, and depth conversion follows `factor_depth=1000`.
- The dominant diagnosed issue is scale mismatch: real object-mask depth mean is about `0.412 m`, while no-refine accepted predicted scale mean is about `0.582 m`.

Current decision:

- Do not write that `exp/kgnv2.pth` cannot grasp real objects.
- It is fair to write that the primitive-trained KGNv2 model can produce plausible real RGB-D grasp candidates, and that real-depth scale refinement is necessary for meaningful converted GraspNet-real matching.
- Do not use T6.4 as the main quantitative effectiveness table unless a stronger, validated evaluation protocol is established.
- Use T6.4 primarily as external real-domain generalization exploration, qualitative visualization, and failure-analysis evidence.
- Do not use `--rot_sample_num` or `--trl_sample_num` on converted mesh/real GraspNet eval sets; those options trigger primitive-only GT reconstruction and crash on `obj_type="mesh"`.

Risk:

- GraspNet object-level labels projected through real-scene meta poses are extremely dense and may not match the KGN primitive evaluation assumptions.
- Real RGB-D domain shift, background clutter, object texture, segmentation convention, scale prediction bias, and gripper-frame convention can all depress strict metrics.
- The existing Mayavi/point-cloud qualitative result can support "the model proposes plausible grasps", but should not be overclaimed as physical robot success without real execution.

### T3.4 target selection is training-side only

Observation:

- T3.4 adds `first`, `random`, and `nearest_cost` target selection inside `ProbPoseAuxLoss`.
- It does not change `test.py`, `decode.py`, `keypoint_graspnet.py`, or `pose_recover/`.

Current decision:

- Treat T3.4 as a completed b1/e5 short-budget attribution experiment, not a final full-budget thesis result.
- `random` completed but is negative; keep it only as a control.
- `nearest_cost` completed and is the only T3.4 mode worth carrying forward.
- `first` remains a compatibility path; only run b1/e5 for it if a strict same-branch control is needed later.

### T3.5a confidence-aware target selection is closed as a non-mainline result

Observation:

- `T3.5a nearest_conf` completed cloud smoke, b1/e5 training, best/last deterministic evaluation, result transfer, and local analysis.
- `model_best.pth` reached `0.1960 / 0.2026 / 0.7080`.
- `model_last.pth` degraded to `0.0978 / 0.0980 / 0.4750`.

Current decision:

- Treat T3.5a as an implemented and fully analyzed negative/partial result.
- Keep the branch as an archive of the attempt.
- Do not continue the next main experiment from the T3.5a branch.
- If confidence-aware training-side selection is revisited later, reopen it as a new dedicated retry with a weaker coupling design.

### T3.5b inference-side enhancement is a diagnostic/quality-cleaning result

Observation:

- `post_pnp_score_type=none` reproduced the T3.4 frozen checkpoint result.
- Top-k and quality-threshold variants remove many accepted candidates and lose object-level successes.
- `--reproj_error_th 5` transfers to both T3.4 and T2 local-repeat checkpoints without hurting `OSR`, but it only removes outliers.

Current decision:

- Keep the code as optional inference-side analysis and quality-cleaning infrastructure.
- Do not continue broad T3.5b parameter sweeps as the next main priority.
- If a new `KGN-main` branch is opened, use closed T3.5b as the default base only because its defaults preserve old behavior; use `T3.4 @ 1fb0084` only when strict attribution requires excluding T3.5b code.

### GraspNet88 protocol labeling risk

Observation:

- GraspNet88 single-object synthetic mesh eval now has two protocols:
  - `KGNv2 no-refine`: official KGNv2 checkpoint with paper-2 scale branch and no additional depth correction.
  - `KGNv2 + Refine-Scale`: the same official checkpoint plus inference-side RGB-D depth scale refinement.
- `Refine-Scale` improves metrics substantially:
  - relaxed `3cm + 45deg`: `0.4338 / 0.2189 / 0.8841` -> `0.5424 / 0.2696 / 0.9364`.

Risk:

- Writing `KGNv2 + Refine-Scale` as if it were the pure paper-2/KGNv2 original inference protocol would be inaccurate.
- Writing it as a training-side improvement would also be inaccurate; it does not change the network weights.

Current decision:

- Use `KGNv2 no-refine` for the paper-2 original-style external-eval line.
- Use `KGNv2 + Refine-Scale` as an inference-side RGB-D scale refinement improvement.
- Keep both protocols in separate rows or clearly separate paragraphs in thesis tables.

### GraspNet88 sparse-label and object-difficulty risk

Observation:

- The 88-object synthetic mesh eval covers all object ids `000..087`, but some objects have few non-colliding GT grasps after placement and collision filtering.
- Sparse-label outliers:
  - object `009`: `14` non-colliding GT
  - object `040`: `19` non-colliding GT
  - object `065`: `2` non-colliding GT
- Under Refine-Scale relaxed `3cm + 45deg`, only object `065` has no successful view:
  `0 / 5` successful views and `0 / 49` successful predictions.

Risk:

- A failed sparse-label object should not be interpreted as the model generally failing all complex objects.
- Filtering by mean GT count would create a biased easier subset and should not replace the main all-88 result.

Current decision:

- Keep the full 88-object result as the main external mesh evaluation.
- Mention object `065` as a limitation case caused by both high-aspect-ratio geometry and very sparse GT.
- Optional sensitivity analysis can exclude only scenes below `20` GT, but the primary result remains full coverage.

### `opts.py --pnp_type` default mismatch

Observation:

- `opts.py` has a `--pnp_type` default that should be checked against available choices.

Current decision:

- Do not prioritize this before T3.1 verification unless it blocks a real command path.

### Trainer `save_result` decode signature risk

Observation:

- The trainer-side `save_result` path may still use an old `grasp_pose_decode(...)` calling pattern.
- Standard `src/test.py` evaluation uses the detector path and is the current main evaluation route.

Current decision:

- Do not prioritize this before T3.1 validation unless `main.py --test` or trainer-side result saving becomes necessary.

### Untracked `src/lib/third_party/__init__.py`

Observation:

- `src/lib/third_party/__init__.py` is currently an untracked empty file.

Current decision:

- Do not delete or submit it unless a dedicated small fix decides it is needed.

## Experiment Risks

- Different training budgets must not be mixed in one main comparison table.
- Different datasets must not be mixed in one main comparison table.
- Different inference parameters must not be mixed in one main comparison table.
- `b1/e5` is high-variance and should be treated as a fast attribution budget.
- `model_best.pth` and `model_last.pth` can differ materially and must be labeled separately.
- `paper2-clean baseline` and `KGN-main` do not share a bit-identical code path; candidate generation, detector/test flow, dataset reading fixes, and analysis hooks may differ even when `--conf_branch` is off.
- `conf_fusion` is P3 inference behavior. Turning it off tests P3-off/nofusion; it does not remove all P1/P2/T2-era code path differences.
- Smoke train/test only proves that the link runs; it does not prove algorithmic improvement.
- Cloud-generated `ps_grasp_multi_1k` data is not trusted and should not be used as the current formal data source.
- Current trusted cloud data is the local-uploaded `ps_grasp_single_1k`.
- Formal T3.1 validation still needs controlled training, testing, and result analysis against a strong baseline.

## Current Attribution Risks

- `paper2-clean baseline b1/e5` around `0.1013 / 0.0922 / 0.4920` is the official-clean fast baseline.
- `d4ff8ca no-conf base b1/e5` around `0.1597 / 0.1585 / 0.6440` is the main KGN-main no-confidence attribution baseline.
- `old T2 best + P3 on` around `0.2021 / 0.2088 / 0.7270`, `T2 cloud repeat model_last + P3 on` around `0.1837 / 0.1998 / 0.7530`, and `T2 local repeat model_best + P3 on` around `0.2090 / 0.2320 / 0.7430` are the primary T2 strong-baseline references.
- `T2 cloud repeat model_last + P3 on` must be labeled carefully: it is a strong cloud-trained reference, but it is not a clean best-checkpoint reference because the run was interrupted by power loss before preserving a comparable `model_best.pth`.
- `KGN-main internal kgnv2base b1/e5` around `0.1995 / 0.2240 / 0.7670` is retained as a historical/internal reference, not the dominant T3.4 comparison target.
- `T2 cloud repeat model_last + P3 on` around `0.1837 / 0.1998 / 0.7530` supports that T2 is strong against official clean, but it is not yet the strictest single-variable proof.
- `T2 cloud repeat model_last + P3 off` around `0.1618 / 0.1483 / 0.6840` shows P3 helps this checkpoint, but nofusion still remains above paper2-clean.
- `T3.4 nearest_cost` around `0.1954 / 0.2080 / 0.7480` is positive and near the T2 strong-baseline range, but it does not yet beat all T2 references in all three metrics.
- `T3.4 random` around `0.1096 / 0.1291 / 0.5060` is negative.
- `T3.5a nearest_conf best` around `0.1960 / 0.2026 / 0.7080` is not good enough to replace `T3.4 nearest_cost`; it raises `GSR` only marginally while lowering `GCR` and clearly lowering `OSR`.
- `T3.5a nearest_conf last` around `0.0978 / 0.0980 / 0.4750` shows strong late-epoch degradation and must not be used as continuation evidence.

## KGN-Pro-main Migration Risks

- `KGN-Pro-main` is reference-only.
- Do not submit `KGN-Pro-main/`.
- Do not migrate `KGN-Pro-main` as a whole.
- Do not directly copy these main-chain files into KGN-main:
  - `KGN-Pro-main/src/test.py`
  - `KGN-Pro-main/src/keypoint_graspnet.py`
  - `KGN-Pro-main/src/lib/pose_recover/`
  - `KGN-Pro-main/src/lib/trains/base_trainer.py`
- `KGN-Pro-main` training side contains useful EPro-PnP / MonteCarloPoseLoss / w2d ideas, but its test and inference chains remain largely KGNv2-style.

## File Safety Risks

- Never delete dirty worktree files without explicit user confirmation.
- Never run cleanup commands such as `rm -rf` unless explicitly requested and scoped.
- Never submit:
  - `data/`
  - `exp/`
  - `pretrained_weights/`
  - `KGN-Pro-main/`
  - `*.tar`
  - `*.tar.gz`
  - checkpoints
  - large logs
  - credentials
- Never compress the whole cloud `exp/grasp_pose/`; compress only one `<exp_id>` directory.

## Security Risks

- Do not record tokens, passwords, cookies, SSH private keys, Codex auth files, GitHub credentials, or full sensitive config files in project documentation.
- `/home/xyk/.codex` and `/root/.codex` are auth/history/config locations, not project files.
- The repository root `.codex` is currently an ignored zero-byte ordinary file and should not be treated as the Codex auth directory.
