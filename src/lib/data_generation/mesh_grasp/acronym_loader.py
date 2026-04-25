import os
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np


@dataclass
class AcronymGraspData:
    grasp_path: str
    mesh_path: str
    mesh_file: str
    mesh_scale: float
    category: str
    object_id: str
    grasp_poses: np.ndarray
    grasp_widths: np.ndarray
    success_count: int
    total_count: int
    meta: dict


def _decode_h5_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "decode"):
        return value.decode("utf-8")
    return value


def _as_bool_success(success_data):
    success = np.asarray(success_data)
    if success.dtype == np.bool_:
        return success
    return success.astype(np.float32) > 0.5


def _infer_category_object_id(grasp_path):
    stem = Path(grasp_path).stem
    parts = stem.split("_")
    category = parts[0] if parts else "mesh"
    object_id = parts[1] if len(parts) > 1 else stem
    return category, object_id


def _resolve_mesh_path(mesh_root, mesh_file):
    mesh_root = Path(mesh_root)
    mesh_file_path = Path(mesh_file)
    if mesh_file_path.is_absolute():
        return str(mesh_file_path)
    return str((mesh_root / mesh_file_path).resolve())


def acronym_to_kgn_transform(gripper_depth=0.11217):
    """Return T_AK, mapping KGN gripper-frame points into ACRONYM frame.

    ACRONYM visualizes the gripper opening along x and fingers extending along
    +z. The local KGN gripper opens along z and approaches along +x. This
    best-effort fixed transform puts the KGN fingertip midpoint at the ACRONYM
    fingertip midpoint and aligns the opening/approach axes.
    """
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    transform[:3, 3] = np.array([0.0, 0.0, float(gripper_depth)], dtype=np.float64)
    return transform


def _load_widths(handle, count):
    if "gripper/configuration" not in handle:
        return np.full((count,), 0.08, dtype=np.float64)

    config = np.asarray(handle["gripper/configuration"])
    if config.size == 0:
        width = 0.08
    else:
        # ACRONYM panda examples store one finger joint value around 0.04m.
        width = float(np.ravel(config)[0]) * 2.0
    return np.full((count,), width, dtype=np.float64)


def load_acronym_grasp_file(
    grasp_path,
    mesh_root,
    max_grasps=300,
    min_grasps=1,
    width_range=(0.01, 0.085),
    gripper_depth=0.11217,
    seed=None,
    convert_to_kgn_frame=True,
):
    """Load one ACRONYM grasp h5 and return KGN-compatible grasp poses.

    The returned grasp poses are in the object frame and can be written into
    PS-style scene annotations after multiplying by the sampled object pose.
    """
    grasp_path = str(Path(grasp_path).resolve())
    with h5py.File(grasp_path, "r") as handle:
        transforms = np.asarray(handle["grasps/transforms"], dtype=np.float64)
        success = _as_bool_success(handle["grasps/qualities/flex/object_in_gripper"])
        mesh_file = _decode_h5_value(handle["object/file"][()])
        mesh_scale = float(handle["object/scale"][()])
        widths = _load_widths(handle, transforms.shape[0])

    width_min, width_max = width_range
    keep_mask = success & (widths >= width_min) & (widths <= width_max)
    keep_idx = np.nonzero(keep_mask)[0]
    if keep_idx.size < min_grasps:
        raise ValueError(
            "Only {} valid grasps in {}, fewer than min_grasps={}".format(
                keep_idx.size, grasp_path, min_grasps
            )
        )

    if max_grasps is not None and max_grasps > 0 and keep_idx.size > max_grasps:
        rng = np.random.RandomState(seed)
        keep_idx = rng.choice(keep_idx, size=max_grasps, replace=False)

    grasp_poses = transforms[keep_idx].copy()
    if convert_to_kgn_frame:
        grasp_poses = grasp_poses @ acronym_to_kgn_transform(gripper_depth)
    grasp_widths = widths[keep_idx].astype(np.float64)

    category, object_id = _infer_category_object_id(grasp_path)
    mesh_path = _resolve_mesh_path(mesh_root, mesh_file)
    meta = {
        "source": "acronym",
        "grasp_path": grasp_path,
        "mesh_file": mesh_file,
        "mesh_path": mesh_path,
        "mesh_scale": mesh_scale,
        "category": category,
        "object_id": object_id,
        "success_count": int(np.count_nonzero(success)),
        "total_count": int(transforms.shape[0]),
        "kept_grasps": int(grasp_poses.shape[0]),
        "width_range": [float(width_min), float(width_max)],
        "gripper_depth": float(gripper_depth),
        "convert_to_kgn_frame": bool(convert_to_kgn_frame),
    }

    return AcronymGraspData(
        grasp_path=grasp_path,
        mesh_path=mesh_path,
        mesh_file=mesh_file,
        mesh_scale=mesh_scale,
        category=category,
        object_id=object_id,
        grasp_poses=grasp_poses,
        grasp_widths=grasp_widths,
        success_count=int(np.count_nonzero(success)),
        total_count=int(transforms.shape[0]),
        meta=meta,
    )


def scan_acronym_grasp_files(grasp_root, categories=None):
    grasp_root = Path(grasp_root)
    categories = set(categories or [])
    paths = sorted(grasp_root.rglob("*.h5"))
    if not categories:
        return [str(path) for path in paths]

    filtered = []
    for path in paths:
        category, _ = _infer_category_object_id(path)
        if category in categories:
            filtered.append(str(path))
    return filtered

