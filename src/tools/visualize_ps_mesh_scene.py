import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import pyrender
import trimesh

src_dir = Path(__file__).resolve().parents[1]
lib_dir = src_dir / "lib"
for path in [src_dir, lib_dir]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from data_generation import Grasp


def _load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def _as_mesh(mesh):
    if isinstance(mesh, trimesh.Scene):
        return trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def _set_color(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual.face_colors = np.asarray(rgba, dtype=np.uint8)
    return mesh


def _load_object_mesh(mesh_meta, obj_pose):
    mesh_path = Path(mesh_meta["mesh_path"])
    mesh = _as_mesh(trimesh.load(mesh_path, force="mesh"))
    mesh = mesh.copy()
    mesh.apply_scale(float(mesh_meta.get("mesh_scale", 1.0)))
    mesh.apply_transform(np.asarray(obj_pose, dtype=np.float64))
    return _set_color(mesh, [80, 190, 170, 255])


def _line_mesh(p0, p1, radius=0.0015, color=(20, 20, 20, 255)):
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    if np.linalg.norm(p1 - p0) < 1e-8:
        return None
    mesh = trimesh.creation.cylinder(radius=radius, sections=8, segment=[p0, p1])
    mesh.visual.face_colors = np.asarray(color, dtype=np.uint8)
    return mesh


def _camera_marker_meshes(camera_pose, intrinsic, image_size=(640, 480), depth=0.09):
    width, height = image_size
    fx, fy = intrinsic[0][0], intrinsic[1][1]
    cx, cy = intrinsic[0][2], intrinsic[1][2]
    corners = np.array(
        [
            [(0 - cx) / fx * depth, (0 - cy) / fy * depth, depth],
            [(width - cx) / fx * depth, (0 - cy) / fy * depth, depth],
            [(width - cx) / fx * depth, (height - cy) / fy * depth, depth],
            [(0 - cx) / fx * depth, (height - cy) / fy * depth, depth],
        ],
        dtype=np.float64,
    )
    origin = np.zeros((1, 3), dtype=np.float64)
    points = np.concatenate([origin, corners], axis=0)
    points_h = np.concatenate([points, np.ones((points.shape[0], 1))], axis=1)
    world = (np.asarray(camera_pose, dtype=np.float64) @ points_h.T).T[:, :3]

    meshes = []
    for i in range(1, 5):
        mesh = _line_mesh(world[0], world[i], radius=0.0012)
        if mesh is not None:
            meshes.append(mesh)
    for i, j in [(1, 2), (2, 3), (3, 4), (4, 1)]:
        mesh = _line_mesh(world[i], world[j], radius=0.0012)
        if mesh is not None:
            meshes.append(mesh)
    return meshes


def _look_at(eye, target, up=(0.0, 0.0, 1.0)):
    eye = np.asarray(eye, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)
    forward = target - eye
    forward = forward / np.linalg.norm(forward)
    z_axis = -forward
    x_axis = np.cross(up, z_axis)
    x_axis = x_axis / np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)
    pose = np.eye(4, dtype=np.float64)
    pose[:3, 0] = x_axis
    pose[:3, 1] = y_axis
    pose[:3, 2] = z_axis
    pose[:3, 3] = eye
    return pose


def _add_mesh(scene, mesh, name):
    scene.add(pyrender.Mesh.from_trimesh(mesh, smooth=False), name=name)


def render_scene(
    data_dir,
    scene_id,
    out_path,
    max_grasps=80,
    draw_cameras=True,
    width=1100,
    height=900,
):
    scene_dir = Path(data_dir) / str(scene_id)
    info = _load_json(scene_dir / "scene_info.json")
    scene = pyrender.Scene(bg_color=[255, 255, 255, 255], ambient_light=[0.35, 0.35, 0.35])

    table = trimesh.creation.box(
        [1.0, 1.0, 0.04],
        transform=trimesh.transformations.translation_matrix([0.0, 0.0, -0.02]),
    )
    _add_mesh(scene, _set_color(table, [115, 115, 115, 255]), "table")

    mesh_meta = info.get("mesh_meta", [{} for _ in info["obj_poses"]])
    for obj_idx, obj_pose in enumerate(info["obj_poses"]):
        mesh = _load_object_mesh(mesh_meta[obj_idx], obj_pose)
        _add_mesh(scene, mesh, "obj_{}".format(obj_idx))

    grasp_added = 0
    for poses, widths, collisions in zip(
        info["grasp_poses"], info["grasp_widths"], info["grasp_collision"]
    ):
        keep = [idx for idx, flag in enumerate(collisions) if not flag]
        if max_grasps > 0 and len(keep) > max_grasps:
            sample = np.linspace(0, len(keep) - 1, max_grasps).round().astype(int)
            keep = [keep[i] for i in sample]
        for idx in keep:
            grasp = Grasp(open_width=float(widths[idx]), pose=np.asarray(poses[idx]))
            grasp_mesh = trimesh.util.concatenate(grasp.get_mesh(kpts=False))
            grasp_mesh.visual.face_colors = np.asarray([0, 230, 0, 255], dtype=np.uint8)
            _add_mesh(scene, grasp_mesh, "grasp_{}".format(grasp_added))
            grasp_added += 1

    if draw_cameras:
        for camera_pose in info["camera_poses"]:
            for mesh in _camera_marker_meshes(camera_pose, info["intrinsic"]):
                _add_mesh(scene, mesh, "camera_marker")

    camera = pyrender.PerspectiveCamera(yfov=np.deg2rad(42.0))
    camera_pose = _look_at(eye=[0.48, -0.62, 0.52], target=[0.0, 0.0, 0.05])
    scene.add(camera, pose=camera_pose, name="render_camera")

    light = pyrender.DirectionalLight(color=np.ones(3), intensity=4.0)
    scene.add(light, pose=camera_pose)

    renderer = pyrender.OffscreenRenderer(viewport_width=width, viewport_height=height)
    color, _ = renderer.render(scene)
    renderer.delete()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), cv2.cvtColor(color, cv2.COLOR_RGB2BGR))
    return grasp_added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--scene_ids", nargs="+", type=int, default=[0, 1, 4, 8])
    parser.add_argument("--max_grasps", type=int, default=80)
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--no_cameras", action="store_true")
    args = parser.parse_args()

    for scene_id in args.scene_ids:
        out_path = Path(args.out_dir) / "graspnet_scene_{:04d}.png".format(scene_id)
        grasp_count = render_scene(
            args.data_dir,
            scene_id,
            out_path,
            max_grasps=args.max_grasps,
            draw_cameras=not args.no_cameras,
            width=args.width,
            height=args.height,
        )
        print("saved {} with {} grasps".format(out_path, grasp_count))


if __name__ == "__main__":
    main()
