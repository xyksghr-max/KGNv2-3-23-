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
from data_generation.mesh_grasp.graspnet_loader import (
    load_graspnet_grasp_file,
    scan_graspnet_object_ids,
)
from data_generation.objects.MeshObject import MeshObject
from utils.configs import load_config
from utils.file import write_numList_to_file


def _resolve_path(path):
    return str(Path(path).expanduser().resolve())


def generate_and_write_split(total_scene_num, test_percentage, save_dir, shuffle=True):
    test_num = round(total_scene_num * (test_percentage / 100))
    scene_idx = np.arange(total_scene_num)
    if shuffle:
        np.random.shuffle(scene_idx)
    test_idx, train_idx, _ = np.split(scene_idx, [test_num, total_scene_num])
    write_numList_to_file(os.path.join(save_dir, "train.txt"), train_idx)
    write_numList_to_file(os.path.join(save_dir, "test.txt"), test_idx)


def _load_graspnet_catalog(graspnet_cfg):
    raw_root = _resolve_path(graspnet_cfg["raw_root"])
    object_ids = graspnet_cfg.get("object_ids", None)
    object_ids = scan_graspnet_object_ids(
        raw_root,
        object_ids=object_ids,
        max_objects=int(graspnet_cfg.get("max_objects", -1)),
    )
    if not object_ids:
        raise RuntimeError("No GraspNet object ids found under {}".format(raw_root))
    return raw_root, object_ids


def _select_object_id(object_ids, scene_count, sampling_mode):
    if sampling_mode == "random":
        return random.choice(object_ids)
    if sampling_mode == "sequential":
        return object_ids[scene_count % len(object_ids)]
    raise ValueError(
        "Unsupported GRASPNET_DATA.sampling_mode={!r}; choose 'random' or "
        "'sequential'.".format(sampling_mode)
    )


def _load_graspnet_data(raw_root, object_id, graspnet_cfg, seed):
    return load_graspnet_grasp_file(
        raw_root=raw_root,
        object_id=object_id,
        mesh_name=graspnet_cfg.get("mesh_name", "nontextured_simplified.ply"),
        max_grasps=int(graspnet_cfg.get("max_grasps_per_object", 300)),
        min_grasps=int(graspnet_cfg.get("min_grasps_per_object", 100)),
        width_range=tuple(graspnet_cfg.get("width_range", [0.01, 0.085])),
        score_max=float(graspnet_cfg.get("score_max", 0.4)),
        seed=seed,
        convert_to_kgn_frame=bool(graspnet_cfg.get("convert_to_kgn_frame", True)),
        use_collision=bool(graspnet_cfg.get("use_collision", True)),
    )


def _make_mesh_object(grasp_data):
    color = np.random.choice(range(256), size=3).astype(np.uint8)
    return MeshObject(
        mesh_path=grasp_data.mesh_path,
        mesh_scale=1.0,
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


def _count_noncolliding_grasps(collides):
    return int(sum(np.count_nonzero(~c) for c in collides))


def _render_scene_payload(args, scene_renderer, intrinsic, cam_poses,
                          grasp_poses, open_widths, collides):
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

    return {
        "intrinsic": intrinsic,
        "cam_poses": cam_poses,
        "colors": colors,
        "depths": depths,
        "ins_masks": ins_masks,
        "grasp_poses": grasp_poses,
        "open_widths": open_widths,
        "collides": collides,
        "obj_types": obj_types,
        "obj_dims": obj_dims,
        "obj_poses": obj_poses,
        "mesh_meta": mesh_meta,
    }


def _save_scene_payload(logger, scene_count, payload):
    logger.save_scene_data(
        scene_count,
        payload["intrinsic"],
        payload["cam_poses"],
        payload["colors"],
        payload["depths"],
        payload["ins_masks"],
        payload["grasp_poses"],
        payload["open_widths"],
        grasp_collision=payload["collides"],
        obj_types=payload["obj_types"],
        obj_dims=payload["obj_dims"],
        obj_poses=payload["obj_poses"],
        mesh_meta=payload["mesh_meta"],
    )


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
    graspnet_cfg = configs["GRASPNET_DATA"]
    raw_root, object_ids = _load_graspnet_catalog(graspnet_cfg)
    max_attempts = int(configs["CARDINALITY"].get("max_attempts_per_scene", 20))
    min_noncolliding = int(configs["CARDINALITY"].get("min_noncolliding_grasps", 1))
    allow_best_effort = bool(configs["CARDINALITY"].get("allow_best_effort", False))
    best_effort_min = int(
        configs["CARDINALITY"].get("best_effort_min_noncolliding_grasps", 1)
    )
    sampling_mode = str(graspnet_cfg.get("sampling_mode", "random")).lower()
    data_cache = {}
    total_scene_num = int(configs["CARDINALITY"]["scene_num"])

    if sampling_mode == "sequential" and total_scene_num != len(object_ids):
        print(
            "Warning: sequential GraspNet generation has scene_num={} but "
            "{} object ids. Object ids will be cycled/truncated by scene index.".format(
                total_scene_num, len(object_ids)
            )
        )

    print(
        "T6.3 GraspNet dataset generation: {} objects, sampling_mode={}, "
        "save_path={}".format(
            len(object_ids), sampling_mode, save_path
        )
    )

    scene_count = 0
    tqdm_bar = tqdm(total=total_scene_num)
    while scene_count < total_scene_num:
        np.random.seed(scene_count)
        random.seed(scene_count)
        success = False
        best_payload = None
        best_noncolliding = -1
        best_attempt = -1

        for attempt in range(max_attempts):
            scene_renderer.clear_objs()
            scene_renderer.resample_camera_poses()
            object_id = _select_object_id(object_ids, scene_count, sampling_mode)

            try:
                cache_key = (object_id, scene_count * 1000 + attempt)
                if cache_key not in data_cache:
                    data_cache[cache_key] = _load_graspnet_data(
                        raw_root,
                        object_id,
                        graspnet_cfg,
                        seed=scene_count * 1000 + attempt,
                    )
                obj = _make_mesh_object(data_cache[cache_key])

                scene_renderer.add_obj(obj, sample_pose=True, resample_xy_loc=False)
                intrinsic, cam_poses, _ = scene_renderer.get_camera_infos(style="OpenCV")
                grasp_poses, open_widths, collides = scene_renderer.get_grasp_infos()
                noncollide_num = _count_noncolliding_grasps(collides)
                if noncollide_num >= min_noncolliding:
                    payload = _render_scene_payload(
                        args,
                        scene_renderer,
                        intrinsic,
                        cam_poses,
                        grasp_poses,
                        open_widths,
                        collides,
                    )
                    _save_scene_payload(logger, scene_count, payload)
                    success = True
                    break

                if (
                    allow_best_effort
                    and noncollide_num >= best_effort_min
                    and noncollide_num > best_noncolliding
                ):
                    best_payload = _render_scene_payload(
                        args,
                        scene_renderer,
                        intrinsic,
                        cam_poses,
                        grasp_poses,
                        open_widths,
                        collides,
                    )
                    best_noncolliding = noncollide_num
                    best_attempt = attempt

                raise ValueError(
                    "Only {} non-colliding grasps survived scene filtering; "
                    "need {}".format(noncollide_num, min_noncolliding)
                )
            except Exception as exc:
                tqdm_bar.set_description(
                    "Failed scene {} attempt {}: {}".format(scene_count, attempt, exc)
                )

        if not success:
            if allow_best_effort and best_payload is not None:
                _save_scene_payload(logger, scene_count, best_payload)
                tqdm.write(
                    "Scene {} saved best-effort attempt {} with {} "
                    "non-colliding grasps below target {}.".format(
                        scene_count,
                        best_attempt,
                        best_noncolliding,
                        min_noncolliding,
                    )
                )
                success = True
            else:
                raise RuntimeError(
                    "Failed to generate scene {} after {} attempts; best "
                    "non-colliding grasp count was {}".format(
                        scene_count, max_attempts, best_noncolliding
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
        shuffle=bool(configs["CARDINALITY"].get("shuffle_split", True)),
    )
    print("Split completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_file",
        default="lib/data_generation/ps_grasp_single_graspnet_t63_smoke.yaml",
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
