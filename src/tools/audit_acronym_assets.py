import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import h5py
import numpy as np
import trimesh

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import _init_paths  # noqa: E402,F401
from data_generation.mesh_grasp.acronym_loader import _decode_h5_value  # noqa: E402


def _norm_category(category):
    return str(category).strip().lower()


def _infer_category_object_id(grasp_path):
    stem = Path(grasp_path).stem
    parts = stem.split("_")
    category = parts[0] if parts else "mesh"
    object_id = parts[1] if len(parts) > 1 else stem
    return category, object_id


def _resolve_mesh_path(mesh_root, mesh_file):
    mesh_file_path = Path(mesh_file)
    if mesh_file_path.is_absolute():
        return mesh_file_path
    return Path(mesh_root) / mesh_file_path


def _load_widths(handle, count):
    if "gripper/configuration" not in handle:
        return np.full((count,), 0.08, dtype=np.float64)
    config = np.asarray(handle["gripper/configuration"])
    if config.size == 0:
        width = 0.08
    else:
        width = float(np.ravel(config)[0]) * 2.0
    return np.full((count,), width, dtype=np.float64)


def _audit_one_h5(path, args, target_categories, support_categories):
    row = {
        "h5_path": str(path),
        "category": "",
        "object_id": "",
        "object_file": "",
        "object_scale": "",
        "mesh_path": "",
        "mesh_exists": False,
        "mesh_loadable": False,
        "bbox_x": "",
        "bbox_y": "",
        "bbox_z": "",
        "bbox_suspicious": False,
        "total_grasps": 0,
        "inspected_grasps": 0,
        "successful_grasps": 0,
        "valid_width_grasps": 0,
        "is_target_category": False,
        "is_support_category": False,
        "meets_min_valid_grasps": False,
        "training_candidate": False,
        "failure_reason": "",
    }
    failure_reasons = []

    category, object_id = _infer_category_object_id(path)
    row["category"] = category
    row["object_id"] = object_id
    row["is_target_category"] = _norm_category(category) in target_categories
    row["is_support_category"] = _norm_category(category) in support_categories
    if target_categories and not row["is_target_category"]:
        failure_reasons.append("unsupported_category")

    try:
        with h5py.File(path, "r") as handle:
            transforms = handle["grasps/transforms"]
            total_grasps = int(transforms.shape[0])
            stat_count = total_grasps
            if args.max_stat_grasps > 0:
                stat_count = min(total_grasps, args.max_stat_grasps)

            success = np.asarray(
                handle["grasps/qualities/flex/object_in_gripper"][:stat_count]
            ).astype(np.float32) > 0.5
            widths = _load_widths(handle, total_grasps)[:stat_count]

            object_file = _decode_h5_value(handle["object/file"][()])
            object_scale = float(handle["object/scale"][()])
            mesh_path = _resolve_mesh_path(args.mesh_root, object_file)

            valid_width = (widths >= args.width_min) & (widths <= args.width_max)
            valid_grasps = success & valid_width

            row.update(
                {
                    "object_file": object_file,
                    "object_scale": object_scale,
                    "mesh_path": str(mesh_path),
                    "total_grasps": total_grasps,
                    "inspected_grasps": stat_count,
                    "successful_grasps": int(np.count_nonzero(success)),
                    "valid_width_grasps": int(np.count_nonzero(valid_grasps)),
                    "meets_min_valid_grasps": int(np.count_nonzero(valid_grasps))
                    >= args.min_valid_grasps,
                }
            )
            if int(np.count_nonzero(valid_grasps)) == 0:
                failure_reasons.append("bad_width")
            elif int(np.count_nonzero(valid_grasps)) < args.min_valid_grasps:
                failure_reasons.append("too_few_success")
    except Exception as exc:
        row["failure_reason"] = "bad_h5:{}".format(type(exc).__name__)
        return row

    mesh_path = Path(row["mesh_path"])
    row["mesh_exists"] = mesh_path.exists()
    if not row["mesh_exists"]:
        failure_reasons.append("missing_mesh")
    else:
        try:
            mesh = trimesh.load(mesh_path, force="mesh")
            if isinstance(mesh, trimesh.Scene):
                mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
            mesh.apply_scale(float(row["object_scale"]))
            extents = np.asarray(mesh.bounding_box.extents, dtype=np.float64)
            row["mesh_loadable"] = True
            row["bbox_x"] = float(extents[0])
            row["bbox_y"] = float(extents[1])
            row["bbox_z"] = float(extents[2])
            suspicious = bool(
                np.any(extents < args.bbox_min) or np.any(extents > args.bbox_max)
            )
            row["bbox_suspicious"] = suspicious
        except Exception as exc:
            row["mesh_loadable"] = False
            failure_reasons.append("bad_mesh:{}".format(type(exc).__name__))

    row["training_candidate"] = bool(
        row["is_target_category"]
        and not row["is_support_category"]
        and row["mesh_exists"]
        and row["mesh_loadable"]
        and row["meets_min_valid_grasps"]
    )
    if row["is_support_category"] and "support_category" not in failure_reasons:
        failure_reasons.append("support_category")
    if row["bbox_suspicious"]:
        failure_reasons.append("suspicious_bbox")
    row["failure_reason"] = ";".join(failure_reasons)
    return row


def _write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "h5_path",
        "category",
        "object_id",
        "object_file",
        "object_scale",
        "mesh_path",
        "mesh_exists",
        "mesh_loadable",
        "bbox_x",
        "bbox_y",
        "bbox_z",
        "bbox_suspicious",
        "total_grasps",
        "inspected_grasps",
        "successful_grasps",
        "valid_width_grasps",
        "is_target_category",
        "is_support_category",
        "meets_min_valid_grasps",
        "training_candidate",
        "failure_reason",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows):
    summary = {
        "total_h5": len(rows),
        "mesh_exists": sum(bool(row["mesh_exists"]) for row in rows),
        "mesh_loadable": sum(bool(row["mesh_loadable"]) for row in rows),
        "target_category": sum(bool(row["is_target_category"]) for row in rows),
        "support_category": sum(bool(row["is_support_category"]) for row in rows),
        "training_candidates": sum(bool(row["training_candidate"]) for row in rows),
        "categories": {},
        "failure_reasons": defaultdict(int),
    }
    by_category = defaultdict(lambda: {"total": 0, "training_candidates": 0})
    for row in rows:
        cat = row["category"] or "unknown"
        by_category[cat]["total"] += 1
        if row["training_candidate"]:
            by_category[cat]["training_candidates"] += 1
        for reason in str(row["failure_reason"]).split(";"):
            if reason:
                summary["failure_reasons"][reason] += 1
    summary["categories"] = dict(sorted(by_category.items()))
    summary["failure_reasons"] = dict(sorted(summary["failure_reasons"].items()))
    return summary


def _write_json(rows, summary, path, args):
    payload = {
        "args": vars(args),
        "summary": summary,
        "rows": rows,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def _write_markdown(rows, summary, path, args):
    lines = []
    lines.append("# ACRONYM Asset Audit Report")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append("- grasp_root: `{}`".format(args.grasp_root))
    lines.append("- mesh_root: `{}`".format(args.mesh_root))
    lines.append("- target_categories: `{}`".format(", ".join(args.target_categories)))
    lines.append("- support_categories: `{}`".format(", ".join(args.support_categories)))
    lines.append("- min_valid_grasps: `{}`".format(args.min_valid_grasps))
    lines.append("- width_range: `{} / {}`".format(args.width_min, args.width_max))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in summary.items():
        if key not in ["categories", "failure_reasons"]:
            lines.append("- {}: `{}`".format(key, value))
    lines.append("")
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| category | total | training_candidates |")
    lines.append("| --- | ---: | ---: |")
    for category, data in summary["categories"].items():
        lines.append(
            "| {} | {} | {} |".format(
                category, data["total"], data["training_candidates"]
            )
        )
    lines.append("")
    lines.append("## Failure Reasons")
    lines.append("")
    if summary["failure_reasons"]:
        for reason, count in summary["failure_reasons"].items():
            lines.append("- `{}`: {}".format(reason, count))
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Training Candidates")
    lines.append("")
    candidate_rows = [row for row in rows if row["training_candidate"]]
    if not candidate_rows:
        lines.append("No training candidates found.")
    else:
        lines.append("| category | object_id | valid_width_grasps | bbox |")
        lines.append("| --- | --- | ---: | --- |")
        for row in candidate_rows[:100]:
            bbox = "{:.4f}, {:.4f}, {:.4f}".format(
                float(row["bbox_x"]), float(row["bbox_y"]), float(row["bbox_z"])
            )
            lines.append(
                "| {} | {} | {} | {} |".format(
                    row["category"], row["object_id"], row["valid_width_grasps"], bbox
                )
            )
    lines.append("")
    path.write_text("\n".join(lines))


def audit(args):
    grasp_root = Path(args.grasp_root).expanduser().resolve()
    args.grasp_root = str(grasp_root)
    args.mesh_root = str(Path(args.mesh_root).expanduser().resolve())
    out_dir = Path(args.out_dir).expanduser().resolve()

    target_categories = {_norm_category(cat) for cat in args.target_categories}
    support_categories = {_norm_category(cat) for cat in args.support_categories}

    if grasp_root.exists():
        h5_paths = sorted(grasp_root.rglob("*.h5"))
    else:
        h5_paths = []

    rows = [
        _audit_one_h5(path, args, target_categories, support_categories)
        for path in h5_paths
    ]
    summary = _summarize(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, out_dir / "acronym_asset_summary.csv")
    _write_json(rows, summary, out_dir / "acronym_asset_summary.json", args)
    _write_markdown(rows, summary, out_dir / "acronym_asset_report.md", args)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print("Report written to {}".format(out_dir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grasp_root", required=True)
    parser.add_argument("--mesh_root", required=True)
    parser.add_argument(
        "--target_categories",
        nargs="+",
        default=["Mug", "Bottle", "Bowl", "Can", "Box", "Tool"],
    )
    parser.add_argument("--support_categories", nargs="+", default=["Table"])
    parser.add_argument("--min_valid_grasps", type=int, default=100)
    parser.add_argument("--width_min", type=float, default=0.01)
    parser.add_argument("--width_max", type=float, default=0.085)
    parser.add_argument("--bbox_min", type=float, default=0.01)
    parser.add_argument("--bbox_max", type=float, default=0.35)
    parser.add_argument("--max_stat_grasps", type=int, default=2000)
    parser.add_argument("--out_dir", required=True)
    audit(parser.parse_args())
