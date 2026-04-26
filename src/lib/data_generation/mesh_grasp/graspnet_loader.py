from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class GraspNetGraspData:
    object_id: str
    label_path: str
    mesh_path: str
    grasp_poses: np.ndarray
    grasp_widths: np.ndarray
    valid_count: int
    total_count: int
    meta: dict


def _choose_mesh_path(model_dir, mesh_name=None):
    candidates = []
    if mesh_name:
        candidates.append(mesh_name)
    candidates.extend(
        [
            "nontextured_simplified.ply",
            "nontextured.ply",
            "textured.obj",
        ]
    )
    for name in candidates:
        path = model_dir / name
        if path.exists():
            return path
    return model_dir / (mesh_name or "nontextured_simplified.ply")


def scan_graspnet_object_ids(raw_root, object_ids=None, max_objects=-1):
    raw_root = Path(raw_root).expanduser().resolve()
    if object_ids:
        ids = ["{:03d}".format(int(obj_id)) for obj_id in object_ids]
    else:
        model_ids = {
            path.name
            for path in (raw_root / "models").glob("*")
            if path.is_dir() and path.name.isdigit()
        }
        label_ids = {
            path.name.split("_")[0]
            for path in (raw_root / "grasp_label").glob("*_labels.npz")
        }
        ids = sorted(model_ids & label_ids)

    if max_objects is not None and int(max_objects) > 0:
        ids = ids[: int(max_objects)]
    return ids


def generate_views(num_views=300):
    """Generate the canonical GraspNet view directions."""
    phi = (np.sqrt(5.0) - 1.0) / 2.0
    views = []
    for i in range(num_views):
        z = (2.0 * i + 1.0) / num_views - 1.0
        radius = np.sqrt(max(0.0, 1.0 - z * z))
        x = radius * np.cos(2.0 * np.pi * i * phi)
        y = radius * np.sin(2.0 * np.pi * i * phi)
        views.append([x, y, z])
    return np.asarray(views, dtype=np.float64)


def batch_viewpoint_params_to_matrix(batch_towards, batch_angle):
    """Convert GraspNet viewpoint/angle parameters to rotation matrices.

    This follows the public GraspNetAPI convention: the gripper local x axis
    points along the approach direction, and the in-plane angle rotates around
    that axis.
    """
    axis_x = np.asarray(batch_towards, dtype=np.float64)
    axis_x = axis_x / np.linalg.norm(axis_x, axis=1, keepdims=True).clip(1e-8)

    axis_y = np.stack(
        [-axis_x[:, 1], axis_x[:, 0], np.zeros(axis_x.shape[0])], axis=1
    )
    zero_mask = np.linalg.norm(axis_y, axis=1) < 1e-8
    if np.any(zero_mask):
        axis_y[zero_mask] = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    axis_y = axis_y / np.linalg.norm(axis_y, axis=1, keepdims=True).clip(1e-8)
    axis_z = np.cross(axis_x, axis_y)

    rot_view = np.stack([axis_x, axis_y, axis_z], axis=2)

    cos = np.cos(batch_angle)
    sin = np.sin(batch_angle)
    rot_angle = np.zeros((axis_x.shape[0], 3, 3), dtype=np.float64)
    rot_angle[:, 0, 0] = 1.0
    rot_angle[:, 1, 1] = cos
    rot_angle[:, 1, 2] = -sin
    rot_angle[:, 2, 1] = sin
    rot_angle[:, 2, 2] = cos
    return np.matmul(rot_view, rot_angle)


def graspnet_to_kgn_transform():
    """Return T_GK, mapping KGN gripper-frame points into GraspNet frame.

    GraspNet represents the gripper opening along local y and height along
    local z. The KGN data-generation gripper opens along local z and uses local
    y as the height axis. Both use local x as the approach/backbone direction.
    """
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, -1.0, 0.0],
        ],
        dtype=np.float64,
    )
    return transform


def load_graspnet_grasp_file(
    raw_root,
    object_id,
    mesh_name=None,
    max_grasps=300,
    min_grasps=20,
    width_range=(0.01, 0.085),
    score_max=0.4,
    seed=None,
    convert_to_kgn_frame=True,
    use_collision=True,
):
    """Load one GraspNet object label and return KGN-compatible grasps.

    Returned poses are object-frame homogeneous transforms. The scene generator
    later multiplies them by the sampled object pose, as with primitive grasps.
    """
    raw_root = Path(raw_root).expanduser().resolve()
    object_id = "{:03d}".format(int(object_id))
    model_dir = raw_root / "models" / object_id
    label_path = raw_root / "grasp_label" / "{}_labels.npz".format(object_id)
    mesh_path = _choose_mesh_path(model_dir, mesh_name)

    if not mesh_path.exists():
        raise FileNotFoundError("Missing GraspNet mesh: {}".format(mesh_path))
    if not label_path.exists():
        raise FileNotFoundError("Missing GraspNet label: {}".format(label_path))

    with np.load(label_path) as label:
        points = np.asarray(label["points"], dtype=np.float64)
        offsets = np.asarray(label["offsets"], dtype=np.float64)
        scores = np.asarray(label["scores"], dtype=np.float64)
        collision = label["collision"].astype(bool) if "collision" in label.files else None

    widths = offsets[..., 2]
    width_min, width_max = width_range
    valid_mask = (scores > 0.0) & (scores <= float(score_max))
    valid_mask &= (widths >= float(width_min)) & (widths <= float(width_max))
    if collision is not None and use_collision:
        valid_mask &= ~collision

    valid_indices = np.argwhere(valid_mask)
    valid_count = int(valid_indices.shape[0])
    if valid_count < int(min_grasps):
        raise ValueError(
            "Only {} valid grasps for object {}, fewer than min_grasps={}".format(
                valid_count, object_id, min_grasps
            )
        )

    if max_grasps is not None and int(max_grasps) > 0 and valid_count > int(max_grasps):
        rng = np.random.RandomState(seed)
        selected = rng.choice(valid_count, size=int(max_grasps), replace=False)
        valid_indices = valid_indices[selected]

    point_ids = valid_indices[:, 0]
    view_ids = valid_indices[:, 1]
    angle_ids = valid_indices[:, 2]
    depth_ids = valid_indices[:, 3]

    views = generate_views(offsets.shape[1])
    grasp_views = views[view_ids]
    grasp_angles = offsets[point_ids, view_ids, angle_ids, depth_ids, 0]
    grasp_widths = offsets[point_ids, view_ids, angle_ids, depth_ids, 2]
    rotations = batch_viewpoint_params_to_matrix(-grasp_views, grasp_angles)

    poses = np.tile(np.eye(4, dtype=np.float64), (valid_indices.shape[0], 1, 1))
    poses[:, :3, :3] = rotations
    poses[:, :3, 3] = points[point_ids]
    if convert_to_kgn_frame:
        poses = poses @ graspnet_to_kgn_transform()

    total_count = int(np.prod(scores.shape))
    meta = {
        "source": "graspnet",
        "object_id": object_id,
        "label_path": str(label_path),
        "mesh_path": str(mesh_path),
        "mesh_name": mesh_path.name,
        "total_count": total_count,
        "valid_count": valid_count,
        "kept_grasps": int(poses.shape[0]),
        "width_range": [float(width_min), float(width_max)],
        "score_range": [0.0, float(score_max)],
        "use_collision": bool(use_collision),
        "has_collision": collision is not None,
        "convert_to_kgn_frame": bool(convert_to_kgn_frame),
        "frame_note": "GraspNet label pose converted to KGN gripper frame.",
    }

    return GraspNetGraspData(
        object_id=object_id,
        label_path=str(label_path),
        mesh_path=str(mesh_path),
        grasp_poses=poses.astype(np.float64),
        grasp_widths=grasp_widths.astype(np.float64),
        valid_count=valid_count,
        total_count=total_count,
        meta=meta,
    )
