import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import trimesh


def _choose_mesh_path(model_dir, mesh_name):
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


def _safe_float(value):
    if value is None:
        return ""
    return float(value)


def _load_mesh_stats(mesh_path):
    mesh = trimesh.load(mesh_path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    extents = np.asarray(mesh.bounding_box.extents, dtype=np.float64)
    return extents


def _summarize_label(label_path, args):
    with np.load(label_path) as data:
        keys = list(data.files)
        required = ["points", "offsets", "scores"]
        missing = [key for key in required if key not in keys]
        if missing:
            raise KeyError("missing keys: {}".format(",".join(missing)))

        points = data["points"]
        scores = data["scores"]
        offsets = data["offsets"]
        collision = data["collision"] if "collision" in keys else None

        total_candidates = int(np.prod(scores.shape))
        score_positive = (scores > 0.0) & (scores <= args.score_max)
        widths = offsets[..., 2]
        width_valid = (widths >= args.width_min) & (widths <= args.width_max)
        valid = score_positive & width_valid

        if collision is not None and not args.ignore_collision:
            valid = valid & (~collision.astype(bool))

        stats = {
            "keys": keys,
            "points_count": int(points.shape[0]),
            "offsets_shape": list(offsets.shape),
            "scores_shape": list(scores.shape),
            "has_collision": collision is not None,
            "collision_shape": list(collision.shape) if collision is not None else [],
            "total_candidates": total_candidates,
            "score_positive_count": int(np.count_nonzero(score_positive)),
            "width_valid_count": int(np.count_nonzero(width_valid)),
            "valid_grasps": int(np.count_nonzero(valid)),
            "score_min": _safe_float(np.min(scores)) if scores.size else "",
            "score_max": _safe_float(np.max(scores)) if scores.size else "",
            "width_min": _safe_float(np.min(widths)) if widths.size else "",
            "width_max": _safe_float(np.max(widths)) if widths.size else "",
            "width_mean": _safe_float(np.mean(widths)) if widths.size else "",
        }
        if collision is not None:
            stats["collision_count"] = int(np.count_nonzero(collision))
        else:
            stats["collision_count"] = ""
        return stats


def _audit_one_object(obj_id, args):
    raw_root = Path(args.graspnet_root)
    model_dir = raw_root / "models" / obj_id
    label_path = raw_root / "grasp_label" / "{}_labels.npz".format(obj_id)
    mesh_path = _choose_mesh_path(model_dir, args.mesh_name)

    row = {
        "object_id": obj_id,
        "model_dir": str(model_dir),
        "mesh_path": str(mesh_path),
        "mesh_exists": False,
        "mesh_loadable": False,
        "bbox_x": "",
        "bbox_y": "",
        "bbox_z": "",
        "bbox_suspicious": False,
        "label_path": str(label_path),
        "label_exists": False,
        "label_loadable": False,
        "label_keys": "",
        "points_count": 0,
        "offsets_shape": "",
        "scores_shape": "",
        "has_collision": False,
        "collision_shape": "",
        "total_candidates": 0,
        "score_positive_count": 0,
        "width_valid_count": 0,
        "collision_count": "",
        "valid_grasps": 0,
        "score_min": "",
        "score_max": "",
        "width_min": "",
        "width_max": "",
        "width_mean": "",
        "meets_min_valid_grasps": False,
        "training_candidate": False,
        "failure_reason": "",
    }
    failures = []

    row["mesh_exists"] = mesh_path.exists()
    if not row["mesh_exists"]:
        failures.append("missing_mesh")
    else:
        try:
            extents = _load_mesh_stats(mesh_path)
            row["mesh_loadable"] = True
            row["bbox_x"] = float(extents[0])
            row["bbox_y"] = float(extents[1])
            row["bbox_z"] = float(extents[2])
            row["bbox_suspicious"] = bool(
                np.any(extents < args.bbox_min) or np.any(extents > args.bbox_max)
            )
            if row["bbox_suspicious"]:
                failures.append("suspicious_bbox")
        except Exception as exc:
            failures.append("bad_mesh:{}".format(type(exc).__name__))

    row["label_exists"] = label_path.exists()
    if not row["label_exists"]:
        failures.append("missing_label")
    else:
        try:
            stats = _summarize_label(label_path, args)
            row["label_loadable"] = True
            row["label_keys"] = ",".join(stats["keys"])
            row["points_count"] = stats["points_count"]
            row["offsets_shape"] = "x".join(map(str, stats["offsets_shape"]))
            row["scores_shape"] = "x".join(map(str, stats["scores_shape"]))
            row["has_collision"] = stats["has_collision"]
            row["collision_shape"] = "x".join(map(str, stats["collision_shape"]))
            row["total_candidates"] = stats["total_candidates"]
            row["score_positive_count"] = stats["score_positive_count"]
            row["width_valid_count"] = stats["width_valid_count"]
            row["collision_count"] = stats["collision_count"]
            row["valid_grasps"] = stats["valid_grasps"]
            row["score_min"] = stats["score_min"]
            row["score_max"] = stats["score_max"]
            row["width_min"] = stats["width_min"]
            row["width_max"] = stats["width_max"]
            row["width_mean"] = stats["width_mean"]
            row["meets_min_valid_grasps"] = (
                stats["valid_grasps"] >= args.min_valid_grasps
            )
            if not row["meets_min_valid_grasps"]:
                failures.append("too_few_valid_grasps")
            if not row["has_collision"] and not args.ignore_collision:
                failures.append("missing_object_collision")
        except Exception as exc:
            failures.append("bad_label:{}".format(type(exc).__name__))

    row["training_candidate"] = bool(
        row["mesh_exists"]
        and row["mesh_loadable"]
        and row["label_exists"]
        and row["label_loadable"]
        and row["meets_min_valid_grasps"]
    )
    row["failure_reason"] = ";".join(failures)
    return row


def _discover_object_ids(raw_root):
    model_ids = {
        path.name
        for path in (raw_root / "models").glob("*")
        if path.is_dir() and path.name.isdigit()
    }
    label_ids = {
        path.name.split("_")[0]
        for path in (raw_root / "grasp_label").glob("*_labels.npz")
    }
    return sorted(model_ids | label_ids)


def _write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "object_id",
        "training_candidate",
        "failure_reason",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows):
    summary = {
        "total_objects": len(rows),
        "mesh_exists": sum(bool(row["mesh_exists"]) for row in rows),
        "mesh_loadable": sum(bool(row["mesh_loadable"]) for row in rows),
        "label_exists": sum(bool(row["label_exists"]) for row in rows),
        "label_loadable": sum(bool(row["label_loadable"]) for row in rows),
        "has_collision": sum(bool(row["has_collision"]) for row in rows),
        "training_candidates": sum(bool(row["training_candidate"]) for row in rows),
        "valid_grasps_total": int(sum(int(row["valid_grasps"]) for row in rows)),
        "failure_reasons": defaultdict(int),
    }
    for row in rows:
        for reason in str(row["failure_reason"]).split(";"):
            if reason:
                summary["failure_reasons"][reason] += 1
    summary["failure_reasons"] = dict(sorted(summary["failure_reasons"].items()))
    return summary


def _write_json(rows, summary, path, args):
    payload = {"args": vars(args), "summary": summary, "rows": rows}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def _write_report(rows, summary, path, args):
    lines = []
    lines.append("# GraspNet Asset Audit Report")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append("- graspnet_root: `{}`".format(args.graspnet_root))
    lines.append("- mesh_name: `{}`".format(args.mesh_name))
    lines.append("- min_valid_grasps: `{}`".format(args.min_valid_grasps))
    lines.append("- score_range: `(0, {}]`".format(args.score_max))
    lines.append("- width_range: `[{}, {}]`".format(args.width_min, args.width_max))
    lines.append("- ignore_collision: `{}`".format(args.ignore_collision))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in summary.items():
        if key != "failure_reasons":
            lines.append("- {}: `{}`".format(key, value))
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
    candidates = [row for row in rows if row["training_candidate"]]
    if not candidates:
        lines.append("No training candidates found.")
    else:
        lines.append("| object_id | valid_grasps | points | bbox | width range |")
        lines.append("| --- | ---: | ---: | --- | --- |")
        for row in candidates[:100]:
            bbox = "{}, {}, {}".format(row["bbox_x"], row["bbox_y"], row["bbox_z"])
            widths = "{} / {}".format(row["width_min"], row["width_max"])
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    row["object_id"],
                    row["valid_grasps"],
                    row["points_count"],
                    bbox,
                    widths,
                )
            )
    lines.append("")
    path.write_text("\n".join(lines))


def audit(args):
    raw_root = Path(args.graspnet_root).expanduser().resolve()
    args.graspnet_root = str(raw_root)
    out_dir = Path(args.out_dir).expanduser().resolve()

    object_ids = _discover_object_ids(raw_root)
    if args.max_objects > 0:
        object_ids = object_ids[: args.max_objects]

    rows = []
    for object_id in object_ids:
        rows.append(_audit_one_object(object_id, args))

    summary = _summarize(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, out_dir / "graspnet_asset_summary.csv")
    _write_json(rows, summary, out_dir / "graspnet_asset_summary.json", args)
    _write_report(rows, summary, out_dir / "graspnet_asset_report.md", args)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print("Report written to {}".format(out_dir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--graspnet_root", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--mesh_name", default="nontextured_simplified.ply")
    parser.add_argument("--min_valid_grasps", type=int, default=100)
    parser.add_argument("--width_min", type=float, default=0.01)
    parser.add_argument("--width_max", type=float, default=0.085)
    parser.add_argument("--score_max", type=float, default=0.4)
    parser.add_argument("--bbox_min", type=float, default=0.005)
    parser.add_argument("--bbox_max", type=float, default=0.5)
    parser.add_argument("--ignore_collision", action="store_true")
    parser.add_argument("--max_objects", type=int, default=-1)
    audit(parser.parse_args())
