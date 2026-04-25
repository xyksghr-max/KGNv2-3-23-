# Current Task

Last updated: 2026-04-25

## Task

Implement `T6.2 ACRONYM mesh-labeled dataset pilot`.

## Goal

Build a mesh-labeled dataset pilot in `KGN-main` after closing the T3.5b inference-side branch. T6 no longer continues network/loss/post-process tuning. T6.2 tests whether external mesh objects with existing 6D grasp labels can be converted into the current PS dataset format and read by the existing KGN training pipeline.

## Branch Context

- Current branch: `feat/t6-aigc-mesh-dataset-pilot`
- Branch base: closed `feat/t3.5b-inference-side-enhancement @ 97f9b22`
- Branch role: data-generation / dataset-loader pilot branch

Known untracked local files remain user/local files and must not be deleted or submitted:

- `KGNv2-Sim PROJECT_PROGRESS.md`
- `T3.5b计划.md`
- `implementation_plan.md`
- `src/lib/third_party/__init__.py`
- `新对话提示词包.md`

## In Scope

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
