#!/usr/bin/env python3
"""
Estimate the residual affine transform between paired cameras using shared tracks.

The existing TRANSFORM_CONFIG in link_merge.py provides a coarse alignment
(flip + negate + shift). Because camera mounts may have small rotational offsets
or scale differences, the residual misalignment can be 100-250 px in the overlap
zone. This script fits a 2D affine correction on top of those rough transforms
using organisms that are visible to both cameras simultaneously.

Algorithm
---------
1. Load per-camera feather files (which carry per-camera particle IDs from
   single-camera linking).
2. Apply the existing coarse transforms to put both cameras in a shared space.
3. In the overlap zone, vote on track correspondences: for each frame, match
   right-camera detections to their nearest left-camera detection within a
   generous radius and accumulate per (right_particle, left_particle) votes.
4. Greedy one-to-one matching: select the highest-vote pair, remove both
   particles, repeat until no pairs have enough votes.
5. Collect point correspondences from matched track pairs.
6. Fit a 2D affine transform (6 DOF) with RANSAC for robustness to a small
   number of bad matches.
7. Report quality metrics and save the calibration to JSON.

The resulting calibration file is loaded by link_merge.py to correct the
right-camera coordinates before concatenation and linking.

Usage
-----
    # Calibrate from one experiment (all pairs)
    uv run python calibrate_transform.py 20260312/20260312a01sao_20260312_130019

    # Specific pair
    uv run python calibrate_transform.py 20260312/20260312a01sao_20260312_130019 --pair bottom

    # Use multiple experiments to get more correspondences (recommended)
    uv run python calibrate_transform.py 20260312/20260312a01sao_20260312_130019 \\
        --extra-experiments 20260315/20260315a01sao_... --pair both

    # Output calibration files to a specific directory
    uv run python calibrate_transform.py 20260312/20260312a01sao_20260312_130019 \\
        --output-dir calibration/
"""

import argparse
import json
import os
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------
# Coarse transform config (mirrors link_merge.py)
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

PAIRS = {
    "top":    ("24568709", "24568744"),
    "bottom": ("25112214", "25128038"),
}


# ---------------------------------------------------------------------------
# Coarse transform application
# ---------------------------------------------------------------------------

def apply_coarse_transform(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Apply the flip/negate/shift coarse transform. Keeps 'particle' column."""
    df = df.copy()
    if t["flip_x"]:
        df["x"] = df["x"].max() - df["x"] + df["x"].min()
    if t["negate_x"]:
        df["x"] = df["x"] * -1
    df["x"] += t["shift_x"]
    df["y"] += t["shift_y"]
    return df


# ---------------------------------------------------------------------------
# Track matching
# ---------------------------------------------------------------------------

def vote_for_track_matches(
    l_ov: pd.DataFrame,
    r_ov: pd.DataFrame,
    radius: float,
) -> dict:
    """
    For each frame where both cameras have detections in the overlap zone,
    match each right detection to its nearest left detection within `radius`.
    Accumulate votes for each (right_particle, left_particle) pair.

    Returns dict mapping (right_particle, left_particle) -> vote_count.
    """
    l_by_frame = {f: g for f, g in l_ov.groupby("frame")}
    votes: dict = {}

    for frame, r_frame in r_ov.groupby("frame"):
        if frame not in l_by_frame:
            continue
        l_frame = l_by_frame[frame]
        if len(l_frame) == 0:
            continue

        l_xy = l_frame[["x", "y"]].values
        r_xy = r_frame[["x", "y"]].values
        tree = cKDTree(l_xy)
        dists, idxs = tree.query(r_xy, k=1)

        for r_row, dist, l_idx in zip(r_frame.itertuples(), dists, idxs):
            if dist <= radius:
                key = (r_row.particle, l_frame.iloc[l_idx]["particle"])
                votes[key] = votes.get(key, 0) + 1

    return votes


def greedy_match_tracks(votes: dict, min_votes: int) -> list[tuple]:
    """
    Select a one-to-one matching by repeatedly taking the (right, left) pair
    with the most votes, then removing both particles from further consideration.

    Returns list of (right_particle, left_particle, vote_count) tuples.
    """
    sorted_pairs = sorted(votes.items(), key=lambda x: x[1], reverse=True)
    used_right: set = set()
    used_left:  set = set()
    matches = []

    for (rp, lp), count in sorted_pairs:
        if count < min_votes:
            break
        if rp in used_right or lp in used_left:
            continue
        matches.append((rp, lp, count))
        used_right.add(rp)
        used_left.add(lp)

    return matches


# ---------------------------------------------------------------------------
# Point correspondence collection
# ---------------------------------------------------------------------------

def collect_point_pairs(
    right_df: pd.DataFrame,
    left_df:  pd.DataFrame,
    matches:  list[tuple],
    overlap_xmin: float,
    overlap_xmax: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    For each matched (right_particle, left_particle) pair, collect the
    (right_xy, left_xy) position pairs over their shared frames.
    Only includes frames where both particles are in the overlap zone.

    Returns (right_pts, left_pts) as (N, 2) arrays.
    """
    r_by_particle = {p: g for p, g in right_df.groupby("particle")}
    l_by_particle = {p: g for p, g in left_df.groupby("particle")}

    right_pts, left_pts = [], []

    for rp, lp, _ in matches:
        r_track = r_by_particle.get(rp)
        l_track = l_by_particle.get(lp)
        if r_track is None or l_track is None:
            continue

        # Filter to overlap zone
        r_ov = r_track[(r_track["x"] >= overlap_xmin) & (r_track["x"] <= overlap_xmax)]
        l_ov = l_track[(l_track["x"] >= overlap_xmin) & (l_track["x"] <= overlap_xmax)]

        r_indexed = r_ov.set_index("frame")[["x", "y"]]
        l_indexed = l_ov.set_index("frame")[["x", "y"]]

        shared_frames = r_indexed.index.intersection(l_indexed.index)
        if len(shared_frames) == 0:
            continue

        right_pts.append(r_indexed.loc[shared_frames].values)
        left_pts.append(l_indexed.loc[shared_frames].values)

    if not right_pts:
        return np.empty((0, 2)), np.empty((0, 2))

    return np.vstack(right_pts), np.vstack(left_pts)


# ---------------------------------------------------------------------------
# Affine fitting with RANSAC
# ---------------------------------------------------------------------------

def fit_translation_robust(
    right_pts: np.ndarray,
    left_pts:  np.ndarray,
) -> np.ndarray:
    """
    Estimate a pure translation (tx, ty) as the robust median displacement.

    No RANSAC is needed — the median is inherently resistant to outliers.
    Appropriate when the overlap zone is too narrow to constrain rotation or scale.

    Returns a (3, 2) matrix compatible with apply_affine_calibration:
        M = [[1, 0],
             [0, 1],
             [tx, ty]]
    """
    delta = left_pts - right_pts
    tx = float(np.median(delta[:, 0]))
    ty = float(np.median(delta[:, 1]))
    return np.array([[1.0, 0.0], [0.0, 1.0], [tx, ty]])


def is_degenerate_transform(
    M: np.ndarray,
    max_scale_error: float = 0.30,
    max_rotation_deg: float = 20.0,
) -> tuple[bool, str]:
    """
    Sanity-check a fitted (3, 2) transform matrix.

    Cameras mounted on the same rig should have:
      - Scale near 1 (pixel sizes don't differ by >30 %)
      - Rotation < 20° (mounts aren't grossly misaligned)

    Returns (is_bad: bool, reason: str).
    """
    decomp = decompose_affine(M)
    sx, sy = decomp["scale_x"], decomp["scale_y"]
    rot = abs(decomp["rotation_deg"])
    lo, hi = 1 - max_scale_error, 1 + max_scale_error
    if not (lo <= sx <= hi):
        return True, "scale_x={:.3f} outside [{:.2f}, {:.2f}]".format(sx, lo, hi)
    if not (lo <= sy <= hi):
        return True, "scale_y={:.3f} outside [{:.2f}, {:.2f}]".format(sy, lo, hi)
    if rot > max_rotation_deg:
        return True, "rotation={:.1f}° > {:.0f}°".format(decomp["rotation_deg"], max_rotation_deg)
    return False, ""


def fit_affine_ransac(
    right_pts: np.ndarray,
    left_pts:  np.ndarray,
    n_iter:    int   = 2000,
    inlier_threshold: float = 40.0,
    seed:      int   = 42,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Fit a 2D affine transform from right_pts → left_pts using RANSAC.

    The transform is represented as a (3, 2) matrix M such that:
        left ≈ [right | 1] @ M

    i.e., for a single point:
        [x', y'] = [x, y, 1] @ M

    Args:
        right_pts:        (N, 2) array of right-camera points (coarse-transformed).
        left_pts:         (N, 2) array of left-camera points (coarse-transformed).
        n_iter:           Number of RANSAC iterations.
        inlier_threshold: Distance threshold (px) for a point to be an inlier.
        seed:             Random seed.

    Returns:
        M:               (3, 2) affine matrix — apply with `np.c_[pts, 1] @ M`
        inliers:         Boolean array of shape (N,) marking inlier pairs.
        residual_mean:   Mean residual distance (px) over inliers after final fit.
    """
    n = len(right_pts)
    if n < 3:
        raise ValueError(f"Need at least 3 point pairs, got {n}")

    rng = np.random.default_rng(seed)
    best_M = None
    best_inliers = np.zeros(n, dtype=bool)
    best_count = 0

    # Homogeneous right points
    R_h = np.column_stack([right_pts, np.ones(n)])

    for _ in range(n_iter):
        idx = rng.choice(n, 3, replace=False)
        A = R_h[idx]
        b = left_pts[idx]
        try:
            M_candidate = np.linalg.solve(A, b)   # exact 3-point fit
        except np.linalg.LinAlgError:
            continue

        residuals = np.linalg.norm(R_h @ M_candidate - left_pts, axis=1)
        inliers = residuals < inlier_threshold
        count = inliers.sum()

        if count > best_count:
            best_count = count
            best_inliers = inliers
            best_M = M_candidate

    # Refit on all inliers using least squares
    if best_count >= 3:
        M_final, _, _, _ = np.linalg.lstsq(
            R_h[best_inliers], left_pts[best_inliers], rcond=None
        )
    else:
        M_final = best_M

    residuals_final = np.linalg.norm(R_h @ M_final - left_pts, axis=1)
    inlier_residuals = residuals_final[best_inliers]
    residual_mean = float(inlier_residuals.mean()) if len(inlier_residuals) > 0 else float("nan")

    return M_final, best_inliers, residual_mean


def fit_similarity_ransac(
    right_pts: np.ndarray,
    left_pts:  np.ndarray,
    n_iter:    int   = 2000,
    inlier_threshold: float = 40.0,
    seed:      int   = 42,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Fit a 2D similarity transform (rotation + uniform scale + translation)
    from right_pts → left_pts using RANSAC.

        x' = a·x − b·y + tx
        y' = b·x + a·y + ty

    where a = s·cos(θ), b = s·sin(θ), s = scale, θ = rotation.

    This is more appropriate than a full affine transform when the overlap zone
    is narrow in x (< ~400 px), because the affine's independent x/y scale and
    shear parameters cannot be reliably constrained.

    The result is returned as a (3, 2) matrix M identical in layout to the
    affine matrix produced by fit_affine_ransac, so it is directly usable by
    apply_affine_calibration:

        M = [[a,  b],
             [−b, a],
             [tx, ty]]

        [x', y'] = [x, y, 1] @ M

    Minimum sample size is 2 points (4 equations, 4 unknowns).
    """
    n = len(right_pts)
    if n < 2:
        raise ValueError(f"Need at least 2 point pairs, got {n}")

    rng = np.random.default_rng(seed)
    best_M = None
    best_inliers = np.zeros(n, dtype=bool)
    best_count = 0

    R_h = np.column_stack([right_pts, np.ones(n)])

    def _build_system(pts_r: np.ndarray, pts_l: np.ndarray):
        """Build (2N, 4) linear system for [a, b, tx, ty]."""
        N = len(pts_r)
        A = np.zeros((2 * N, 4))
        bv = np.zeros(2 * N)
        rx, ry = pts_r[:, 0], pts_r[:, 1]
        lx, ly = pts_l[:, 0], pts_l[:, 1]
        A[0::2, 0] =  rx;  A[0::2, 1] = -ry;  A[0::2, 2] = 1
        A[1::2, 0] =  ry;  A[1::2, 1] =  rx;                  A[1::2, 3] = 1
        bv[0::2] = lx
        bv[1::2] = ly
        return A, bv

    def _params_to_M(params: np.ndarray) -> np.ndarray:
        a, b, tx, ty = params
        return np.array([[a, b], [-b, a], [tx, ty]])

    for _ in range(n_iter):
        idx = rng.choice(n, 2, replace=False)
        A_s, b_s = _build_system(right_pts[idx], left_pts[idx])
        try:
            params, _, _, _ = np.linalg.lstsq(A_s, b_s, rcond=None)
        except np.linalg.LinAlgError:
            continue

        M_cand = _params_to_M(params)
        residuals = np.linalg.norm(R_h @ M_cand - left_pts, axis=1)
        inliers = residuals < inlier_threshold
        count = inliers.sum()
        if count > best_count:
            best_count = count
            best_inliers = inliers
            best_M = M_cand

    # Refit on all inliers using least squares
    if best_count >= 2:
        A_full, b_full = _build_system(right_pts[best_inliers], left_pts[best_inliers])
        params_final, _, _, _ = np.linalg.lstsq(A_full, b_full, rcond=None)
        M_final = _params_to_M(params_final)
    else:
        M_final = best_M

    residuals_final = np.linalg.norm(R_h @ M_final - left_pts, axis=1)
    inlier_residuals = residuals_final[best_inliers]
    residual_mean = float(inlier_residuals.mean()) if len(inlier_residuals) > 0 else float("nan")

    return M_final, best_inliers, residual_mean


def decompose_affine(M: np.ndarray) -> dict:
    """
    Decompose a (3, 2) affine matrix into interpretable components.

    Returns dict with rotation_deg, scale_x, scale_y, shear_deg, tx, ty.
    A pure similarity transform would have scale_x ≈ scale_y and shear_deg ≈ 0.
    """
    # M = [[a, b], [c, d], [tx, ty]]
    a, b = float(M[0, 0]), float(M[0, 1])
    c, d = float(M[1, 0]), float(M[1, 1])
    tx, ty = float(M[2, 0]), float(M[2, 1])

    scale_x = float(np.sqrt(a**2 + c**2))
    scale_y = float(np.sqrt(b**2 + d**2))
    rotation_rad = float(np.arctan2(c, a))
    rotation_deg = float(np.degrees(rotation_rad))
    shear = float(np.arctan2(b, d) - rotation_rad + np.pi / 2)
    shear_deg = float(np.degrees(shear))

    return {
        "rotation_deg": round(rotation_deg, 3),
        "scale_x":      round(scale_x, 5),
        "scale_y":      round(scale_y, 5),
        "shear_deg":    round(shear_deg, 3),
        "tx":           round(tx, 2),
        "ty":           round(ty, 2),
    }


# ---------------------------------------------------------------------------
# Diagnostic plots
# ---------------------------------------------------------------------------

def plot_calibration_diagnostics(
    right_pts: np.ndarray,
    left_pts:  np.ndarray,
    M: np.ndarray,
    inliers: np.ndarray,
    residuals_before: np.ndarray,
    residuals_after:  np.ndarray,
    output_path: str,
    pair: str,
):
    """Four-panel diagnostic plot for the calibration result."""
    R_h = np.column_stack([right_pts, np.ones(len(right_pts))])
    corrected = R_h @ M

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Affine calibration diagnostics — {pair} pair\n"
                 f"Inliers: {inliers.sum()} / {len(inliers)} ({100*inliers.mean():.1f}%)")

    # 1. Correspondence scatter before correction (inliers only)
    ax = axes[0, 0]
    ax.scatter(right_pts[inliers, 0], right_pts[inliers, 1],
               s=2, alpha=0.3, color="tab:orange", label="right (coarse)")
    ax.scatter(left_pts[inliers, 0],  left_pts[inliers, 1],
               s=2, alpha=0.3, color="tab:blue",   label="left")
    ax.set_title("Before correction (inliers only)")
    ax.set_xlabel("x (px)"); ax.set_ylabel("y (px)")
    ax.legend(markerscale=5)

    # 2. Correspondence scatter after correction (inliers only)
    ax = axes[0, 1]
    ax.scatter(corrected[inliers, 0], corrected[inliers, 1],
               s=2, alpha=0.3, color="tab:orange", label="right (corrected)")
    ax.scatter(left_pts[inliers, 0],  left_pts[inliers, 1],
               s=2, alpha=0.3, color="tab:blue",   label="left")
    ax.set_title("After affine correction (inliers only)")
    ax.set_xlabel("x (px)"); ax.set_ylabel("y (px)")
    ax.legend(markerscale=5)

    # 3. Residual distributions
    ax = axes[1, 0]
    pct = [50, 75, 90, 95]
    ax.hist(residuals_before[inliers], bins=60, alpha=0.6,
            color="tab:red",   label="Before", density=True)
    ax.hist(residuals_after[inliers],  bins=60, alpha=0.6,
            color="tab:green", label="After",  density=True)
    ax.set_xlabel("Residual distance (px)")
    ax.set_ylabel("Density")
    ax.set_title("Residual distribution (inliers)")
    ax.legend()
    txt = "  ".join([f"p{p}: {np.percentile(residuals_after[inliers], p):.1f}"
                     for p in pct])
    ax.text(0.02, 0.97, f"After: {txt}", transform=ax.transAxes,
            va="top", fontsize=8)

    # 4. Quiver: displacement arrows (subsample for readability)
    ax = axes[1, 1]
    n = len(right_pts[inliers])
    step = max(1, n // 300)
    rp = right_pts[inliers][::step]
    lp = left_pts[inliers][::step]
    dx = lp[:, 0] - rp[:, 0]
    dy = lp[:, 1] - rp[:, 1]
    ax.quiver(rp[:, 0], rp[:, 1], dx, dy,
              angles="xy", scale_units="xy", scale=1,
              alpha=0.4, width=0.002, color="tab:purple")
    ax.set_title("Displacement field\n(right → left, before correction, inliers)")
    ax.set_xlabel("x (px)"); ax.set_ylabel("y (px)")

    plt.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  Saved: {output_path}")


# ---------------------------------------------------------------------------
# Per-pair calibration
# ---------------------------------------------------------------------------

def calibrate_pair(
    base_dir:     str,
    exp_name:     str,
    pair:         str,
    vote_radius:  float = 400.0,
    min_votes:    int   = 30,
    ransac_threshold: float = 40.0,
    output_dir:   str  = None,
    model:        str  = "auto",
) -> dict | None:
    """
    Run full calibration for one camera pair from one experiment.

    Args:
        model: Transform model to fit.
            "affine"      — 6 DOF (independent x/y scale, rotation, shear, tx, ty).
                            Requires a wide overlap to constrain all parameters.
            "similarity"  — 4 DOF (uniform scale, rotation, tx, ty).
                            Robust for moderate overlaps; auto-falls-back to
                            translation if the fit is degenerate.
            "translation" — 2 DOF (tx, ty only, using robust median).
                            Always works; appropriate for very narrow overlaps.
            "auto"        — Use similarity when overlap < 400 px, else affine.
                            Falls back to translation if similarity is degenerate.

    Returns the calibration dict, or None if not enough matches were found.
    """
    right_cam, left_cam = PAIRS[pair]
    transforms = TRANSFORM_CONFIG[tuple(sorted([right_cam, left_cam]))]
    _, side_r = CAMERA_CONFIG[right_cam]   # position (top/bottom) — unused
    side_r_key, _ = CAMERA_CONFIG[right_cam]   # 'right' or 'left'
    side_l_key, _ = CAMERA_CONFIG[left_cam]

    def feather(cam):
        return os.path.join(base_dir, f"{exp_name}.{cam}", f"{exp_name}_tracks.feather")

    print(f"\n  Loading {pair} pair...")
    r_raw = pd.read_feather(feather(right_cam))
    l_raw = pd.read_feather(feather(left_cam))

    r_t = apply_coarse_transform(r_raw, transforms[side_r_key])
    l_t = apply_coarse_transform(l_raw, transforms[side_l_key])

    overlap_xmin = float(max(r_t["x"].min(), l_t["x"].min()))
    overlap_xmax = float(min(r_t["x"].max(), l_t["x"].max()))
    print(f"  Overlap zone: x ∈ [{overlap_xmin:.0f}, {overlap_xmax:.0f}]  "
          f"({overlap_xmax - overlap_xmin:.0f} px wide)")

    # Filter to overlap zone for voting
    r_ov = r_t[(r_t["x"] >= overlap_xmin) & (r_t["x"] <= overlap_xmax)].copy()
    l_ov = l_t[(l_t["x"] >= overlap_xmin) & (l_t["x"] <= overlap_xmax)].copy()

    # Vote
    print(f"  Voting on track matches (radius={vote_radius}px, min_votes={min_votes})...")
    votes = vote_for_track_matches(l_ov, r_ov, radius=vote_radius)
    print(f"  Candidate pairs with ≥1 vote: {len(votes)}")

    # Greedy one-to-one matching
    matches = greedy_match_tracks(votes, min_votes=min_votes)
    print(f"  One-to-one matched track pairs: {len(matches)}")

    if len(matches) < 5:
        print(f"  ⚠️  Too few matched pairs ({len(matches)} < 5). "
              f"Try lowering --min-votes or using more experiments.")
        return None

    # Collect point correspondences
    right_pts, left_pts = collect_point_pairs(r_t, l_t, matches, overlap_xmin, overlap_xmax)
    print(f"  Total point correspondences: {len(right_pts)}")

    if len(right_pts) < 10:
        print("  ⚠️  Too few point pairs for fitting.")
        return None

    # Residuals before correction
    residuals_before = np.linalg.norm(right_pts - left_pts, axis=1)
    print(f"  Residuals BEFORE (p50 / p90): "
          f"{np.percentile(residuals_before, 50):.1f} / {np.percentile(residuals_before, 90):.1f} px")

    # Select transform model
    overlap_width = overlap_xmax - overlap_xmin
    AUTO_SIMILARITY_THRESHOLD = 400.0   # px — narrow overlap can't constrain x-scale
    if model == "auto":
        chosen_model = "similarity" if overlap_width < AUTO_SIMILARITY_THRESHOLD else "affine"
        print("  Model selection (auto): overlap={:.0f} px -> using {}".format(
            overlap_width, chosen_model))
    else:
        chosen_model = model
        print("  Model: {} (explicit)".format(chosen_model))

    # Fit transform with RANSAC (or robust median for translation)
    print("  Fitting {} transform (RANSAC threshold={:.0f}px)...".format(
        chosen_model, ransac_threshold))

    if chosen_model == "translation":
        M = fit_translation_robust(right_pts, left_pts)
        inliers = np.ones(len(right_pts), dtype=bool)
    elif chosen_model == "similarity":
        M, inliers, _ = fit_similarity_ransac(
            right_pts, left_pts, inlier_threshold=ransac_threshold)
        # Sanity check — fall back to translation if degenerate
        bad, reason = is_degenerate_transform(M)
        if bad:
            print("  ⚠️  Similarity fit is degenerate ({}). "
                  "Falling back to translation-only.".format(reason))
            chosen_model = "translation"
            M = fit_translation_robust(right_pts, left_pts)
            inliers = np.ones(len(right_pts), dtype=bool)
    else:  # affine
        M, inliers, _ = fit_affine_ransac(
            right_pts, left_pts, inlier_threshold=ransac_threshold)
        # Warn if degenerate but don't fall back (user asked explicitly)
        bad, reason = is_degenerate_transform(M)
        if bad:
            print("  ⚠️  Affine fit is degenerate ({}). "
                  "Consider re-running with --model similarity.".format(reason))

    R_h = np.column_stack([right_pts, np.ones(len(right_pts))])
    residuals_after = np.linalg.norm(R_h @ M - left_pts, axis=1)

    print(f"  RANSAC inliers: {inliers.sum()} / {len(inliers)} "
          f"({100*inliers.mean():.1f}%)")
    print(f"  Residuals AFTER  (p50 / p90, inliers): "
          f"{np.percentile(residuals_after[inliers], 50):.1f} / "
          f"{np.percentile(residuals_after[inliers], 90):.1f} px")
    print(f"  Mean improvement: "
          f"{np.percentile(residuals_before[inliers], 50):.1f} → "
          f"{np.percentile(residuals_after[inliers], 50):.1f} px (p50)")

    decomp = decompose_affine(M)
    print(f"  Transform decomposition: {decomp}")

    # Build calibration dict
    cal = {
        "pair":               pair,
        "model":              chosen_model,
        "right_camera":       right_cam,
        "left_camera":        left_cam,
        "affine_matrix":      M.tolist(),        # (3, 2), applied to right camera
        "n_matched_pairs":    len(matches),
        "n_point_pairs":      int(len(right_pts)),
        "n_inliers":          int(inliers.sum()),
        "inlier_fraction":    round(float(inliers.mean()), 4),
        "residual_before_p50": round(float(np.percentile(residuals_before[inliers], 50)), 2),
        "residual_before_p90": round(float(np.percentile(residuals_before[inliers], 90)), 2),
        "residual_after_p50":  round(float(np.percentile(residuals_after[inliers], 50)), 2),
        "residual_after_p90":  round(float(np.percentile(residuals_after[inliers], 90)), 2),
        "decomposition":      decomp,
        "vote_radius_px":     vote_radius,
        "ransac_threshold_px": ransac_threshold,
        "created":            str(date.today()),
        "source_experiments": [exp_name],
    }

    # Save calibration JSON
    out_dir = output_dir or os.path.join(base_dir.split("/")[0]
                                         if "/" in base_dir else ".", "calibration")
    os.makedirs(out_dir, exist_ok=True)
    cal_path = os.path.join(out_dir, f"affine_calibration_{pair}.json")
    with open(cal_path, "w") as f:
        json.dump(cal, f, indent=2)
    print(f"  Saved calibration: {cal_path}")

    # Diagnostic plot
    plot_path = os.path.join(out_dir, f"affine_calibration_{pair}.pdf")
    plot_calibration_diagnostics(
        right_pts, left_pts, M, inliers,
        residuals_before, residuals_after,
        plot_path, pair,
    )

    return cal


# ---------------------------------------------------------------------------
# Affine application (used by link_merge.py)
# ---------------------------------------------------------------------------

def apply_affine_calibration(df: pd.DataFrame, calibration: dict) -> pd.DataFrame:
    """
    Apply the stored affine correction to the RIGHT camera DataFrame.

    Args:
        df:            Right-camera DataFrame after coarse transform.
        calibration:   Dict loaded from the JSON calibration file.

    Returns:
        DataFrame with corrected x, y coordinates.
    """
    M = np.array(calibration["affine_matrix"])   # (3, 2)
    xy = df[["x", "y"]].values
    xy_h = np.column_stack([xy, np.ones(len(xy))])
    df = df.copy()
    df[["x", "y"]] = xy_h @ M
    return df


def load_calibration(cal_dir: str, pair: str) -> dict | None:
    """Load a calibration file for a given pair, or return None if not found."""
    path = os.path.join(cal_dir, f"affine_calibration_{pair}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Estimate residual affine transform between paired cameras using tracks"
    )
    parser.add_argument(
        "experiment_dir",
        help="Path to experiment base dir (e.g. 20260312/20260312a01sao_20260312_130019)",
    )
    parser.add_argument(
        "--pair", choices=["top", "bottom", "both"], default="both",
        help="Camera pair to calibrate (default: both)",
    )
    parser.add_argument(
        "--vote-radius", type=float, default=400.0,
        help="Max px distance to vote for a track match (default: 400)",
    )
    parser.add_argument(
        "--min-votes", type=int, default=30,
        help="Minimum vote count for a matched track pair to be used (default: 30)",
    )
    parser.add_argument(
        "--ransac-threshold", type=float, default=40.0,
        help="RANSAC inlier threshold in pixels (default: 40)",
    )
    parser.add_argument(
        "--model", choices=["affine", "similarity", "translation", "auto"], default="auto",
        help=(
            "Transform model: 'affine' (6 DOF), 'similarity' (4 DOF: rotation + "
            "uniform scale + translation), 'translation' (2 DOF: tx/ty only, always "
            "robust), or 'auto' (default). "
            "'auto' uses similarity when overlap < 400 px — if that fit is "
            "degenerate, it falls back to translation automatically."
        ),
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Directory for calibration JSON and plots (default: <date>/calibration/)",
    )
    args = parser.parse_args()

    exp_dir  = args.experiment_dir
    exp_name = Path(exp_dir).name
    base_dir = str(Path(exp_dir).parent)
    out_dir  = args.output_dir or os.path.join(base_dir, "calibration")

    pairs = ["top", "bottom"] if args.pair == "both" else [args.pair]

    for pair in pairs:
        print(f"\n{'='*60}")
        print(f"Calibrating {pair} pair")
        print(f"{'='*60}")
        calibrate_pair(
            base_dir=base_dir,
            exp_name=exp_name,
            pair=pair,
            vote_radius=args.vote_radius,
            min_votes=args.min_votes,
            ransac_threshold=args.ransac_threshold,
            output_dir=out_dir,
            model=args.model,
        )


if __name__ == "__main__":
    main()
