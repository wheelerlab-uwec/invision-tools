#!/usr/bin/env python3
"""
Evaluate deduplication of overlap detections from paired cameras.

In the overlap region, the same physical organism is visible to both cameras.
This script:
  1. Applies coordinate transforms to both cameras
  2. Runs deduplication with configurable parameters
  3. Evaluates quality before/after using quantitative metrics
  4. Saves results to JSON for comparison

Usage:
    uv run python evaluate_dedup.py <experiment_dir> [options]

Examples:
    uv run python evaluate_dedup.py 20260312/20260312a01sao_20260312_130019 --pair top
    uv run python evaluate_dedup.py 20260312/20260312a01sao_20260312_130019 --pair bottom --radius 30
    uv run python evaluate_dedup.py 20260312/20260312a01sao_20260312_130019 --sweep
"""

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trackpy as tp
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------
# Camera / transform config (mirrors link_merge.py)
# ---------------------------------------------------------------------------

CAMERA_CONFIG = {
    "24568709": ("right", "top"),
    "24568744": ("left", "top"),
    "25112214": ("left", "bottom"),
    "25128038": ("right", "bottom"),
}

TRANSFORM_CONFIG = {
    ("24568709", "24568744"): {
        "right": {"flip_x": True,  "negate_x": False, "shift_x": -200, "shift_y": 100},
        "left":  {"flip_x": False, "negate_x": True,  "shift_x": 0,    "shift_y": 0},
    },
    ("25112214", "25128038"): {
        "right": {"flip_x": False, "negate_x": False, "shift_x": 0,    "shift_y": 20},
        "left":  {"flip_x": True,  "negate_x": True,  "shift_x": 800,  "shift_y": 100},
    },
}

# Camera pairs indexed by position
PAIRS = {
    "top":    ("24568709", "24568744"),   # right, left
    "bottom": ("25112214", "25128038"),   # left,  right
}

# Trackpy linking params for miracidia
LINK_SEARCH_RANGE = 45
LINK_MEMORY = 25
LINK_ADAPTIVE_STOP = 15
STUB_THRESHOLD = 200


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform_camera_data(df: pd.DataFrame, transforms: dict) -> pd.DataFrame:
    """Apply coordinate transforms and drop the per-camera particle column."""
    df = df.drop("particle", axis=1).copy()

    if transforms["flip_x"]:
        x_max, x_min = df["x"].max(), df["x"].min()
        df["x"] = x_max - df["x"] + x_min

    if transforms["negate_x"]:
        df["x"] = df["x"] * -1

    df["x"] = df["x"] + transforms["shift_x"]
    df["y"] = df["y"] + transforms["shift_y"]

    return df


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate_overlap(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    radius: float,
    overlap_xmin: float,
    overlap_xmax: float,
) -> pd.DataFrame:
    """
    Remove duplicate detections in the camera overlap zone.

    For each frame, any right-camera detection that has a left-camera detection
    within `radius` pixels (in the overlap zone) is considered a duplicate and
    dropped. Left-camera detections in the overlap are kept. Detections outside
    the overlap zone are never touched.

    Args:
        left_df:      Transformed detections from the left camera, with a
                      'source' column set to 'left'.
        right_df:     Transformed detections from the right camera, with a
                      'source' column set to 'right'.
        radius:       Maximum distance (px) for two detections to be considered
                      the same organism.
        overlap_xmin: Left edge of the overlap zone in transformed coordinates.
        overlap_xmax: Right edge of the overlap zone in transformed coordinates.

    Returns:
        Combined DataFrame with duplicate right-camera detections removed.
    """
    # Split each camera into overlap / non-overlap
    left_in  = left_df[(left_df["x"] >= overlap_xmin)  & (left_df["x"] <= overlap_xmax)]
    left_out = left_df[(left_df["x"] <  overlap_xmin)  | (left_df["x"] >  overlap_xmax)]

    right_in  = right_df[(right_df["x"] >= overlap_xmin) & (right_df["x"] <= overlap_xmax)]
    right_out = right_df[(right_df["x"] <  overlap_xmin) | (right_df["x"] >  overlap_xmax)]

    # For each frame, drop right detections that pair with a left detection
    keep_right_in_idx = []

    # Group both into per-frame dicts for fast lookup
    left_by_frame  = {f: g[["x", "y"]].values for f, g in left_in.groupby("frame")}
    right_by_frame = {f: (g, g[["x", "y"]].values) for f, g in right_in.groupby("frame")}

    for frame, (right_group, right_xy) in right_by_frame.items():
        if frame not in left_by_frame or len(left_by_frame[frame]) == 0:
            # No left detections in this frame's overlap — keep all right
            keep_right_in_idx.extend(right_group.index.tolist())
            continue

        left_xy = left_by_frame[frame]
        tree = cKDTree(left_xy)
        # For each right detection, find nearest left detection
        dists, _ = tree.query(right_xy, k=1)
        # Keep only right detections that have NO left neighbor within radius
        mask = dists > radius
        keep_right_in_idx.extend(right_group.index[mask].tolist())

    right_in_kept = right_in.loc[keep_right_in_idx]

    combined = pd.concat([left_out, left_in, right_out, right_in_kept], ignore_index=True)
    return combined


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def pairing_rate(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    radius: float,
    overlap_xmin: float,
    overlap_xmax: float,
) -> float:
    """
    Fraction of right-camera overlap detections that have a left-camera
    neighbor within `radius`. High = lots of duplicates; near 0 = clean.
    """
    left_in  = left_df[(left_df["x"] >= overlap_xmin) & (left_df["x"] <= overlap_xmax)]
    right_in = right_df[(right_df["x"] >= overlap_xmin) & (right_df["x"] <= overlap_xmax)]

    if len(right_in) == 0:
        return 0.0

    left_by_frame  = {f: g[["x", "y"]].values for f, g in left_in.groupby("frame")}
    right_by_frame = {f: (g, g[["x", "y"]].values) for f, g in right_in.groupby("frame")}

    paired = 0
    total  = 0

    for frame, (right_group, right_xy) in right_by_frame.items():
        total += len(right_group)
        if frame not in left_by_frame or len(left_by_frame[frame]) == 0:
            continue
        tree = cKDTree(left_by_frame[frame])
        dists, _ = tree.query(right_xy, k=1)
        paired += int((dists <= radius).sum())

    return paired / total if total > 0 else 0.0


def compute_track_metrics(linked: pd.DataFrame) -> dict:
    """Compute trackpy-based quality metrics from a linked DataFrame."""
    if len(linked) == 0 or "particle" not in linked.columns:
        return {}

    lengths = linked.groupby("particle").size()
    long_threshold = 200

    return {
        "num_tracks":        int(len(lengths)),
        "track_length_mean": float(lengths.mean()),
        "track_length_median": float(lengths.median()),
        "track_length_max":  int(lengths.max()),
        "long_track_ratio":  float((lengths >= long_threshold).mean()),
        "noise_ratio":       float((lengths < 5).mean()),
    }


def alignment_analysis(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    overlap_xmin: float,
    overlap_xmax: float,
    n_frames: int = 2000,
) -> dict:
    """
    Analyse the spatial offset between the two cameras in the overlap zone.

    For each frame that has detections from both cameras, finds the nearest
    left-camera neighbor for every right-camera detection. The resulting
    distance distribution characterises how well the transforms align the
    cameras and informs what dedup radius is sensible.

    Returns a dict with percentile distances, the fraction of detections
    within several candidate radii, and suggested dedup radii.
    """
    r_ov = right_df[
        (right_df["x"] >= overlap_xmin)
        & (right_df["x"] <= overlap_xmax)
        & (right_df["frame"] < n_frames)
    ]
    l_ov = left_df[
        (left_df["x"] >= overlap_xmin)
        & (left_df["x"] <= overlap_xmax)
        & (left_df["frame"] < n_frames)
    ]

    shared_frames = set(r_ov["frame"].unique()) & set(l_ov["frame"].unique())

    if not shared_frames:
        return {"error": "no shared frames in overlap zone"}

    l_by_frame = {f: g[["x", "y"]].values for f, g in l_ov.groupby("frame")}
    r_by_frame = {f: g[["x", "y"]].values for f, g in r_ov[r_ov["frame"].isin(shared_frames)].groupby("frame")}

    all_dists = []
    for frame, r_pts in r_by_frame.items():
        l_pts = l_by_frame.get(frame)
        if l_pts is None or len(l_pts) == 0:
            continue
        tree = cKDTree(l_pts)
        dists, _ = tree.query(r_pts, k=1)
        all_dists.extend(dists.tolist())

    all_dists = np.array(all_dists)
    percentiles = {f"p{p}": float(np.percentile(all_dists, p)) for p in [5, 10, 25, 50, 75, 90, 95, 99]}
    candidate_radii = [15, 30, 45, 60, 90, 120, 150, 200]
    fractions = {f"frac_lt_{r}px": float((all_dists < r).mean()) for r in candidate_radii}

    # Suggest radius that captures ~50% and ~80% of the closest pairs
    r50 = float(np.percentile(all_dists, 50))
    r80 = float(np.percentile(all_dists, 80))

    return {
        "n_shared_frames": len(shared_frames),
        "n_distances": len(all_dists),
        "overlap_width_px": round(overlap_xmax - overlap_xmin, 1),
        **percentiles,
        **fractions,
        "suggested_radius_50pct": round(r50, 1),
        "suggested_radius_80pct": round(r80, 1),
    }


def overlap_density_ratio(
    df: pd.DataFrame,
    overlap_xmin: float,
    overlap_xmax: float,
    n_frames: int = 1000,
) -> float:
    """
    Ratio of (detections/frame in overlap) to (detections/frame outside overlap).

    Before deduplication this will be > 1 because the overlap has double
    coverage. After good deduplication it should approach 1.0.
    """
    sample = df[df["frame"] < n_frames]
    in_ov  = sample[(sample["x"] >= overlap_xmin) & (sample["x"] <= overlap_xmax)]
    out_ov = sample[(sample["x"] <  overlap_xmin) | (sample["x"] >  overlap_xmax)]

    ov_width  = overlap_xmax - overlap_xmin
    tot_width = df["x"].max() - df["x"].min()
    out_width = tot_width - ov_width

    if out_width <= 0 or ov_width <= 0:
        return float("nan")

    ov_density  = len(in_ov)  / ov_width
    out_density = len(out_ov) / out_width

    return float(ov_density / out_density) if out_density > 0 else float("nan")


# ---------------------------------------------------------------------------
# Load and prepare a camera pair
# ---------------------------------------------------------------------------

def load_pair(base_dir: str, experiment_name: str, pair: str):
    """
    Load both cameras for a pair ('top' or 'bottom'), apply transforms,
    tag with source, and return (left_df, right_df, camera_pair_key,
    overlap_xmin, overlap_xmax).
    """
    right_cam, left_cam = PAIRS[pair]
    transforms = TRANSFORM_CONFIG[tuple(sorted([right_cam, left_cam]))]
    side_r, _ = CAMERA_CONFIG[right_cam]
    side_l, _ = CAMERA_CONFIG[left_cam]

    def feather_path(cam):
        return os.path.join(
            base_dir,
            f"{experiment_name}.{cam}",
            f"{experiment_name}_tracks.feather",
        )

    left_raw  = pd.read_feather(feather_path(left_cam))
    right_raw = pd.read_feather(feather_path(right_cam))

    left_t  = transform_camera_data(left_raw,  transforms[side_l])
    right_t = transform_camera_data(right_raw, transforms[side_r])

    left_t["source"]  = "left"
    right_t["source"] = "right"

    # Overlap = intersection of x ranges
    overlap_xmin = float(max(left_t["x"].min(),  right_t["x"].min()))
    overlap_xmax = float(min(left_t["x"].max(),  right_t["x"].max()))

    print(f"  {pair} pair overlap zone: x ∈ [{overlap_xmin:.1f}, {overlap_xmax:.1f}]  "
          f"({overlap_xmax - overlap_xmin:.0f} px wide)")

    return left_t, right_t, overlap_xmin, overlap_xmax


# ---------------------------------------------------------------------------
# Single evaluation run
# ---------------------------------------------------------------------------

def evaluate(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    overlap_xmin: float,
    overlap_xmax: float,
    radius: float,
    link: bool = True,
    n_link_frames: int = 2000,
) -> dict:
    """
    Run deduplication with `radius` and return a metrics dict.

    Args:
        left_df, right_df:   Transformed + source-tagged DataFrames.
        overlap_xmin/xmax:   Overlap zone boundaries.
        radius:              Dedup matching radius in pixels.
        link:                Whether to run tp.link for track metrics.
        n_link_frames:       How many frames to link (subset for speed).

    Returns:
        dict with keys: radius, pairing_rate_before, pairing_rate_after,
        density_ratio_before, density_ratio_after, removed_count,
        removal_fraction, and (if link=True) track_* metrics.
    """
    combined_before = pd.concat([left_df, right_df], ignore_index=True)

    pr_before = pairing_rate(left_df, right_df, radius, overlap_xmin, overlap_xmax)
    dr_before = overlap_density_ratio(combined_before, overlap_xmin, overlap_xmax)

    combined_after = deduplicate_overlap(
        left_df, right_df, radius, overlap_xmin, overlap_xmax
    )

    # Recompute pairing rate on deduplicated data
    after_left  = combined_after[combined_after["source"] == "left"]
    after_right = combined_after[combined_after["source"] == "right"]
    pr_after = pairing_rate(after_left, after_right, radius, overlap_xmin, overlap_xmax)
    dr_after = overlap_density_ratio(combined_after, overlap_xmin, overlap_xmax)

    removed = len(combined_before) - len(combined_after)

    metrics = {
        "radius":               radius,
        "pairing_rate_before":  round(pr_before, 4),
        "pairing_rate_after":   round(pr_after, 4),
        "density_ratio_before": round(dr_before, 4),
        "density_ratio_after":  round(dr_after, 4),
        "n_before":             len(combined_before),
        "n_after":              len(combined_after),
        "removed_count":        removed,
        "removal_fraction":     round(removed / len(combined_before), 4),
    }

    if link:
        print(f"    Linking {n_link_frames} frames (radius={radius})...")
        subset = combined_after[combined_after["frame"] < n_link_frames].drop(
            "source", axis=1
        )
        linked = tp.link(
            subset,
            search_range=LINK_SEARCH_RANGE,
            memory=LINK_MEMORY,
            adaptive_stop=LINK_ADAPTIVE_STOP,
        )
        tm = compute_track_metrics(linked)
        metrics.update({f"track_{k}": v for k, v in tm.items()})

        # Baseline (no dedup) track metrics
        subset_raw = combined_before[combined_before["frame"] < n_link_frames].drop(
            "source", axis=1
        )
        linked_raw = tp.link(
            subset_raw,
            search_range=LINK_SEARCH_RANGE,
            memory=LINK_MEMORY,
            adaptive_stop=LINK_ADAPTIVE_STOP,
        )
        tm_raw = compute_track_metrics(linked_raw)
        metrics.update({f"baseline_track_{k}": v for k, v in tm_raw.items()})

    return metrics


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_sweep_results(results: list[dict], output_path: str, pair: str):
    """Plot key metrics vs. dedup radius from a parameter sweep."""
    radii    = [r["radius"] for r in results]
    pr_after = [r["pairing_rate_after"] for r in results]
    dr_after = [r["density_ratio_after"] for r in results]
    removed  = [r["removal_fraction"] for r in results]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle(f"Deduplication sweep — {pair} pair")

    axes[0].plot(radii, pr_after, "o-")
    axes[0].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[0].set_xlabel("Dedup radius (px)")
    axes[0].set_ylabel("Pairing rate after dedup")
    axes[0].set_title("Residual duplicate rate\n(lower = cleaner)")

    axes[1].plot(radii, dr_after, "o-", color="tab:orange")
    axes[1].axhline(1.0, color="gray", linestyle="--", alpha=0.5, label="ideal = 1.0")
    axes[1].set_xlabel("Dedup radius (px)")
    axes[1].set_ylabel("Overlap density ratio")
    axes[1].set_title("Detection density: overlap / outside\n(closer to 1 = better)")
    axes[1].legend()

    axes[2].plot(radii, removed, "o-", color="tab:red")
    axes[2].set_xlabel("Dedup radius (px)")
    axes[2].set_ylabel("Fraction removed")
    axes[2].set_title("Detections removed\n(sanity check — shouldn't be huge)")

    plt.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  Saved sweep plot: {output_path}")


def plot_spatial_before_after(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    combined_after: pd.DataFrame,
    overlap_xmin: float,
    overlap_xmax: float,
    output_path: str,
    pair: str,
    n_frames: int = 200,
):
    """Scatter plot of detections before/after dedup in the overlap zone."""
    left_sample  = left_df[left_df["frame"] < n_frames]
    right_sample = right_df[right_df["frame"] < n_frames]
    after_sample = combined_after[combined_after["frame"] < n_frames]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"Detections in overlap zone — {pair} pair (first {n_frames} frames)")

    for ax, (df_l, df_r, title) in zip(
        axes,
        [
            (left_sample, right_sample, "Before deduplication"),
            (
                after_sample[after_sample["source"] == "left"],
                after_sample[after_sample["source"] == "right"],
                "After deduplication",
            ),
        ],
    ):
        in_l = df_l[(df_l["x"] >= overlap_xmin) & (df_l["x"] <= overlap_xmax)]
        in_r = df_r[(df_r["x"] >= overlap_xmin) & (df_r["x"] <= overlap_xmax)]
        ax.scatter(in_l["x"], in_l["y"], s=2, alpha=0.4, label=f"left ({len(in_l)})", color="tab:blue")
        ax.scatter(in_r["x"], in_r["y"], s=2, alpha=0.4, label=f"right ({len(in_r)})", color="tab:orange")
        ax.axvline(overlap_xmin, color="gray", linestyle="--", alpha=0.6)
        ax.axvline(overlap_xmax, color="gray", linestyle="--", alpha=0.6)
        ax.set_title(title)
        ax.set_xlabel("x (transformed px)")
        ax.set_ylabel("y (transformed px)")
        ax.legend(markerscale=4)

    plt.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  Saved spatial plot: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Evaluate camera overlap deduplication")
    parser.add_argument(
        "experiment_dir",
        help="Path to experiment base directory (e.g. 20260312/20260312a01sao_20260312_130019)",
    )
    parser.add_argument(
        "--pair",
        choices=["top", "bottom", "both"],
        default="both",
        help="Which camera pair to process (default: both)",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=30.0,
        help="Dedup matching radius in pixels (default: 30)",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Sweep over a range of radii and report metrics for each",
    )
    parser.add_argument(
        "--sweep-radii",
        nargs="+",
        type=float,
        default=[15, 30, 45, 60, 90, 120, 150, 200, 300],
        help="Radii to test in sweep mode",
    )
    parser.add_argument(
        "--no-link",
        action="store_true",
        help="Skip tp.link (faster; omits track quality metrics)",
    )
    parser.add_argument(
        "--link-frames",
        type=int,
        default=2000,
        help="Number of frames to use for tp.link evaluation (default: 2000)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for results JSON and plots (default: experiment_dir)",
    )
    args = parser.parse_args()

    exp_dir  = args.experiment_dir
    exp_name = Path(exp_dir).name
    out_dir  = args.output_dir or exp_dir
    os.makedirs(out_dir, exist_ok=True)

    # Find the base dir (parent of experiment dir)
    base_dir = str(Path(exp_dir).parent)

    pairs_to_run = ["top", "bottom"] if args.pair == "both" else [args.pair]

    for pair in pairs_to_run:
        print(f"\n{'='*60}")
        print(f"Camera pair: {pair}")
        print(f"{'='*60}")

        left_df, right_df, overlap_xmin, overlap_xmax = load_pair(
            base_dir, exp_name, pair
        )

        # Always run alignment analysis first — it informs the right radius range
        print("  Running alignment analysis...")
        align = alignment_analysis(left_df, right_df, overlap_xmin, overlap_xmax)
        align_path = os.path.join(out_dir, f"alignment_{pair}.json")
        with open(align_path, "w") as f:
            json.dump(align, f, indent=2)
        print(f"  Alignment analysis saved: {align_path}")
        print(f"  Nearest-neighbour distances (right→left in overlap, first 2000 frames):")
        for k in ["p5", "p25", "p50", "p75", "p90", "p95"]:
            print(f"    {k}: {align.get(k, 'N/A'):.1f}px")
        print(f"  Fraction within candidate radii:")
        for r in [30, 60, 120, 200]:
            key = f"frac_lt_{r}px"
            print(f"    < {r}px: {align.get(key, 0):.3f}")
        print(f"  Suggested dedup radius (50th pct): {align.get('suggested_radius_50pct', 'N/A')}px")
        print(f"  Suggested dedup radius (80th pct): {align.get('suggested_radius_80pct', 'N/A')}px")

        if args.sweep:
            print(f"  Sweeping radii: {args.sweep_radii}")
            all_results = []
            for r in args.sweep_radii:
                print(f"  radius={r}px")
                m = evaluate(
                    left_df, right_df, overlap_xmin, overlap_xmax,
                    radius=r,
                    link=(not args.no_link),
                    n_link_frames=args.link_frames,
                )
                all_results.append(m)
                print(f"    pairing_rate: {m['pairing_rate_before']:.3f} → {m['pairing_rate_after']:.3f}  "
                      f"density_ratio: {m['density_ratio_before']:.3f} → {m['density_ratio_after']:.3f}  "
                      f"removed: {m['removal_fraction']:.3f}")

            out_json = os.path.join(out_dir, f"dedup_sweep_{pair}.json")
            with open(out_json, "w") as f:
                json.dump(all_results, f, indent=2)
            print(f"  Saved: {out_json}")

            plot_sweep_results(
                all_results,
                os.path.join(out_dir, f"dedup_sweep_{pair}.pdf"),
                pair,
            )

        else:
            print(f"  radius={args.radius}px")
            m = evaluate(
                left_df, right_df, overlap_xmin, overlap_xmax,
                radius=args.radius,
                link=(not args.no_link),
                n_link_frames=args.link_frames,
            )
            print(f"\n  Results:")
            for k, v in m.items():
                print(f"    {k}: {v}")

            out_json = os.path.join(out_dir, f"dedup_r{int(args.radius)}_{pair}.json")
            with open(out_json, "w") as f:
                json.dump(m, f, indent=2)
            print(f"\n  Saved: {out_json}")

            # Spatial before/after plot
            combined_after = deduplicate_overlap(
                left_df, right_df, args.radius, overlap_xmin, overlap_xmax
            )
            plot_spatial_before_after(
                left_df, right_df, combined_after,
                overlap_xmin, overlap_xmax,
                os.path.join(out_dir, f"dedup_spatial_r{int(args.radius)}_{pair}.pdf"),
                pair,
            )


if __name__ == "__main__":
    main()
