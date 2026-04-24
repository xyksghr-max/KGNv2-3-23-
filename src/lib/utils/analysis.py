import csv
import json
import os

import numpy as np


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def prepare_analysis_dirs(base_dir, save_kpt_vis=False):
    dirs = {
        "base": ensure_dir(base_dir),
        "images": ensure_dir(os.path.join(base_dir, "images")),
    }
    if save_kpt_vis:
        dirs["kpt_vis"] = ensure_dir(os.path.join(base_dir, "kpt_vis"))
    else:
        dirs["kpt_vis"] = None
    return dirs


def array_stats(values):
    arr = np.asarray(values, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p50": None,
            "p90": None,
            "max": None,
        }

    return {
        "count": int(arr.size),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "max": float(arr.max()),
    }


def to_serializable(obj):
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serializable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_serializable(data), f, indent=2, ensure_ascii=False)


def save_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def summarize_records(records, avg_spf):
    summary = {
        "num_images": len(records),
        "avg_time_spf": float(avg_spf),
        "avg_time_fps": float(1.0 / avg_spf) if avg_spf > 0 else None,
        "decoded_candidates_total": 0,
        "score_filtered_candidates_total": 0,
        "pnp_attempted_total": 0,
        "pnp_failed_total": 0,
        "scale_refine_failed_total": 0,
        "reproj_filtered_total": 0,
        "quality_filtered_total": 0,
        "accepted_candidates_total": 0,
        "images_with_any_prediction": 0,
        "images_with_any_eval_success": 0,
        "eval_successful_prediction_total": 0,
    }

    reproj_pool = []
    score_pool = []
    scale_pool = []
    confidence_pool = []
    quality_pool = []

    for record in records:
        summary["decoded_candidates_total"] += record.get("decoded_candidates", 0)
        summary["score_filtered_candidates_total"] += record.get("score_filtered_candidates", 0)
        summary["pnp_attempted_total"] += record.get("pnp_attempted", 0)
        summary["pnp_failed_total"] += record.get("pnp_failed", 0)
        summary["scale_refine_failed_total"] += record.get("scale_refine_failed", 0)
        summary["reproj_filtered_total"] += record.get("reproj_filtered", 0)
        summary["quality_filtered_total"] += record.get("quality_filtered", 0)
        summary["accepted_candidates_total"] += record.get("accepted_candidates", 0)
        summary["eval_successful_prediction_total"] += record.get("eval_successful_prediction_count", 0)

        if record.get("accepted_candidates", 0) > 0:
            summary["images_with_any_prediction"] += 1
        if record.get("eval_any_success", False):
            summary["images_with_any_eval_success"] += 1

        reproj_pool.extend(record.get("accepted_reprojection_errors", []))
        score_pool.extend(record.get("accepted_scores", []))
        scale_pool.extend(record.get("accepted_scales", []))
        confidence_pool.extend(record.get("accepted_confidences", []))
        quality_pool.extend(record.get("accepted_quality_scores", []))

    score_filtered_total = summary["score_filtered_candidates_total"]
    summary["accepted_ratio_vs_score_filtered"] = (
        float(summary["accepted_candidates_total"] / score_filtered_total)
        if score_filtered_total > 0 else None
    )
    summary["accepted_reprojection_error_stats"] = array_stats(reproj_pool)
    summary["accepted_score_stats"] = array_stats(score_pool)
    summary["accepted_scale_stats"] = array_stats(scale_pool)
    summary["accepted_confidence_stats"] = array_stats(confidence_pool)
    summary["accepted_quality_stats"] = array_stats(quality_pool)
    return summary


def classify_failure_reason(record):
    accepted_candidates = int(record.get("accepted_candidates", 0) or 0)
    eval_successful_prediction_count = int(record.get("eval_successful_prediction_count", 0) or 0)
    score_filtered_candidates = int(record.get("score_filtered_candidates", 0) or 0)
    pnp_attempted = int(record.get("pnp_attempted", 0) or 0)
    pnp_failed = int(record.get("pnp_failed", 0) or 0)
    scale_refine_failed = int(record.get("scale_refine_failed", 0) or 0)
    reproj_filtered = int(record.get("reproj_filtered", 0) or 0)
    pre_quality_candidates = int(record.get("pre_quality_candidates", 0) or 0)
    quality_filtered = int(record.get("quality_filtered", 0) or 0)

    if accepted_candidates <= 0:
        if score_filtered_candidates <= 0:
            return "no_score_pass"
        if pnp_attempted > 0 and pnp_failed >= pnp_attempted:
            return "all_pnp_fail"
        if scale_refine_failed > 0 and accepted_candidates <= 0:
            return "all_scale_refine_fail"
        if pre_quality_candidates > 0 and quality_filtered >= pre_quality_candidates:
            return "all_quality_filtered"
        if reproj_filtered > 0 and accepted_candidates <= 0:
            return "all_reproj_filtered"
        return "no_prediction_after_filter"

    if eval_successful_prediction_count > 0:
        return "has_eval_success"
    return "predicted_but_eval_failed"


def summarize_records_by_shape(records, avg_spf):
    grouped = {}
    for record in records:
        shapes = record.get("obj_types", [])
        if not shapes:
            shapes = ["unknown"]
        for shape in shapes:
            grouped.setdefault(shape, []).append(record)

    summaries = []
    for shape, shape_records in sorted(grouped.items()):
        shape_summary = summarize_records(shape_records, avg_spf)
        failure_reason_counts = {}
        for record in shape_records:
            failure_reason = record.get("failure_reason", "unknown")
            failure_reason_counts[failure_reason] = failure_reason_counts.get(failure_reason, 0) + 1
        shape_summary["shape"] = shape
        shape_summary["failure_reason_counts"] = failure_reason_counts
        summaries.append(shape_summary)
    return summaries
