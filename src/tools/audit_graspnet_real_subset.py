import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.io import loadmat

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import _init_paths  # noqa: F401


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


def _read_object_ids(scene_dir):
    path = scene_dir / "object_id_list.txt"
    if not path.exists():
        return []
    with open(path, "r") as f:
        return [int(line.strip()) for line in f if line.strip()]


def _view_ids(camera_dir):
    rgb_dir = camera_dir / "rgb"
    return sorted(path.stem for path in rgb_dir.glob("*.png"))


def audit_subset(args):
    subset_root = Path(args.subset_root).expanduser().resolve()
    raw_root = Path(args.graspnet_raw_root).expanduser().resolve()
    if not subset_root.exists():
        raise FileNotFoundError(subset_root)

    scene_dirs = sorted(
        [path for path in subset_root.glob("scene_*") if path.is_dir()],
        key=lambda path: int(path.name.split("_")[1]),
    )
    stats = {
        "subset_root": str(subset_root),
        "scene_count": len(scene_dirs),
        "view_count": 0,
        "split_counts": {},
        "missing_camera_dir": 0,
        "missing_core_files": 0,
        "missing_view_files": 0,
        "bad_meta": 0,
        "objects_total": 0,
        "objects_visible": 0,
        "objects_with_mesh": 0,
        "objects_with_grasp_label": 0,
        "object_ids": {},
        "image_shapes": {},
        "intrinsic_shapes": {},
        "depth_min_max_m": [None, None],
    }

    for scene_dir in scene_dirs:
        scene_id = int(scene_dir.name.split("_")[1])
        split = _scene_split(scene_id)
        stats["split_counts"][split] = stats["split_counts"].get(split, 0) + 1

        camera_dir = scene_dir / args.camera
        if not camera_dir.exists():
            stats["missing_camera_dir"] += 1
            continue

        core_files = [
            scene_dir / "object_id_list.txt",
            camera_dir / "camK.npy",
            camera_dir / "camera_poses.npy",
            camera_dir / "cam0_wrt_table.npy",
        ]
        if any(not path.exists() for path in core_files):
            stats["missing_core_files"] += 1
            continue

        object_ids = _read_object_ids(scene_dir)
        for obj_id in object_ids:
            key = "{:03d}".format(obj_id)
            stats["object_ids"][key] = stats["object_ids"].get(key, 0) + 1
            stats["objects_total"] += 1
            if (raw_root / "models" / key).exists():
                stats["objects_with_mesh"] += 1
            if (raw_root / "grasp_label" / f"{key}_labels.npz").exists():
                stats["objects_with_grasp_label"] += 1

        cam_k = np.load(camera_dir / "camK.npy")
        stats["intrinsic_shapes"][str(tuple(cam_k.shape))] = (
            stats["intrinsic_shapes"].get(str(tuple(cam_k.shape)), 0) + 1
        )

        for view_id in _view_ids(camera_dir):
            stats["view_count"] += 1
            files = {
                "rgb": camera_dir / "rgb" / f"{view_id}.png",
                "depth": camera_dir / "depth" / f"{view_id}.png",
                "label": camera_dir / "label" / f"{view_id}.png",
                "meta": camera_dir / "meta" / f"{view_id}.mat",
                "annotation": camera_dir / "annotations" / f"{view_id}.xml",
            }
            if any(not path.exists() for path in files.values()):
                stats["missing_view_files"] += 1
                continue

            rgb = cv2.imread(str(files["rgb"]), cv2.IMREAD_COLOR)
            depth = cv2.imread(str(files["depth"]), cv2.IMREAD_UNCHANGED)
            label = cv2.imread(str(files["label"]), cv2.IMREAD_UNCHANGED)
            if rgb is not None:
                shape = str(tuple(rgb.shape[:2]))
                stats["image_shapes"][shape] = stats["image_shapes"].get(shape, 0) + 1
            if depth is not None:
                depth_m = depth.astype(np.float64) / float(args.depth_factor)
                d_min = float(np.min(depth_m))
                d_max = float(np.max(depth_m))
                stats["depth_min_max_m"][0] = (
                    d_min
                    if stats["depth_min_max_m"][0] is None
                    else min(stats["depth_min_max_m"][0], d_min)
                )
                stats["depth_min_max_m"][1] = (
                    d_max
                    if stats["depth_min_max_m"][1] is None
                    else max(stats["depth_min_max_m"][1], d_max)
                )
            try:
                meta = loadmat(files["meta"])
                cls_indexes = np.asarray(meta["cls_indexes"]).reshape(-1)
                poses = np.asarray(meta["poses"])
                if poses.shape[:2] != (3, 4) or poses.shape[2] != cls_indexes.size:
                    stats["bad_meta"] += 1
                if label is not None:
                    visible_labels = set(int(v) for v in np.unique(label) if int(v) > 0)
                    stats["objects_visible"] += sum(
                        1 for cls_id in cls_indexes if int(cls_id) in visible_labels
                    )
            except Exception:
                stats["bad_meta"] += 1

    print(json.dumps(stats, indent=2, sort_keys=True))
    if args.out_json:
        out_path = Path(args.out_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(stats, f, indent=2, sort_keys=True)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset_root", required=True)
    parser.add_argument(
        "--graspnet_raw_root",
        default="../data/external/graspnet/raw",
        help="Directory containing GraspNet models/ and grasp_label/.",
    )
    parser.add_argument("--camera", default="realsense")
    parser.add_argument("--depth_factor", type=float, default=1000.0)
    parser.add_argument("--out_json", default="")
    audit_subset(parser.parse_args())
