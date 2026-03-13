#!/usr/bin/env python3
"""
Link and merge tracking data from left and right cameras.

Usage:
    python link_merge.py <date_or_experiment> [options]

Examples:
    # Process all experiments for a date
    python link_merge.py 20260108

    # Process a specific experiment
    python link_merge.py 20260108a01bas_20260108_125709

    # Specify base directory
    python link_merge.py 20260108 --base-dir /path/to/data
"""

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import trackpy as tp
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree


# Camera configuration: maps camera numbers to their side and position
# Format: camera_number: (side, position)
# side: 'left' or 'right'
# position: 'top' or 'bottom'
CAMERA_CONFIG = {
    "24568709": ("right", "top"),  # Camera 09 - right top
    "24568744": ("left", "top"),  # Camera 44 - left top
    "25112214": ("left", "bottom"),  # Camera 14 - left bottom
    "25128038": ("right", "bottom"),  # Camera 38 - right bottom
}

# Default deduplication radius (pixels, in transformed coordinate space).
# Based on empirical alignment analysis: the bottom pair (wider overlap) benefits
# from a larger radius (~200-300px); the top pair (narrow 181px overlap) is less
# sensitive. Set to None to disable deduplication.
DEFAULT_DEDUP_RADIUS = 200

# Transformation parameters for each camera pair
# Format: (top_cameras, bottom_cameras): transformation_config
TRANSFORM_CONFIG = {
    ("24568709", "24568744"): {  # Top cameras (09/44)
        "right": {
            "flip_x": True,
            "negate_x": False,
            "shift_x": -200,
            "shift_y": 100,
        },
        "left": {
            "flip_x": False,
            "negate_x": True,
            "shift_x": 0,
            "shift_y": 0,
        },
    },
    ("25112214", "25128038"): {  # Bottom cameras (14/38) - inverted mounting from top
        "right": {
            "flip_x": False,
            "negate_x": False,
            "shift_x": 0,
            "shift_y": 20,
        },
        "left": {
            "flip_x": True,
            "negate_x": True,
            "shift_x": 800,
            "shift_y": 100,
        },
    },
}


def find_experiments_by_date(base_dir, date):
    """Find all experiments for a given date."""
    pattern = os.path.join(base_dir, f"{date}*")
    all_dirs = glob.glob(pattern)

    # Find experiment names (directories with camera numbers)
    experiments = set()
    for d in all_dirs:
        if os.path.isdir(d):
            dir_name = os.path.basename(d)
            # Check if it's a camera directory (ends with camera number)
            if "." in dir_name:
                parts = dir_name.rsplit(".", 1)
                if parts[1] in CAMERA_CONFIG:
                    experiments.add(parts[0])

    return sorted(list(experiments))


def find_camera_dirs(base_dir, experiment_name):
    """Find all camera directories for a given experiment."""
    pattern = os.path.join(base_dir, f"{experiment_name}.*")
    dirs = glob.glob(pattern)

    camera_dirs = {}
    for d in dirs:
        if os.path.isdir(d):
            # Extract camera number from directory name
            camera_num = d.split(".")[-1]
            if camera_num in CAMERA_CONFIG:
                camera_dirs[camera_num] = d

    return camera_dirs


def transform_camera_data(df, transforms, source_label=None):
    """Apply transformations to camera data.

    Args:
        df:           Raw per-camera feather DataFrame.
        transforms:   Dict with flip_x, negate_x, shift_x, shift_y keys.
        source_label: Optional string tag (e.g. 'left' / 'right') added as a
                      'source' column so detections can be identified after
                      concatenation. Stripped before tp.link is called.
    """
    df = df.drop("particle", axis=1)

    if transforms["flip_x"]:
        max_x = max(df["x"])
        min_x = min(df["x"])
        df["x"] = max_x - df["x"] + min_x

    if transforms["negate_x"]:
        df["x"] = df["x"] * -1

    df["x"] = df["x"] + transforms["shift_x"]
    df["y"] = df["y"] + transforms["shift_y"]

    if source_label is not None:
        df["source"] = source_label

    return df


def deduplicate_overlap(left_df, right_df, radius):
    """Remove duplicate detections in the camera overlap zone.

    The overlap zone is defined as the intersection of the two cameras'
    x-coordinate ranges after transformation. For each frame, any right-camera
    detection that has a left-camera detection within `radius` pixels in the
    overlap zone is dropped (the left-camera detection is kept).

    Args:
        left_df:  Transformed left-camera DataFrame with a 'source' column.
        right_df: Transformed right-camera DataFrame with a 'source' column.
        radius:   Maximum distance (px) for two detections to be considered
                  the same organism. Use DEFAULT_DEDUP_RADIUS if unsure.

    Returns:
        Combined DataFrame with duplicate right-camera detections removed and
        the 'source' column stripped (ready for tp.link).
    """
    overlap_xmin = float(max(left_df["x"].min(), right_df["x"].min()))
    overlap_xmax = float(min(left_df["x"].max(), right_df["x"].max()))

    left_in  = left_df[(left_df["x"] >= overlap_xmin)  & (left_df["x"] <= overlap_xmax)]
    left_out = left_df[(left_df["x"] <  overlap_xmin)  | (left_df["x"] >  overlap_xmax)]
    right_in  = right_df[(right_df["x"] >= overlap_xmin) & (right_df["x"] <= overlap_xmax)]
    right_out = right_df[(right_df["x"] <  overlap_xmin) | (right_df["x"] >  overlap_xmax)]

    # Build per-frame lookup for left detections in the overlap zone
    left_by_frame = {f: g[["x", "y"]].values for f, g in left_in.groupby("frame")}

    keep_right_idx = []
    for frame, right_group in right_in.groupby("frame"):
        r_xy = right_group[["x", "y"]].values
        if frame not in left_by_frame or len(left_by_frame[frame]) == 0:
            keep_right_idx.extend(right_group.index.tolist())
            continue
        tree = cKDTree(left_by_frame[frame])
        dists, _ = tree.query(r_xy, k=1)
        keep_right_idx.extend(right_group.index[dists > radius].tolist())

    right_in_kept = right_in.loc[keep_right_idx]
    n_removed = len(right_in) - len(right_in_kept)
    if n_removed > 0:
        print(f"  Deduplication: removed {n_removed} overlap detections "
              f"({100 * n_removed / (len(left_in) + len(right_in)):.1f}% of overlap zone, "
              f"overlap x ∈ [{overlap_xmin:.0f}, {overlap_xmax:.0f}])")

    combined = pd.concat([left_out, left_in, right_out, right_in_kept], ignore_index=True)
    return combined.drop(columns=["source"])


def load_affine_calibration(cal_dir: str | None, pair: str) -> dict | None:
    """
    Load a pre-computed affine calibration for a camera pair.

    Calibrations are produced by calibrate_transform.py and stored as:
        <cal_dir>/affine_calibration_<pair>.json

    Returns the calibration dict, or None if no file is found.
    """
    if cal_dir is None:
        return None
    path = os.path.join(cal_dir, f"affine_calibration_{pair}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        cal = json.load(f)
    print(f"  Loaded affine calibration ({pair}): "
          f"residual {cal.get('residual_before_p50', '?')} → "
          f"{cal.get('residual_after_p50', '?')} px (p50)")
    return cal


def apply_affine_calibration(df: pd.DataFrame, calibration: dict) -> pd.DataFrame:
    """
    Apply the stored affine correction to the right-camera DataFrame.

    The affine matrix M (3×2) maps right-camera coordinates (after coarse
    transform) to left-camera coordinates:
        [x', y'] = [x, y, 1] @ M

    Args:
        df:           Right-camera DataFrame after coarse transform.
        calibration:  Dict loaded from the JSON calibration file.

    Returns:
        DataFrame with corrected x, y coordinates.
    """
    M = np.array(calibration["affine_matrix"])  # (3, 2)
    xy = df[["x", "y"]].values
    xy_h = np.column_stack([xy, np.ones(len(xy))])
    df = df.copy()
    df[["x", "y"]] = xy_h @ M
    return df


def process_camera_pair(left_path, right_path, camera_pair, output_prefix, position, **kwargs):
    """Process a pair of left/right cameras."""
    print(f"\nProcessing {position} cameras...")
    print(f"  Left:  {left_path}")
    print(f"  Right: {right_path}")

    # Load data
    left_df = pd.read_feather(left_path)
    right_df = pd.read_feather(right_path)

    # Get transformation config for this camera pair
    transforms = TRANSFORM_CONFIG[camera_pair]

    # Apply transformations (tag with source for deduplication)
    left_df  = transform_camera_data(left_df,  transforms["left"],  source_label="left")
    right_df = transform_camera_data(right_df, transforms["right"], source_label="right")

    # Apply affine calibration to right camera if available
    calibration = kwargs.get("calibration")
    if calibration is not None:
        right_df = apply_affine_calibration(right_df, calibration)

    # Deduplicate overlap zone, then combine
    dedup_radius = kwargs.get("dedup_radius", DEFAULT_DEDUP_RADIUS)
    if dedup_radius is not None:
        combined = deduplicate_overlap(left_df, right_df, radius=dedup_radius)
    else:
        combined = pd.concat([left_df, right_df]).drop(columns=["source"])

    # Link trajectories
    search_range = 45
    memory = 25
    adaptive_stop = 15

    print(f"  Linking trajectories (search_range={search_range}, memory={memory})...")
    linked = tp.link(
        combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
    )

    # Save results
    feather_path = f"{output_prefix}_{position}_tracks.feather"
    linked.to_feather(feather_path)
    print(f"  Saved: {feather_path}")

    # Create and save plot
    pdf_path = f"{output_prefix}_{position}_tracks.pdf"
    fig = plt.figure()
    ax = plt.gca()
    filtered = tp.filter_stubs(linked, 200)
    tp.plot_traj(filtered, ax=ax)
    fig.savefig(pdf_path)
    plt.close(fig)
    print(f"  Saved: {pdf_path}")

    return linked


def process_experiment(base_dir, experiment_name, output_dir=None, **kwargs):
    """Process a single experiment."""
    print(f"\n{'='*80}")
    print(f"Processing experiment: {experiment_name}")
    print(f"{'='*80}")

    # Find camera directories
    camera_dirs = find_camera_dirs(base_dir, experiment_name)

    if not camera_dirs:
        print(f"Error: No camera directories found for experiment '{experiment_name}'")
        return False

    print(f"Found {len(camera_dirs)} camera directories:")
    for cam_num, cam_dir in sorted(camera_dirs.items()):
        side, position = CAMERA_CONFIG[cam_num]
        print(f"  {cam_num}: {side} {position}")

    # Group cameras by position
    top_cameras = {}
    bottom_cameras = {}

    for cam_num, cam_dir in camera_dirs.items():
        side, position = CAMERA_CONFIG[cam_num]
        track_file = os.path.join(cam_dir, f"{experiment_name}_tracks.feather")

        if not os.path.exists(track_file):
            print(f"Warning: Track file not found: {track_file}")
            continue

        if position == "top":
            top_cameras[side] = (cam_num, track_file)
        else:
            bottom_cameras[side] = (cam_num, track_file)

    # Determine output directory
    if output_dir:
        exp_output_dir = output_dir
    else:
        # Extract date from experiment name (e.g., 20260108a01bas... -> 20260108)
        date = experiment_name[:8]
        exp_output_dir = os.path.join(base_dir, date)

    os.makedirs(exp_output_dir, exist_ok=True)
    output_prefix = os.path.join(exp_output_dir, experiment_name)

    print(f"\nOutput directory: {exp_output_dir}")

    dedup_radius = kwargs.get("dedup_radius", DEFAULT_DEDUP_RADIUS)
    cal_dir = kwargs.get("cal_dir")

    # Process top cameras
    if len(top_cameras) == 2:
        left_cam, left_path = top_cameras["left"]
        right_cam, right_path = top_cameras["right"]
        camera_pair = tuple(sorted([left_cam, right_cam]))
        process_camera_pair(left_path, right_path, camera_pair, output_prefix, "top",
                            dedup_radius=dedup_radius,
                            calibration=load_affine_calibration(cal_dir, "top"))
    else:
        print(f"Warning: Expected 2 top cameras, found {len(top_cameras)}")

    # Process bottom cameras
    if len(bottom_cameras) == 2:
        left_cam, left_path = bottom_cameras["left"]
        right_cam, right_path = bottom_cameras["right"]
        camera_pair = tuple(sorted([left_cam, right_cam]))
        process_camera_pair(left_path, right_path, camera_pair, output_prefix, "bottom",
                            dedup_radius=dedup_radius,
                            calibration=load_affine_calibration(cal_dir, "bottom"))
    else:
        print(f"Warning: Expected 2 bottom cameras, found {len(bottom_cameras)}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Link and merge tracking data from left and right cameras"
    )
    parser.add_argument(
        "date_or_experiment",
        help="Date (YYYYMMDD) to process all experiments, or full experiment name (e.g., 20260108a01bas_20260108_125709)",
    )
    parser.add_argument(
        "--base-dir",
        default=os.getcwd(),
        help="Base directory containing camera data (default: current working directory)",
    )
    parser.add_argument(
        "--output-dir", help="Output directory (default: date folder in base_dir)"
    )
    parser.add_argument(
        "--dedup-radius",
        type=float,
        default=DEFAULT_DEDUP_RADIUS,
        help=(
            f"Overlap deduplication radius in pixels (default: {DEFAULT_DEDUP_RADIUS}). "
            "Set to 0 to disable deduplication. See evaluate_dedup.py for sweep analysis."
        ),
    )
    parser.add_argument(
        "--cal-dir",
        default=None,
        help=(
            "Directory containing affine_calibration_top.json and/or "
            "affine_calibration_bottom.json (produced by calibrate_transform.py). "
            "If not set, the script looks for a 'calibration/' subdirectory "
            "inside the base data directory."
        ),
    )

    args = parser.parse_args()

    print(f"Searching in: {args.base_dir}")

    # Determine if input is a date or full experiment name
    input_str = args.date_or_experiment

    # If input is 8 characters and all digits, treat as date
    if len(input_str) == 8 and input_str.isdigit():
        # Find all experiments for this date
        experiments = find_experiments_by_date(args.base_dir, input_str)

        if not experiments:
            print(f"Error: No experiments found for date '{input_str}'")
            sys.exit(1)

        print(f"\nFound {len(experiments)} experiment(s) for date {input_str}:")
        for exp in experiments:
            print(f"  - {exp}")

        dedup_radius = args.dedup_radius if args.dedup_radius > 0 else None
        cal_dir = args.cal_dir or os.path.join(args.base_dir, "calibration")

        # Process each experiment
        success_count = 0
        for exp in experiments:
            if process_experiment(args.base_dir, exp, args.output_dir,
                                  dedup_radius=dedup_radius, cal_dir=cal_dir):
                success_count += 1

        print(f"\n{'='*80}")
        print(
            f"Completed: {success_count}/{len(experiments)} experiment(s) processed successfully"
        )
        print(f"{'='*80}")

    else:
        # Treat as full experiment name
        dedup_radius = args.dedup_radius if args.dedup_radius > 0 else None
        cal_dir = args.cal_dir or os.path.join(args.base_dir, "calibration")
        if process_experiment(args.base_dir, input_str, args.output_dir,
                              dedup_radius=dedup_radius, cal_dir=cal_dir):
            print("\nDone!")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
