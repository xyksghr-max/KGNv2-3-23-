# Project Decisions

This file records stable project decisions so future sessions do not reopen
settled questions after context compaction.

## 2026-04-26 T6.3 Uses GraspNet Object-Level Assets While ShapeNetSem Is Pending

Decision:

- T6.3 switches the next dataset-feasibility effort from ACRONYM full-data construction to GraspNet object-level assets.
- Use GraspNet `models/` and `grasp_label/` first.
- Do not download the 80GB+ official RGB-D scene image packages in the first pass.
- Do not extract or depend on scene-level `collision_label/` before object-level synthetic rendering is proven.

Why:

- ShapeNetSem access for full ACRONYM is still uncertain.
- GraspNet object models and object-level grasp labels are locally available and loadable.
- The full asset audit found `88` usable objects and `8,419,024` valid grasps after score, width, and object-level collision filtering.
- This route is better aligned with the current PS-style synthetic rendering pipeline than waiting indefinitely for ShapeNetSem approval.

Consequences:

- The next implementation target is a small `ps_grasp_single_graspnet_t63_smoke` dataset, not b1/e5 training.
- GraspNet label conversion must explicitly verify frame conventions and score semantics.
- The resulting dataset should be described as a GraspNet object-level mesh-label adaptation, not full GraspNet scene training.
- ACRONYM + ShapeNetSem remains a retained route and can resume after mesh access is granted.

Status:

- active

## 2026-04-25 T6 Uses Controlled Geometry Enhancement Before Arbitrary AIGC Mesh

Decision:

- T6 v1 will test a `primitive + controlled geometry-enhanced` mixed dataset.
- The first implementation keeps enhanced objects inside the existing PS object taxonomy (`cuboid`, `cylinder`, `ring`, `stick`) and changes their size/aspect-ratio distributions.
- The first T6 comparison uses the same training image count and b1/e5 budget as the primitive-only baseline.
- Arbitrary Text-to-3D / Objaverse `.obj` meshes are deferred to a later T6 stage or simulation testbed stage.

Why:

- Existing `PSGrasp` evaluation and reconstruction paths assume the original primitive object types.
- Keeping object types unchanged preserves `generate_grasp_family()`, simplified gripper collision filtering, and the current `test.py` metric path.
- Arbitrary mesh data would need a new grasp-labeling pipeline with surface sampling, collision checking, stability handling, and quality filtering; this is too risky as the first dataset pilot.
- Texture-only generative augmentation is not prioritized because current validation is offline KGN-main evaluation and PyBullet simulation rather than real-camera robot deployment.

Consequences:

- T6 v1 can be described as controlled geometric distribution augmentation, not full AIGC mesh grasp annotation.
- T6 v1 success requires no obvious regression on primitive tests and preferably a gain on a geometry-enhanced held-out test.
- Generated data stays out of Git.

Status:

- active

## 2026-04-24 T3.5b Is Kept As Analysis Infrastructure, Not A Mainline Gain

Decision:

- `T3.5b inference-side enhancement` is implemented and locally validated.
- It should be closed as a diagnostic / quality-cleaning branch, not as a mainline performance improvement.
- The next `KGN-main` branch should normally start from the closed `feat/t3.5b-inference-side-enhancement` branch because default behavior is backward-compatible.
- If the next experiment requires strict exclusion of T3.5b inference code, start from `feat/t3.4-multigrasp-target-matching @ 1fb0084`.
- Do not start the next mainline from `feat/t3.5-conf-aware-target-selection`.

Why:

- E0 parity reproduced `T3.4 nearest_cost = 0.1954 / 0.2080 / 0.7480`.
- Top-k and quality-filter variants improved `GSR` slightly but reduced `GCR` and `OSR`.
- `--reproj_error_th 5` preserved `OSR` on both T3.4 and T2 local-repeat checkpoints and reduced reprojection outliers, but did not create new successful images.

Consequences:

- T3.5b can be written as an inference-side error-analysis and outlier-filtering result.
- Further broad post-PnP threshold sweeps are not the best next priority.
- The next high-value work should be either simulation/physical-style evaluation closure or a carefully scoped dataset/generalization pilot, not another unbounded T3.5b tuning round.

Status:

- active

## 2026-04-24 T3.5a Is Closed And T3.5b Should Start From T3.4

Decision:

- `T3.5a nearest_conf` is implemented, cloud-validated, and closed as a non-mainline result.
- `T3.5a nearest_conf` does not replace `T3.4 nearest_cost` as the current best `KGN-Pro-inspired` training-side result.
- The next main task should be `T3.5b inference-side enhancement`.
- `T3.5b` should start from the documented `T3.4 nearest_cost` line:
  - `feat/t3.4-multigrasp-target-matching @ 1fb0084`
- The active implementation branch for that next task is `feat/t3.5b-inference-side-enhancement`.
- `feat/t3.5-conf-aware-target-selection` should be kept as an archive/result branch, not used as the default base for the next main experiment.

Why:

- `T3.5a nearest_conf best` reached `0.1960 / 0.2026 / 0.7080`.
- `T3.5a nearest_conf last` degraded to `0.0978 / 0.0980 / 0.4750`.
- Relative to `T3.4 nearest_cost = 0.1954 / 0.2080 / 0.7480`, T3.5a only gained a negligible amount on `GSR`, while losing on `GCR` and clearly losing on `OSR`.
- Candidate-level analysis shows `nearest_conf` reduced `score_filtered`, `accepted`, and `successful_preds`, while shifting supervision toward easier/high-confidence matches.
- Starting T3.5b from T3.4 keeps inference-side attribution clean.

Consequences:

- Future writeups should say:
  - T3.5a verified that confidence-aware target selection is runnable,
  - but the current formulation is not a mainline improvement.
- If training-side confidence-aware selection is revisited later, it should be reopened as a new dedicated retry rather than silently continued from this branch.
- T3.5b should first test inference-side ranking/post-process improvements without inheriting T3.5a training-side behavior.

Status:

- active

## 2026-04-23 T3.4 Result Interpretation Uses T2 Strong Baselines

Decision:

- T3.4 `nearest_cost` is a positive b1/e5 attribution result, but not a new overall strongest mainline.
- T3.4 `random` is a negative/control result and should not be carried forward as a main method.
- T3.4 should be compared primarily against `paper2-clean`, `d4ff8ca no-conf base`, and T2 strong baselines.
- `KGN-main internal kgnv2base` remains a historical/internal reference, not the dominant comparison target for T3.4 claims.

Why:

- T3.4 `nearest_cost` reached `0.1954 / 0.2080 / 0.7480`, close to the T2 strong-baseline range.
- The main T2 references are:
  - old T2 best + P3 on: `0.2021 / 0.2088 / 0.7270`
  - T2 cloud repeat model_last + P3 on: `0.1837 / 0.1998 / 0.7530`
  - T2 local repeat model_best + P3 on: `0.2090 / 0.2320 / 0.7430`
- The cloud-repeat T2 reference is strong, but it is still a `model_last.pth` reference rather than a clean best-checkpoint reference because that run was interrupted by power loss.
- Candidate-level analysis shows T3.4 `nearest_cost` has strong geometry quality (`accepted_reproj_mean = 0.6741`) but still does not dominate every T2 reference in every metric.
- The project goal is not to prove "prob_pose_loss alone beats T3.2b-fix"; it is to gradually build a KGN-Pro-lite path combining confidence/correspondence weighting, EPro-PnP/MC loss, probabilistic inference, x2d, and multi-grasp target matching where feasible.

Consequences:

- Future writeups should say: T3.4 validates `nearest_cost` multi-grasp target matching as a useful KGN-Pro-inspired training-side module under b1/e5 attribution.
- Do not write that T3.4 fully reproduces KGN-Pro or surpasses all T2 baselines.
- The next method branch should build from T3.4 `nearest_cost` evidence toward a combined KGN-Pro-lite route, while keeping the current deterministic test chain stable unless a dedicated inference task is opened.

Status:

- active

## 2026-04-23 T3.4 Starts From Clean T3.2b-Fix Lineage

Decision:

- T3.4 starts from `134cd27 fix: stabilize probabilistic pose auxiliary loss`.
- The T3.4 branch is `feat/t3.4-multigrasp-target-matching`.
- T3.4 implements only training-side target selection for `ProbPoseAuxLoss`.

Why:

- T3.3b and T3.3c were useful negative/diagnostic experiments but are not the best base for a new target-matching test.
- Starting from `134cd27` keeps the experiment closer to the stable T3.2b-fix line.
- Target matching is a smaller and cleaner KGN-Pro-inspired idea than migrating inference or pose-recovery chains.

Consequences:

- Do not stack T3.4 on top of T3.3c.
- Do not change `test.py`, `decode.py`, `keypoint_graspnet.py`, or `pose_recover/` for T3.4.
- Evaluate `first`, `random`, and `nearest_cost` as separate experiment modes.
- Treat all b1/e5 results as short-budget attribution until larger validation exists.

Status:

- completed for implementation and b1/e5 attribution

## 2026-04-19 Main Workspace And Workflow

Decision:

- The main development workspace is `/home/xyk/KGN-main`.
- GitHub is the version transfer, branch archive, and rollback anchor.
- The cloud workspace `/root/autodl-tmp/KGN-main` is for training and evaluation.
- Remote Codex on the cloud is only a backup for environment checks and logs.

Why:

- Local Codex is more stable for code modification and documentation.
- Cloud resources are best used for GPU training and evaluation.
- GitHub provides a clean synchronization and rollback boundary.

Consequences:

- Code changes should be made locally first.
- Cloud training starts after pulling the target branch.
- Cloud results are returned as single experiment directories.

Status:

- active

## 2026-04-21 Official Clean Baseline And Internal Strong Baseline Are Different

Decision:

- `paper2-clean baseline` refers only to the official-clean KGN paper2 repository path, with the minimal NumPy compatibility fix.
- `KGN-main internal kgnv2base` refers to a strong internal baseline trained/evaluated in the KGN-main code state, with no `conf_branch`, no `conf_fusion`, and no `prob_pose_loss`.
- These two baselines must not be renamed into each other.

Why:

- The official-clean b1/e5 baseline is around `0.1013 / 0.0922 / 0.4920`.
- The KGN-main internal kgnv2base b1/e5 result is around `0.1995 / 0.2240 / 0.7670`.
- KGN-main includes historical data, test, detector, decode, analysis, and training-path changes that are not all controlled by `--conf_branch`.

Consequences:

- `paper2-clean` remains the official-clean baseline for comparison to the released paper2 code.
- `KGN-main internal kgnv2base` is a strong internal/historical reference and should not be confused with the official-clean baseline.
- For T3.4 and later KGN-Pro-inspired comparisons, the main practical baselines are `paper2-clean`, `d4ff8ca no-conf base`, and the T2 strong baselines; `KGN-main internal kgnv2base` is retained as a reference line rather than the dominant comparison target.
- Do not present paper2-clean vs KGN-main T2 as a strict single-variable T2 ablation without caveats.

Status:

- active

## 2026-04-21 Prioritize d4ff8ca No-Conf Attribution Before Paper2-Clean T2 Migration

Decision:

- First complete the `d4ff8ca no-conf base b1/e5` experiment in `/root/autodl-tmp/KGN-main`.
- Only after seeing that result decide whether to migrate T2 into `/root/autodl-tmp/KGN-paper2-clean` for a stricter `paper2-clean + T2-only` run.

Why:

- The no-conf run is cheaper and directly tests whether the strong baseline already exists at the T2 commit when T2/P3 runtime switches are off.
- If no-conf base is weak, T2 evidence against official clean is already much clearer.
- If no-conf base is strong, the strict T2-only migration becomes more important for thesis-grade attribution.
- The completed no-conf result is around `0.1597 / 0.1585 / 0.6440`, above paper2-clean but below the main T2 P3-on references.

Consequences:

- The no-conf result should be used as the main KGN-main no-confidence attribution baseline.
- It does not replace T2 P3-on as the strong mainline.
- It reduces the need to keep using `KGN-main internal kgnv2base` as the main comparison axis for T3.4.

Status:

- completed for b1/e5 attribution

## 2026-04-21 T3.2 Should Challenge The Strong Internal Baseline

Decision:

- Do not continue tuning T3.1 only against weak `ctrl_t2off` control results.
- The next T3 direction should preferentially test a cleaner `KGNv2-base + prob_pose_loss` design that does not depend on `conf_branch` or `conf_fusion`.

Why:

- T3.1 recovered performance relative to `ctrl_t2off`, but did not beat `KGN-main internal kgnv2base`.
- Removing `conf_fusion` did not rescue `ctrl_t2off` or `prob_on_signal`; the weaker behavior is not simply a P3 fusion artifact.

Consequences:

- T3.1 may be described as having a recovery-style positive signal, not as verified effective.
- T3.2 should be planned as a clean strong-baseline challenge rather than more conf-fusion parameter search.

Status:

- active

## 2026-04-19 KGN-main Remains The Main Repository

Decision:

- `KGN-main` remains the main development, training, testing, and evaluation repository.
- `KGN-Pro-main` is a local and cloud reference directory only.

Why:

- KGN-main has the working KGNv2-based pipeline and local improvements.
- KGN-Pro-main is incomplete as an implementation of the KGN-Pro paper.
- KGN-Pro-main training side has useful ideas, but its testing and inference chains largely retain KGNv2 logic.

Consequences:

- Do not migrate KGN-Pro-main as a whole.
- Do not submit KGN-Pro-main.
- Only migrate audited, local, useful assets with new KGN-main-compatible integration.

Status:

- active

## 2026-04-19 T2 Is The Latest Verified Strong Mainline

Decision:

- The latest verified strong mainline is T2:
  `exp/grasp_pose/p2_conf_single_r512_e5_800200/model_best.pth`
  with `conf_fusion_alpha = 0.7` and `conf_fusion_min_conf = 0.3`.

Why:

- This is the current confirmed standard baseline after geometry-aware confidence and inference-side calibration.
- Earlier P3 best, P4-lite-v2, and the "fine-tune 3 epochs without pose_reg" line have different roles and must not replace this baseline.

Consequences:

- New method comparisons should default to T2 `model_best.pth + a0.7/g0.3`.
- Historical strong references can be cited for attribution, not as the default baseline.

Status:

- active

## 2026-04-19 T3.1 Is Implemented But Not Verified

Decision:

- T3.1 is a training-side probabilistic pose auxiliary loss prototype.
- T3.1 has been implemented, committed, pushed, and synchronized to the cloud.
- Later short-budget cloud control/prob runs found recovery-style signal relative to `ctrl_t2off`, but T3.1 still has not completed effectiveness validation against the strong internal baseline.

Why:

- The code exists and local/static/smoke-style probes were performed.
- Formal strong-baseline evidence is still missing.

Consequences:

- T3.1 can be described as an implemented prototype with recovery-style positive signal relative to `ctrl_t2off`.
- T3.1 must not be described as verified effective or as the new mainline.
- The next T3 direction should be a clean strong-baseline challenge, as recorded in the 2026-04-21 decision.

Status:

- active

## 2026-04-19 Single Experiment Directory Transfer

Decision:

- Cloud experiment results must be transferred one experiment directory at a time.

Why:

- Compressing all of `exp/grasp_pose/` is slow, risky, and mixes unrelated experiments.
- Single-directory transfer preserves experiment identity and avoids accidental large transfers.

Consequences:

- Cloud source: `/root/autodl-tmp/KGN-main/exp/grasp_pose/<exp_id>`.
- Local target: `/home/xyk/KGN-main/exp/grasp_pose/<exp_id>`.
- Do not submit `exp/` to GitHub.

Status:

- active

## 2026-04-19 Branching Discipline

Decision:

- New features, fixes, validation adjustments, and documentation tasks should start from the latest confirmed branch.
- Each branch should contain one clear task.

Why:

- The project needs reversible, auditable progress.
- Training and evaluation are expensive enough that mixed changes make attribution difficult.

Consequences:

- Do not keep adding unrelated changes directly to the T3.1 baseline branch.
- Use explicit `git add <file>` only.
- Do not use `git add .`.

Status:

- active

## 2026-04-26 T6.3 GraspNet Object-Level PS Conversion

Decision:

- Use GraspNet object-level `models/` and `grasp_label/` as the active external-mesh dataset route while ShapeNetSem access for full ACRONYM remains pending.
- First convert GraspNet object-level grasps into synthetic PS-style RGB-D data with the existing renderer, not the official 80GB+ GraspNet RGB-D scene packages.
- Keep the accepted smoke dataset as `data/ps_grasp_single_graspnet_t63_smoke_v2`.

Why:

- Full local GraspNet asset audit found `88 / 88` loadable meshes and labels, with `8,419,024` valid grasps after score, width, and object-level collision filtering.
- T6.3-C smoke conversion produced 50 PS-style scenes and passed `audit_ps_dataset.py`.
- `PSGrasp` loader/training smoke completed 20 iterations, proving the converted data can enter the current training chain.

Consequences:

- It is now valid to describe T6.3 as an implemented and loader-verified GraspNet-to-PS smoke pipeline.
- It is not yet valid to claim any training-performance improvement.
- Do not start b1/e5 until the smoke visualizations are manually inspected and a 1k GraspNet-derived/mixed dataset protocol is fixed.
- The partial `data/ps_grasp_single_graspnet_t63_smoke` directory with `48 / 50` scenes is diagnostic only.

Status:

- active

## 2026-04-26 T6.4 GraspNet Real RGB-D Evaluation Is Exploratory

Decision:

- Use `data/external/graspnet/real_rgbd_subset/` as an external real RGB-D evaluation source.
- Convert it to PS-style eval format for `test.py`, but do not treat it as a training dataset.
- Use official KGNv2 primitive-trained checkpoint `exp/kgnv2.pth` for the first external real-domain evaluation.
- Keep `train_4.zip` out of the main T6.4 evaluation because it belongs to the GraspNet train split.

Why:

- The real subset contains `90` GraspNet test scenes and `1440` RealSense frames.
- It directly tests the thesis claim that a model trained on simple primitive synthetic data can produce useful grasp candidates on real RGB-D images of complex objects.
- Strict smoke evaluation produced `0 / 0 / 0`, but diagnostics showed the model was not silent.
- Relaxed smoke evaluation produced nonzero matches: `0.0190 / 0.0020 / 0.0540`, with `17 / 48` images having at least one successful prediction.
- A follow-up relaxed smoke evaluation with `--refine_scale` produced a much stronger result: `0.3894 / 0.0371 / 0.5047`, with `48 / 48` images having at least one successful prediction.
- Full 1440-frame evaluation with the same `--refine_scale` protocol produced `0.4751 / 0.0443 / 0.4876`, with `1434 / 1440` images having at least one successful prediction.
- Audit evidence points to real-depth scale mismatch as the main no-refine failure source, not a basic GraspNet intrinsics or depth-factor conversion error.

Consequences:

- T6.4 should be described as real-domain generalization exploration and qualitative/diagnostic evidence.
- Do not use the strict zero result to claim the model cannot grasp real objects.
- Do not compare the GraspNet-real GSR/GCR/OSR directly against primitive-test GSR/GCR/OSR as a main superiority claim; the data source, GT density, and evaluation assumptions differ.
- For GraspNet-real converted evaluation, include `--refine_scale` in the recommended diagnostic protocol.
- For converted mesh/real GraspNet data, do not use primitive GT resampling options such as `--rot_sample_num` or `--trl_sample_num`.

Status:

- active

## 2026-04-27 GraspNet88 Single-Object Synthetic Mesh Evaluation Is Completed

Decision:

- Treat `data/ps_grasp_single_graspnet_t63_eval_88obj` as the completed GraspNet object-level single-object synthetic mesh evaluation set.
- Use all `88` object ids `000..087` and all `440` rendered RGB-D samples as the main result.
- Keep sparse-label objects in the main table rather than removing them.

Why:

- The dataset covers exactly `88` GraspNet object meshes with `5` views per object.
- `train.txt` is empty and `test.txt` covers all scenes, matching the intended eval-only role.
- The dataset passed loader/audit checks and contains no zero-label projected samples.
- Although objects `009`, `040`, and `065` have few non-colliding GT grasps, removing them would bias the full-object-coverage claim.

Consequences:

- The main thesis table can report all-88-object synthetic mesh evaluation.
- Object `065` should be discussed as a difficult sparse-label failure case.
- Do not describe this dataset as a real-camera single-object GraspNet split; it is synthetic rendering from GraspNet meshes and labels.

Status:

- active

## 2026-04-27 KGNv2 + Refine-Scale Is an Inference-Side Improvement

Decision:

- Treat `KGNv2 + Refine-Scale` as a project-level inference-side improvement, not as pure paper-2 original inference and not as a training-side method.
- Report `KGNv2 no-refine` and `KGNv2 + Refine-Scale` separately.

Why:

- Paper-2/KGNv2 core inference uses the separate scale branch to set translation magnitude from predicted scale.
- Current code also has an optional `--refine_scale` path that replaces the translation magnitude with the RGB-D depth at the predicted grasp center.
- On GraspNet88 single-object synthetic mesh eval, `--refine_scale` improves all three threshold settings:
  - strict `1cm + 20deg`: `0.0249 / 0.0065 / 0.2318` -> `0.0614 / 0.0135 / 0.3750`
  - standard `2cm + 30deg`: `0.1685 / 0.0567 / 0.6409` -> `0.2868 / 0.0864 / 0.8136`
  - relaxed `3cm + 45deg`: `0.4338 / 0.2189 / 0.8841` -> `0.5424 / 0.2696 / 0.9364`

Consequences:

- `KGNv2 no-refine` is the paper-2 original-style external-evaluation protocol.
- `KGNv2 + Refine-Scale` is a valid inference-side RGB-D scale refinement improvement for this thesis project.
- Qualitative two-finger gripper visualizations should label whether they are no-refine or Refine-Scale.

Status:

- active
