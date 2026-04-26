#!/usr/bin/env python3
"""Render selected GraspNet88 predictions as two-finger gripper poses."""

from __future__ import absolute_import, division, print_function

import argparse
import json
import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import _init_paths  # noqa: E402,F401
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

from data_generation import MeshObject, SceneRender  # noqa: E402
from datasets.dataset_factory import dataset_factory  # noqa: E402
from detectors.detector_factory import detector_factory  # noqa: E402
from keypoint_graspnet import KeypointGraspNet as KGN  # noqa: E402
from opts import opts  # noqa: E402
from pose_recover.pnp_solver_factory import PnPSolverFactory  # noqa: E402
from utils.transform import cam_pose_convert, create_homog_matrix  # noqa: E402


DEFAULT_ANALYSIS_DIR = (
    "../exp/grasp_pose/t63_graspnet88_single_kgnv2_official_relaxed_d03_a45_visall/"
    "analysis_analysis_t63_graspnet88_single_kgnv2_relaxed_d03_a45_visall"
)
DEFAULT_SUMMARY = (
    DEFAULT_ANALYSIS_DIR
    + "/presentation/graspnet88_selected_atypical_objects_summary.json"
)


def _repo_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[1] / path).resolve()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary_json", default=DEFAULT_SUMMARY)
    parser.add_argument("--output_dir", default=None)
    parser.add_argument("--ps_data_dir", default="ps_grasp_single_graspnet_t63_eval_88obj")
    parser.add_argument("--load_model", default="../exp/kgnv2.pth")
    parser.add_argument("--top_k", type=int, default=8)
    parser.add_argument("--gpus", default="0")
    parser.add_argument("--dist_th", type=float, default=0.03)
    parser.add_argument("--angle_th", type=float, default=45.0)
    parser.add_argument("--center_thresh", type=float, default=0.3)
    parser.add_argument("--vis_thresh", type=float, default=0.3)
    parser.add_argument("--refine_scale", action="store_true")
    parser.add_argument("--max_width_for_vis", type=float, default=0.12)
    parser.add_argument("--render_camera_backoff", type=float, default=0.0)
    parser.add_argument("--panel_width", type=int, default=1280)
    return parser.parse_args()


def _build_opt(args):
    load_model = _repo_path(args.load_model)
    opt_args = [
        "grasp_pose",
        "--exp_id",
        "render_selected_graspnet88_two_finger",
        "--input_mod",
        "RGBD",
        "--dataset",
        "ps_grasp",
        "--ps_data_dir",
        args.ps_data_dir,
        "--keep_res",
        "--load_model",
        str(load_model),
        "--not_prefetch_test",
        "--trainval",
        "--kpt_type",
        "box",
        "--pnp_type",
        "cvIPPE",
        "--center_thresh",
        str(args.center_thresh),
        "--vis_thresh",
        str(args.vis_thresh),
        "--sep_scale_branch",
        "--no_nms",
        "--dist_th",
        str(args.dist_th),
        "--angle_th",
        str(args.angle_th),
        "--ori_num",
        "9",
        "--no_kpts_refine",
        "--scale_kpts_mode",
        "1",
        "--scale_coeff_k",
        "1",
        "--gpus",
        args.gpus,
        "--num_workers",
        "0",
    ]
    if args.refine_scale:
        opt_args.append("--refine_scale")
    parsed = opts().parse(opt_args)
    Dataset = dataset_factory[parsed.dataset]
    return opts().update_dataset_info_and_set_heads(parsed, Dataset)


def _load_selected(summary_json):
    with open(_repo_path(summary_json), "r") as handle:
        records = json.load(handle)
    selected = []
    for record in records:
        selected.append(
            {
                "object_id": str(record["object_id"]).zfill(3),
                "img_id": int(record["img_id"]),
                "camera_idx": int(record["camera_idx"]),
                "previous_successful_predictions": int(record["successful_predictions"]),
                "previous_accepted_predictions": int(record["accepted_predictions"]),
                "noncolliding_gt_scene": int(record["noncolliding_gt_scene"]),
            }
        )
    return selected


def _load_rgbd(dataset, img_id):
    rgb = cv2.imread(dataset.images[img_id])
    if rgb is None:
        raise FileNotFoundError(dataset.images[img_id])
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    depth = np.load(dataset.depths[img_id])
    rgbd = np.concatenate([rgb.astype(np.float32), depth[:, :, None]], axis=2)
    return rgb, depth, rgbd


def _world_poses(camera_pose, quaternions, locations):
    poses = []
    for quat, loc in zip(quaternions, locations):
        rot = R.from_quat(quat).as_matrix()
        pose_cam = create_homog_matrix(R_mat=rot, T_vec=loc)
        poses.append(camera_pose @ pose_cam)
    return np.asarray(poses, dtype=np.float64)


def _read_scene_json(dataset, scene_idx):
    scene_path = Path(dataset.data_dir) / str(scene_idx) / "scene_info.json"
    with open(scene_path, "r") as handle:
        return json.load(handle)


def _render_grippers(
    intrinsic,
    camera_pose_cv,
    obj_pose,
    mesh_meta,
    grasp_poses_world,
    grasp_widths,
    max_width_for_vis,
    render_camera_backoff,
):
    scene = SceneRender(
        table_size=1,
        table_thickness=0.04,
        table_color=[0.50, 0.50, 0.50, 1.0],
        camera=intrinsic,
        cam_width=640,
        cam_height=480,
        camera_num=1,
    )
    mesh_obj = MeshObject(
        mesh_path=mesh_meta["mesh_path"],
        mesh_scale=float(mesh_meta.get("mesh_scale", 1.0)),
        grasp_poses=np.zeros((0, 4, 4), dtype=np.float64),
        grasp_widths=np.zeros((0,), dtype=np.float64),
        color=np.array([120, 170, 235], dtype=np.uint8),
        pose=np.asarray(obj_pose, dtype=np.float64),
        mesh_meta=mesh_meta,
    )
    scene.add_objs([mesh_obj])
    render_camera_pose_cv = np.asarray(camera_pose_cv, dtype=np.float64).copy()
    render_camera_pose_cv[:3, 3] -= (
        render_camera_pose_cv[:3, 2] * float(render_camera_backoff)
    )
    scene.camera_poses = cam_pose_convert(np.asarray([render_camera_pose_cv]), mode="cv2gl")
    widths_vis = np.asarray(grasp_widths, dtype=np.float64).copy()
    widths_vis[widths_vis < 0.02] = widths_vis[widths_vis < 0.02] * 3.0
    widths_vis = np.clip(widths_vis, 0.005, float(max_width_for_vis))
    scene.grasp_poses = [np.asarray(grasp_poses_world, dtype=np.float64)]
    scene.grasp_widths = [widths_vis]
    scene.grasp_collide = [np.zeros((len(widths_vis),), dtype=bool)]
    scene.grasp_color = [0, 255, 0]
    scene.grasp_analyzed = True
    colors, _ = scene.render_imgs(instance_masks=False, grasp_mode=0)
    return colors[0]


def _fit_image(image, size):
    return Image.fromarray(image).resize(size, Image.Resampling.LANCZOS)


def _font(size):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _make_panel(rgb, rendered, title, subtitle, panel_width):
    title_h = 58
    label_h = 34
    gap = 18
    margin = 22
    col_w = (panel_width - margin * 2 - gap) // 2
    col_h = int(col_w * 480 / 640)
    panel_h = margin + title_h + label_h + col_h + margin
    canvas = Image.new("RGB", (panel_width, panel_h), (248, 248, 246))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 14), title, fill=(20, 20, 20), font=_font(24))
    draw.text((margin, 42), subtitle, fill=(70, 70, 70), font=_font(16))
    y0 = margin + title_h
    draw.text((margin, y0), "Input RGB", fill=(55, 55, 55), font=_font(16))
    draw.text(
        (margin + col_w + gap, y0),
        "KGNv2 prediction as two-finger gripper poses",
        fill=(35, 125, 35),
        font=_font(16),
    )
    img_y = y0 + label_h
    canvas.paste(_fit_image(rgb, (col_w, col_h)), (margin, img_y))
    canvas.paste(_fit_image(rendered, (col_w, col_h)), (margin + col_w + gap, img_y))
    return canvas


def _make_montage(panel_paths, out_path, columns=2):
    panels = [Image.open(path).convert("RGB") for path in panel_paths]
    if not panels:
        return
    thumb_w = 900
    thumbs = []
    for panel in panels:
        h = int(panel.height * thumb_w / panel.width)
        thumbs.append(panel.resize((thumb_w, h), Image.Resampling.LANCZOS))
    rows = int(np.ceil(len(thumbs) / columns))
    gap = 24
    margin = 28
    thumb_h = max(img.height for img in thumbs)
    canvas = Image.new(
        "RGB",
        (
            columns * thumb_w + (columns - 1) * gap + margin * 2,
            rows * thumb_h + (rows - 1) * gap + margin * 2,
        ),
        (242, 242, 240),
    )
    for idx, img in enumerate(thumbs):
        row, col = divmod(idx, columns)
        x = margin + col * (thumb_w + gap)
        y = margin + row * (thumb_h + gap)
        canvas.paste(img, (x, y))
    canvas.save(out_path, quality=95)


def main():
    args = _parse_args()
    opt = _build_opt(args)
    selected = _load_selected(args.summary_json)

    Dataset = dataset_factory[opt.dataset]
    dataset = Dataset(opt, "test")
    Detector = detector_factory[opt.task]
    detector = Detector(opt)
    PNPSolver = PnPSolverFactory[opt.pnp_type]
    pnp_solver = PNPSolver(kpt_type=opt.kpt_type, use_center=opt.use_center)
    kgn = KGN(opt, detector, pnp_solver)

    analysis_dir = _repo_path(DEFAULT_ANALYSIS_DIR)
    output_dir = Path(args.output_dir) if args.output_dir else analysis_dir / "presentation" / "two_finger_gripper_panels"
    output_dir = _repo_path(output_dir)
    individual_dir = output_dir / "individuals"
    individual_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    panel_paths = []
    for record in selected:
        img_id = record["img_id"]
        scene_idx = int(dataset.scene_idxs[img_id])
        cam_idx = int(dataset.camera_idxs[img_id])
        rgb, _, rgbd = _load_rgbd(dataset, img_id)
        intrinsic, camera_poses, obj_types, _, obj_poses, _, _, _ = dataset._get_scene_info(scene_idx)
        kgn.set_cam_intrinsic_mat(intrinsic)
        quats, locs, widths, _, scores, _, _, analysis = kgn.generate(rgbd, return_all=True)
        result = {"locations": locs, "quaternions": quats, "widths": widths}
        eval_flags = dataset.run_eval(
            {img_id: result},
            str(output_dir),
            angle_th=opt.angle_th,
            dist_th=opt.dist_th,
            rot_sample=-1,
            trl_sample=-1,
        )[img_id]

        scores = np.asarray(scores, dtype=np.float32).reshape(-1)
        eval_flags = np.asarray(eval_flags, dtype=bool).reshape(-1)
        success_ids = np.where(eval_flags)[0]
        if success_ids.size > 0:
            order = success_ids[np.argsort(-scores[success_ids], kind="mergesort")]
            selected_ids = order[: args.top_k]
            selection_note = "top successful"
        else:
            order = np.argsort(-scores, kind="mergesort")
            selected_ids = order[: args.top_k]
            selection_note = "top score fallback"

        scene_json = _read_scene_json(dataset, scene_idx)
        mesh_meta = scene_json["mesh_meta"][0]
        world_poses = _world_poses(camera_poses[cam_idx], quats[selected_ids], locs[selected_ids])
        rendered = _render_grippers(
            intrinsic=np.asarray(intrinsic, dtype=np.float64),
            camera_pose_cv=np.asarray(camera_poses[cam_idx], dtype=np.float64),
            obj_pose=np.asarray(obj_poses[0], dtype=np.float64),
            mesh_meta=mesh_meta,
            grasp_poses_world=world_poses,
            grasp_widths=widths[selected_ids],
            max_width_for_vis=args.max_width_for_vis,
            render_camera_backoff=args.render_camera_backoff,
        )

        object_id = str(mesh_meta.get("object_id", record["object_id"])).zfill(3)
        title = "Object {} | camera {} | {} {}/{}".format(
            object_id,
            cam_idx,
            "success",
            int(eval_flags.sum()),
            int(eval_flags.size),
        )
        protocol = "primitive-trained KGNv2 + Refine-Scale" if args.refine_scale else "primitive-trained KGNv2"
        subtitle = (
            "{}, relaxed match 3cm + 45deg, "
            "{} {} grippers shown, GT {}".format(
                protocol,
                selection_note,
                int(len(selected_ids)),
                record["noncolliding_gt_scene"],
            )
        )
        panel = _make_panel(rgb, rendered, title, subtitle, args.panel_width)

        stem = "object_{}_cam{}_two_finger".format(object_id, cam_idx)
        rgb_path = individual_dir / "{}_input_rgb.png".format(stem)
        gripper_path = individual_dir / "{}_grippers.png".format(stem)
        panel_path = individual_dir / "{}_panel.png".format(stem)
        Image.fromarray(rgb).save(rgb_path)
        Image.fromarray(rendered).save(gripper_path)
        panel.save(panel_path, quality=95)
        panel_paths.append(panel_path)
        summary.append(
            {
                "object_id": object_id,
                "img_id": int(img_id),
                "scene_idx": int(scene_idx),
                "camera_idx": int(cam_idx),
                "accepted_predictions": int(eval_flags.size),
                "successful_predictions": int(eval_flags.sum()),
                "shown_grippers": int(len(selected_ids)),
                "selection_note": selection_note,
                "noncolliding_gt_scene": int(record["noncolliding_gt_scene"]),
                "input_rgb": str(rgb_path),
                "gripper_render": str(gripper_path),
                "panel": str(panel_path),
            }
        )
        print("saved", panel_path)

    montage_path = output_dir / "graspnet88_selected_two_finger_gripper_montage.jpg"
    _make_montage(panel_paths, montage_path, columns=2)
    with open(output_dir / "graspnet88_selected_two_finger_gripper_summary.json", "w") as handle:
        json.dump(summary, handle, indent=2)
    print("montage:", montage_path)
    print("summary:", output_dir / "graspnet88_selected_two_finger_gripper_summary.json")


if __name__ == "__main__":
    main()
