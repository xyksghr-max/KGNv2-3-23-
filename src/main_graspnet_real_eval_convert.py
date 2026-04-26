import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import trimesh
from scipy.io import loadmat

import _init_paths  # noqa: F401

from data_generation.grasp.grasp import Grasp
from data_generation.mesh_grasp.graspnet_loader import load_graspnet_grasp_file
from utils.keypoints import kpts_3d_to_2d
from utils.file import write_numList_to_file


def _scene_split(scene_id):
    if 100 <= scene_id <= 129:
        return "seen"
    if 130 <= scene_id <= 159:
        return "similar"
    if 160 <= scene_id <= 189:
        return "novel"
    if 0 <= scene_id <= 99:
        return "train"
    return "unknown"


def _parse_scene_ids(values):
    if not values:
        return None
    scene_ids = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            if "-" in item:
                start, end = item.split("-", 1)
                scene_ids.extend(range(int(start), int(end) + 1))
            else:
                scene_ids.append(int(item))
    return sorted(set(scene_ids))


def _view_ids(camera_dir, requested=None):
    available = sorted(path.stem for path in (camera_dir / "rgb").glob("*.png"))
    if not requested:
        return available
    requested_set = set()
    for value in requested:
        for item in value.split(","):
            item = item.strip()
            if item:
                requested_set.add("{:04d}".format(int(item)))
    return [view_id for view_id in available if view_id in requested_set]


def _make_scene_dirs(out_scene):
    (out_scene / "color_images").mkdir(parents=True, exist_ok=True)
    (out_scene / "depth_raw").mkdir(parents=True, exist_ok=True)
    (out_scene / "depth_img").mkdir(parents=True, exist_ok=True)
    (out_scene / "seg_labels").mkdir(parents=True, exist_ok=True)


def _load_mesh_extent(raw_root, object_id):
    mesh_path = raw_root / "models" / "{:03d}".format(object_id) / "nontextured_simplified.ply"
    if not mesh_path.exists():
        mesh_path = raw_root / "models" / "{:03d}".format(object_id) / "nontextured.ply"
    if not mesh_path.exists():
        return [], ""
    mesh = trimesh.load(str(mesh_path), force="mesh", process=False)
    return mesh.extents.astype(float).tolist(), str(mesh_path)


def _load_object_grasps(raw_root, object_id, args, cache):
    key = (int(object_id), int(args.max_grasps_per_object))
    if key not in cache:
        cache[key] = load_graspnet_grasp_file(
            raw_root=raw_root,
            object_id=object_id,
            mesh_name=args.mesh_name,
            max_grasps=args.max_grasps_per_object,
            min_grasps=args.min_grasps_per_object,
            width_range=(args.width_min, args.width_max),
            score_max=args.score_max,
            seed=args.seed + int(object_id),
            convert_to_kgn_frame=True,
            use_collision=True,
        )
    return cache[key]


def _transform_grasps(obj_pose_cam, grasp_data):
    poses = np.asarray(grasp_data.grasp_poses, dtype=np.float64)
    return np.matmul(obj_pose_cam[None, :, :], poses)


def _filter_grasps_by_projection(grasps_cam, widths, intrinsic, image_shape, args):
    if not args.filter_projected_centers and not args.filter_projected_keypoints:
        return grasps_cam, widths

    h, w = image_shape[:2]
    keep = []
    for idx, pose in enumerate(grasps_cam):
        center = pose[:3, 3]
        if center[2] <= 1e-6:
            continue
        u = intrinsic[0, 0] * center[0] / center[2] + intrinsic[0, 2]
        v = intrinsic[1, 1] * center[1] / center[2] + intrinsic[1, 2]
        if args.filter_projected_centers:
            if not (0 <= u < w and 0 <= v < h):
                continue
        if args.filter_projected_keypoints:
            grasp = Grasp(widths[idx], pose=pose, kpts_option="box")
            kpts = grasp.get_kpts(frame="world")
            kpts_2d = kpts_3d_to_2d(intrinsic, np.eye(4), kpts)
            inside = (
                (kpts_2d[:, 0] >= 0)
                & (kpts_2d[:, 0] < w)
                & (kpts_2d[:, 1] >= 0)
                & (kpts_2d[:, 1] < h)
            )
            if np.count_nonzero(inside) < args.min_projected_keypoints:
                continue
        keep.append(idx)

    if not keep:
        return np.zeros((0, 4, 4), dtype=np.float64), np.zeros((0,), dtype=np.float64)
    keep = np.asarray(keep, dtype=np.int64)
    return grasps_cam[keep], widths[keep]


def _save_frame_as_ps_scene(
    out_scene,
    camera_dir,
    view_id,
    intrinsic,
    obj_infos,
    args,
):
    _make_scene_dirs(out_scene)
    rgb_path = camera_dir / "rgb" / f"{view_id}.png"
    depth_path = camera_dir / "depth" / f"{view_id}.png"
    label_path = camera_dir / "label" / f"{view_id}.png"

    image = cv2.imread(str(rgb_path), cv2.IMREAD_COLOR)
    depth_raw = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
    label = cv2.imread(str(label_path), cv2.IMREAD_UNCHANGED)
    if image is None or depth_raw is None or label is None:
        raise FileNotFoundError(f"Missing image/depth/label for {rgb_path}")

    shutil.copyfile(rgb_path, out_scene / "color_images" / "color_image_0.png")
    depth_m = depth_raw.astype(np.float32) / float(args.depth_factor)
    np.save(out_scene / "depth_raw" / "depth_raw_0.npy", depth_m)
    depth_img = np.round(depth_m * 10000).astype(np.uint16)
    cv2.imwrite(str(out_scene / "depth_img" / "depth_image_0.png"), depth_img)
    label_u8 = np.clip(label, 0, 255).astype(np.uint8)
    cv2.imwrite(
        str(out_scene / "seg_labels" / "segmask_label_0.jpg"),
        label_u8,
        [int(cv2.IMWRITE_JPEG_QUALITY), 100],
    )

    scene_info = {
        "intrinsic": intrinsic.astype(float).tolist(),
        "camera_poses": np.eye(4, dtype=np.float64)[None, :, :].tolist(),
        "grasp_poses": [obj["grasp_poses"].tolist() for obj in obj_infos],
        "grasp_widths": [obj["grasp_widths"].tolist() for obj in obj_infos],
        "grasp_collision": [
            np.zeros((obj["grasp_widths"].shape[0],), dtype=bool).tolist()
            for obj in obj_infos
        ],
        "obj_types": ["mesh" for _ in obj_infos],
        "obj_dims": [obj["obj_dims"] for obj in obj_infos],
        "obj_poses": [obj["obj_pose"].tolist() for obj in obj_infos],
        "mesh_meta": [obj["mesh_meta"] for obj in obj_infos],
        "real_rgbd_meta": {
            "source": "graspnet_real_rgbd",
            "camera": args.camera,
            "original_scene": obj_infos[0]["original_scene"] if obj_infos else None,
            "original_view": view_id,
            "frame_convention": "PS world frame is set equal to this RealSense camera frame.",
        },
    }
    with open(out_scene / "scene_info.json", "w") as f:
        json.dump(scene_info, f)


def _convert_one_view(scene_dir, camera_dir, view_id, raw_root, args, cache):
    meta_path = camera_dir / "meta" / f"{view_id}.mat"
    label_path = camera_dir / "label" / f"{view_id}.png"
    image_path = camera_dir / "rgb" / f"{view_id}.png"
    meta = loadmat(meta_path)
    intrinsic = np.asarray(meta.get("intrinsic_matrix", np.load(camera_dir / "camK.npy")), dtype=np.float64)
    cls_indexes = np.asarray(meta["cls_indexes"]).reshape(-1).astype(int)
    poses = np.asarray(meta["poses"], dtype=np.float64)
    label = cv2.imread(str(label_path), cv2.IMREAD_UNCHANGED)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if label is None or image is None:
        raise FileNotFoundError(f"Missing label or rgb for {scene_dir.name}/{view_id}")
    visible_labels = set(int(v) for v in np.unique(label) if int(v) > 0)
    obj_infos = []

    for obj_idx, cls_id in enumerate(cls_indexes):
        cls_id = int(cls_id)
        object_id = cls_id - 1
        if cls_id not in visible_labels:
            continue
        visible_pixels = int(np.count_nonzero(label == cls_id))
        if visible_pixels < args.min_visible_pixels:
            continue
        try:
            grasp_data = _load_object_grasps(raw_root, object_id, args, cache)
        except Exception as exc:
            if args.verbose:
                print(f"Skip object {object_id:03d}: {exc}")
            continue

        obj_pose = np.eye(4, dtype=np.float64)
        obj_pose[:3, :4] = poses[:, :, obj_idx]
        grasp_poses = _transform_grasps(obj_pose, grasp_data)
        widths = np.asarray(grasp_data.grasp_widths, dtype=np.float64)
        grasp_poses, widths = _filter_grasps_by_projection(
            grasp_poses, widths, intrinsic, image.shape, args
        )
        if widths.size < args.min_kept_grasps_per_object:
            continue
        dims, mesh_path = _load_mesh_extent(raw_root, object_id)
        obj_infos.append(
            {
                "obj_pose": obj_pose,
                "obj_dims": dims,
                "grasp_poses": grasp_poses,
                "grasp_widths": widths,
                "mesh_meta": {
                    "source": "graspnet_real_rgbd",
                    "object_id": "{:03d}".format(object_id),
                    "cls_index": cls_id,
                    "visible_pixels": visible_pixels,
                    "mesh_path": mesh_path,
                    "label_path": grasp_data.label_path,
                    "original_scene": scene_dir.name,
                    "original_view": view_id,
                    "split": _scene_split(int(scene_dir.name.split("_")[1])),
                },
                "original_scene": scene_dir.name,
            }
        )

    if len(obj_infos) < args.min_objects_per_frame:
        raise ValueError(
            f"{scene_dir.name}/{view_id} has {len(obj_infos)} usable objects, "
            f"need {args.min_objects_per_frame}"
        )
    return intrinsic, obj_infos


def convert(args):
    subset_root = Path(args.subset_root).expanduser().resolve()
    raw_root = Path(args.graspnet_raw_root).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    if out_dir.exists() and not args.overwrite:
        raise FileExistsError(f"{out_dir} exists. Use --overwrite to replace it.")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    requested_scene_ids = _parse_scene_ids(args.scenes)
    scene_dirs = sorted(
        [path for path in subset_root.glob("scene_*") if path.is_dir()],
        key=lambda path: int(path.name.split("_")[1]),
    )
    if requested_scene_ids is not None:
        requested = set(requested_scene_ids)
        scene_dirs = [
            path for path in scene_dirs if int(path.name.split("_")[1]) in requested
        ]

    cache = {}
    converted = []
    skipped = []
    scene_idx = 0
    for scene_dir in scene_dirs:
        camera_dir = scene_dir / args.camera
        if not camera_dir.exists():
            skipped.append({"scene": scene_dir.name, "reason": "missing_camera"})
            continue
        for view_id in _view_ids(camera_dir, requested=args.views):
            if args.max_frames > 0 and scene_idx >= args.max_frames:
                break
            try:
                intrinsic, obj_infos = _convert_one_view(
                    scene_dir, camera_dir, view_id, raw_root, args, cache
                )
                _save_frame_as_ps_scene(
                    out_dir / str(scene_idx),
                    camera_dir,
                    view_id,
                    intrinsic,
                    obj_infos,
                    args,
                )
                converted.append(
                    {
                        "ps_scene": scene_idx,
                        "original_scene": scene_dir.name,
                        "original_view": view_id,
                        "split": _scene_split(int(scene_dir.name.split("_")[1])),
                        "objects": len(obj_infos),
                        "grasps": int(sum(obj["grasp_widths"].size for obj in obj_infos)),
                    }
                )
                scene_idx += 1
            except Exception as exc:
                skipped.append(
                    {
                        "scene": scene_dir.name,
                        "view": view_id,
                        "reason": str(exc),
                    }
                )
                if args.verbose:
                    print(f"Skip {scene_dir.name}/{view_id}: {exc}")
        if args.max_frames > 0 and scene_idx >= args.max_frames:
            break

    write_numList_to_file(str(out_dir / "train.txt"), [])
    write_numList_to_file(str(out_dir / "test.txt"), list(range(scene_idx)))
    summary = {
        "source_subset": str(subset_root),
        "graspnet_raw_root": str(raw_root),
        "out_dir": str(out_dir),
        "converted_frames": len(converted),
        "skipped_frames": len(skipped),
        "splits": {},
        "converted": converted,
        "skipped": skipped[:200],
        "notes": [
            "Each PS scene corresponds to one real GraspNet RGB-D frame.",
            "PS world frame is set equal to that frame's RealSense camera frame.",
            "Grasp labels come from GraspNet object-level labels transformed by meta poses.",
        ],
    }
    for row in converted:
        summary["splits"][row["split"]] = summary["splits"].get(row["split"], 0) + 1
    with open(out_dir / "conversion_summary.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    print(json.dumps({k: v for k, v in summary.items() if k not in ["converted", "skipped"]}, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset_root", required=True)
    parser.add_argument("--graspnet_raw_root", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--camera", default="realsense")
    parser.add_argument("--scenes", nargs="*", default=[])
    parser.add_argument("--views", nargs="*", default=[])
    parser.add_argument("--max_frames", type=int, default=-1)
    parser.add_argument("--max_grasps_per_object", type=int, default=120)
    parser.add_argument("--min_grasps_per_object", type=int, default=20)
    parser.add_argument("--min_kept_grasps_per_object", type=int, default=5)
    parser.add_argument("--min_objects_per_frame", type=int, default=1)
    parser.add_argument("--min_visible_pixels", type=int, default=100)
    parser.add_argument("--width_min", type=float, default=0.01)
    parser.add_argument("--width_max", type=float, default=0.085)
    parser.add_argument("--score_max", type=float, default=0.4)
    parser.add_argument("--mesh_name", default="nontextured_simplified.ply")
    parser.add_argument("--depth_factor", type=float, default=1000.0)
    parser.add_argument("--seed", type=int, default=317)
    parser.add_argument("--filter_projected_centers", action="store_true")
    parser.add_argument("--filter_projected_keypoints", action="store_true")
    parser.add_argument("--min_projected_keypoints", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    convert(parser.parse_args())
