import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import _init_paths

from data_generation.grasp.grasp import Grasp
from utils.keypoints import kpts_3d_to_2d


def _read_split(path):
    if not path.exists():
        return []
    with open(path, "r") as f:
        return [int(line.strip()) for line in f if line.strip()]


def _load_info(scene_dir):
    with open(scene_dir / "scene_info.json", "r") as f:
        return json.load(f)


def _count_files(scene_dir):
    return {
        "color": len(list((scene_dir / "color_images").glob("*.png"))),
        "depth": len(list((scene_dir / "depth_raw").glob("*.npy"))),
        "seg": len(list((scene_dir / "seg_labels").glob("*.jpg"))),
    }


def _check_projection(info, image_shape, max_grasps_per_obj=20):
    h, w = image_shape[:2]
    intrinsic = np.asarray(info["intrinsic"])
    camera_poses = np.asarray(info["camera_poses"])
    total = 0
    inside = 0
    for cam_pose in camera_poses:
        for obj_poses, widths, collisions in zip(
            info["grasp_poses"], info["grasp_widths"], info["grasp_collision"]
        ):
            obj_poses = np.asarray(obj_poses)
            widths = np.asarray(widths)
            collisions = np.asarray(collisions)
            valid_idx = np.nonzero(~collisions.astype(bool))[0]
            for grasp_idx in valid_idx[:max_grasps_per_obj]:
                grasp = Grasp(widths[grasp_idx], pose=obj_poses[grasp_idx], kpts_option="box")
                kpts_3d = grasp.get_kpts(frame="world")
                kpts_2d = kpts_3d_to_2d(intrinsic, np.linalg.inv(cam_pose), kpts_3d)
                total += kpts_2d.shape[0]
                inside += int(
                    np.sum(
                        (kpts_2d[:, 0] >= 0)
                        & (kpts_2d[:, 0] < w)
                        & (kpts_2d[:, 1] >= 0)
                        & (kpts_2d[:, 1] < h)
                    )
                )
    return inside, total


def _draw_sample_vis(data_dir, scene_idx, sample_vis_dir):
    scene_dir = data_dir / str(scene_idx)
    info = _load_info(scene_dir)
    intrinsic = np.asarray(info["intrinsic"])
    camera_poses = np.asarray(info["camera_poses"])
    sample_vis_dir.mkdir(parents=True, exist_ok=True)

    for cam_idx, cam_pose in enumerate(camera_poses):
        img_path = scene_dir / "color_images" / "color_image_{}.png".format(cam_idx)
        image = cv2.imread(str(img_path))
        if image is None:
            continue
        for obj_poses, widths, collisions in zip(
            info["grasp_poses"], info["grasp_widths"], info["grasp_collision"]
        ):
            obj_poses = np.asarray(obj_poses)
            widths = np.asarray(widths)
            collisions = np.asarray(collisions)
            valid_idx = np.nonzero(~collisions.astype(bool))[0][:20]
            for grasp_idx in valid_idx:
                grasp = Grasp(widths[grasp_idx], pose=obj_poses[grasp_idx], kpts_option="box")
                kpts_3d = grasp.get_kpts(frame="world")
                kpts_2d = kpts_3d_to_2d(intrinsic, np.linalg.inv(cam_pose), kpts_3d)
                for x, y in kpts_2d:
                    cv2.circle(image, (int(round(x)), int(round(y))), 2, (0, 0, 255), -1)
        out_path = sample_vis_dir / "scene{}_cam{}.png".format(scene_idx, cam_idx)
        cv2.imwrite(str(out_path), image)


def audit_dataset(args):
    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.exists():
        raise FileNotFoundError(data_dir)

    scene_dirs = sorted(
        [path for path in data_dir.iterdir() if path.is_dir() and path.name.isdigit()],
        key=lambda path: int(path.name),
    )
    train_ids = _read_split(data_dir / "train.txt")
    test_ids = _read_split(data_dir / "test.txt")

    stats = {
        "scene_count": len(scene_dirs),
        "train_count": len(train_ids),
        "test_count": len(test_ids),
        "missing_scene_info": 0,
        "missing_images": 0,
        "empty_grasp_objects": 0,
        "total_grasps": 0,
        "noncolliding_grasps": 0,
        "width_min": None,
        "width_max": None,
        "obj_types": {},
        "projection_inside": 0,
        "projection_total": 0,
    }

    sample_scene_ids = []
    for scene_dir in scene_dirs:
        info_path = scene_dir / "scene_info.json"
        if not info_path.exists():
            stats["missing_scene_info"] += 1
            continue
        info = _load_info(scene_dir)

        if args.check_images:
            counts = _count_files(scene_dir)
            cam_count = len(info["camera_poses"])
            if counts["color"] != cam_count or counts["depth"] != cam_count or counts["seg"] != cam_count:
                stats["missing_images"] += 1

        for obj_type in info.get("obj_types", []):
            stats["obj_types"][obj_type] = stats["obj_types"].get(obj_type, 0) + 1

        if args.check_grasps:
            for widths, collisions in zip(info["grasp_widths"], info["grasp_collision"]):
                widths = np.asarray(widths, dtype=np.float64)
                collisions = np.asarray(collisions).astype(bool)
                if widths.size == 0:
                    stats["empty_grasp_objects"] += 1
                    continue
                stats["total_grasps"] += int(widths.size)
                stats["noncolliding_grasps"] += int(np.count_nonzero(~collisions))
                w_min = float(np.min(widths))
                w_max = float(np.max(widths))
                stats["width_min"] = w_min if stats["width_min"] is None else min(stats["width_min"], w_min)
                stats["width_max"] = w_max if stats["width_max"] is None else max(stats["width_max"], w_max)

        if args.check_grasps and len(sample_scene_ids) < max(args.sample_vis, 1):
            image_path = scene_dir / "color_images" / "color_image_0.png"
            image = cv2.imread(str(image_path))
            if image is not None:
                inside, total = _check_projection(info, image.shape)
                stats["projection_inside"] += inside
                stats["projection_total"] += total
            sample_scene_ids.append(int(scene_dir.name))

    if args.sample_vis > 0:
        sample_vis_dir = data_dir / "audit_vis"
        for scene_idx in sample_scene_ids[: args.sample_vis]:
            _draw_sample_vis(data_dir, scene_idx, sample_vis_dir)
        stats["sample_vis_dir"] = str(sample_vis_dir)

    print(json.dumps(stats, indent=2, sort_keys=True))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--check_images", action="store_true")
    parser.add_argument("--check_grasps", action="store_true")
    parser.add_argument("--sample_vis", type=int, default=0)
    audit_dataset(parser.parse_args())
