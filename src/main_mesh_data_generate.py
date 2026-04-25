import argparse
import os
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

import _init_paths

from data_generation import SceneRender
from data_generation.dataLogger import DataLogger
from data_generation.mesh_grasp.acronym_loader import (
    load_acronym_grasp_file,
    scan_acronym_grasp_files,
)
from data_generation.objects.MeshObject import MeshObject
from utils.configs import load_config
from utils.file import write_numList_to_file


def _resolve_path(path):
    return str(Path(path).expanduser().resolve())


def generate_and_write_split(total_scene_num, test_percentage, save_dir):
    test_num = round(total_scene_num * (test_percentage / 100))
    scene_idx = np.arange(total_scene_num)
    np.random.shuffle(scene_idx)
    test_idx, train_idx, _ = np.split(scene_idx, [test_num, total_scene_num])
    write_numList_to_file(os.path.join(save_dir, "train.txt"), train_idx)
    write_numList_to_file(os.path.join(save_dir, "test.txt"), test_idx)


def _load_grasp_catalog(mesh_cfg):
    grasp_root = _resolve_path(mesh_cfg["grasp_root"])
    mesh_root = _resolve_path(mesh_cfg["mesh_root"])
    categories = mesh_cfg.get("categories", None)
    grasp_files = scan_acronym_grasp_files(grasp_root, categories=categories)
    max_objects = int(mesh_cfg.get("max_objects", -1))
    if max_objects > 0:
        grasp_files = grasp_files[:max_objects]
    if not grasp_files:
        raise RuntimeError("No ACRONYM grasp files found under {}".format(grasp_root))
    return grasp_files, mesh_root


def _make_mesh_object(grasp_file, mesh_root, mesh_cfg, seed):
    grasp_data = load_acronym_grasp_file(
        grasp_file,
        mesh_root=mesh_root,
        max_grasps=int(mesh_cfg.get("max_grasps_per_object", 300)),
        min_grasps=int(mesh_cfg.get("min_grasps_per_object", 1)),
        width_range=tuple(mesh_cfg.get("width_range", [0.01, 0.085])),
        gripper_depth=float(mesh_cfg.get("gripper_depth", 0.11217)),
        seed=seed,
        convert_to_kgn_frame=bool(mesh_cfg.get("convert_to_kgn_frame", True)),
    )
    color = np.random.choice(range(256), size=3).astype(np.uint8)
    return MeshObject(
        mesh_path=grasp_data.mesh_path,
        mesh_scale=grasp_data.mesh_scale,
        grasp_poses=grasp_data.grasp_poses,
        grasp_widths=grasp_data.grasp_widths,
        color=color,
        obj_type="mesh",
        mesh_meta=grasp_data.meta,
    )


def _collect_mesh_meta(scene_renderer):
    mesh_meta = []
    for obj in scene_renderer.objects:
        if hasattr(obj, "get_mesh_meta"):
            mesh_meta.append(obj.get_mesh_meta())
        else:
            mesh_meta.append({})
    return mesh_meta


def main(args, configs):
    scene_renderer = SceneRender(
        table_size=configs["TABLE"]["size"],
        table_thickness=configs["TABLE"]["thickness"],
        camera=configs["CAMERA"]["intrinsic"],
        camera_num=configs["CAMERA"]["camera_num"],
        radius_range=configs["CAMERA"]["radius_range"],
        latitude_range=np.array(configs["CAMERA"]["latitude_range"]) / 180 * np.pi,
    )

    save_path = configs["SAVE_PATH"]
    logger = DataLogger(logging_directory=save_path)
    mesh_cfg = configs["MESH_DATA"]
    grasp_files, mesh_root = _load_grasp_catalog(mesh_cfg)
    max_attempts = int(configs["CARDINALITY"].get("max_attempts_per_scene", 20))

    print(
        "T6.2 mesh dataset generation: {} grasp files, save_path={}".format(
            len(grasp_files), save_path
        )
    )

    scene_count = 0
    total_scene_num = int(configs["CARDINALITY"]["scene_num"])
    tqdm_bar = tqdm(total=total_scene_num)
    while scene_count < total_scene_num:
        np.random.seed(scene_count)
        random.seed(scene_count)
        success = False

        for attempt in range(max_attempts):
            scene_renderer.clear_objs()
            scene_renderer.resample_camera_poses()
            grasp_file = random.choice(grasp_files)

            try:
                obj = _make_mesh_object(
                    grasp_file,
                    mesh_root=mesh_root,
                    mesh_cfg=mesh_cfg,
                    seed=scene_count * 1000 + attempt,
                )
                scene_renderer.add_obj(obj, sample_pose=True, resample_xy_loc=False)
                intrinsic, cam_poses, _ = scene_renderer.get_camera_infos(style="OpenCV")
                grasp_poses, open_widths, collides = scene_renderer.get_grasp_infos()
                obj_types, obj_dims, obj_poses = scene_renderer.get_obj_infos()
                colors, depths, ins_masks = scene_renderer.render_imgs(instance_masks=True)
                mesh_meta = _collect_mesh_meta(scene_renderer)

                if args.debug:
                    scene_renderer.vis_scene(grasp_mode=1, world_frame=True)
                    for color, depth, ins_mask in zip(colors, depths, ins_masks):
                        _, axarr = plt.subplots(1, 3)
                        axarr[0].imshow(color)
                        axarr[1].imshow(depth)
                        axarr[2].imshow(ins_mask)
                    plt.show()

                logger.save_scene_data(
                    scene_count,
                    intrinsic,
                    cam_poses,
                    colors,
                    depths,
                    ins_masks,
                    grasp_poses,
                    open_widths,
                    grasp_collision=collides,
                    obj_types=obj_types,
                    obj_dims=obj_dims,
                    obj_poses=obj_poses,
                    mesh_meta=mesh_meta,
                )
                success = True
                break
            except Exception as exc:
                tqdm_bar.set_description(
                    "Failed scene {} attempt {}: {}".format(scene_count, attempt, exc)
                )

        if not success:
            raise RuntimeError(
                "Failed to generate scene {} after {} attempts".format(
                    scene_count, max_attempts
                )
            )

        scene_count += 1
        tqdm_bar.set_description("Scene data saved out.")
        tqdm_bar.update()

    print("\n\n Splitting into training and testing subset...")
    generate_and_write_split(
        total_scene_num,
        configs["CARDINALITY"]["test_percentage"],
        save_path,
    )
    print("Split completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_file",
        default="lib/data_generation/ps_grasp_single_mesh_t62_smoke.yaml",
        help="The configuration file.",
    )
    parser.add_argument("--debug", action="store_true", help="Visualize generated scenes.")
    parser.add_argument(
        "--arg_configs",
        nargs="*",
        type=str,
        default=[],
        help="overwrite config parameters",
    )
    args = parser.parse_args()
    print(args)
    cfg = load_config(args.config_file, arg_configs=args.arg_configs)
    main(args, cfg)

