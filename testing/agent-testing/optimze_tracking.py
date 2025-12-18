"""
Miracidia Tracking Optimization Script

This script loads a test video, tracks miracidia using TrackPy, links trajectories,
and evaluates tracking quality using quantitative metrics. Designed for agentic
parameter optimization.

Usage:
    python optimize_tracking.py --video path/to/video.mp4 --output results.json
    
Or modify parameters directly in test_parameters() function for batch testing.
"""

import numpy as np
import pandas as pd
import trackpy as tp
import pims
import json
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class MiracidiaTracker:
    """Handles miracidia detection and trajectory linking."""
    
    def __init__(self, video_path: str):
        """
        Initialize tracker with video file.
        
        Args:
            video_path: Path to video file (mp4, avi, etc.)
        """
        self.video_path = Path(video_path)
        self.frames = None
        self.features = None
        self.trajectories = None
        
    def load_video(self) -> None:
        """Load video frames using PIMS."""
        print(f"Loading video: {self.video_path}")
        self.frames = pims.open(str(self.video_path))
        print(f"Loaded {len(self.frames)} frames, shape: {self.frames.frame_shape}")
        
    def subtract_background(self, frame: np.ndarray, background: np.ndarray) -> np.ndarray:
        """
        Subtract background from frame.
        
        Args:
            frame: Current frame
            background: Background image
            
        Returns:
            Background-subtracted frame
        """
        # Ensure same dtype for subtraction
        frame_float = frame.astype(float)
        bg_float = background.astype(float)
        subtracted = frame_float - bg_float
        
        # Clip to valid range
        subtracted = np.clip(subtracted, 0, 255)
        return subtracted.astype(np.uint8)
    
    def generate_background(self, start_frame: int = 0, chunk_size: int = 25) -> np.ndarray:
        """
        Generate background by maximum projection over chunk of frames.
        
        Args:
            start_frame: Starting frame index
            chunk_size: Number of frames to use for background
            
        Returns:
            Background image
        """
        end_frame = min(start_frame + chunk_size, len(self.frames))
        chunk = [self.frames[i] for i in range(start_frame, end_frame)]
        
        # Handle grayscale vs color
        if len(chunk[0].shape) == 3:
            # Convert to grayscale if color
            chunk = [np.mean(frame, axis=2).astype(np.uint8) for frame in chunk]
        
        background = np.max(chunk, axis=0)
        return background
    
    def detect_features(self, 
                       diameter: int = 11,
                       minmass: float = 100,
                       separation: Optional[float] = None,
                       maxsize: Optional[float] = None,
                       noise_size: float = 1,
                       smoothing_size: Optional[float] = None,
                       threshold: Optional[float] = None,
                       percentile: float = 64,
                       invert: bool = False,
                       chunk_size: int = 25) -> pd.DataFrame:
        """
        Detect features (miracidia) in all frames using TrackPy.
        Uses rolling background subtraction.
        
        Args:
            diameter: Approximate feature size (odd integer)
            minmass: Minimum integrated brightness
            separation: Minimum separation between features
            maxsize: Maximum radius of gyration
            noise_size: Size for noise reduction
            smoothing_size: Size for Gaussian smoothing
            threshold: Brightness threshold (None = auto)
            percentile: Percentile for automatic threshold
            invert: Invert image before processing
            chunk_size: Frames per background generation
            
        Returns:
            DataFrame with detected features
        """
        print(f"\nDetecting features with parameters:")
        print(f"  diameter={diameter}, minmass={minmass}, separation={separation}")
        
        if separation is None:
            separation = diameter + 1
        
        all_features = []
        num_chunks = int(np.ceil(len(self.frames) / chunk_size))
        
        for chunk_idx in range(num_chunks):
            start_frame = chunk_idx * chunk_size
            end_frame = min((chunk_idx + 1) * chunk_size, len(self.frames))
            
            # Generate background for this chunk
            background = self.generate_background(start_frame, chunk_size)
            
            # Process each frame in chunk
            for frame_idx in range(start_frame, end_frame):
                frame = self.frames[frame_idx]
                
                # Convert to grayscale if needed
                if len(frame.shape) == 3:
                    frame = np.mean(frame, axis=2).astype(np.uint8)
                
                # Subtract background
                processed = self.subtract_background(frame, background)
                
                # Detect features
                try:
                    features = tp.locate(
                        processed,
                        diameter=diameter,
                        minmass=minmass,
                        separation=separation,
                        maxsize=maxsize,
                        noise_size=noise_size,
                        smoothing_size=smoothing_size,
                        threshold=threshold,
                        percentile=percentile,
                        invert=invert
                    )
                    
                    if len(features) > 0:
                        features['frame'] = frame_idx
                        all_features.append(features)
                        
                except Exception as e:
                    print(f"  Warning: Frame {frame_idx} failed: {e}")
                    continue
                
                if frame_idx % 100 == 0:
                    total_found = sum(len(f) for f in all_features)
                    print(f"  Processed frame {frame_idx}/{len(self.frames)}, "
                          f"total features: {total_found}")
        
        if all_features:
            self.features = pd.concat(all_features, ignore_index=True)
            print(f"\nTotal features detected: {len(self.features)}")
            print(f"Frames with detections: {self.features['frame'].nunique()}")
            return self.features
        else:
            print("\nWARNING: No features detected!")
            return pd.DataFrame()
    
    def link_trajectories(self,
                         search_range: float = 5,
                         memory: int = 3,
                         adaptive_stop: Optional[float] = None,
                         adaptive_step: float = 0.95) -> pd.DataFrame:
        """
        Link detected features into trajectories using TrackPy.
        
        Args:
            search_range: Maximum distance features can move between frames
            memory: Number of frames to remember when a feature disappears
            adaptive_stop: Minimum percentile for adaptive search
            adaptive_step: Adaptive search step size
            
        Returns:
            DataFrame with linked trajectories
        """
        if self.features is None or len(self.features) == 0:
            print("ERROR: No features to link. Run detect_features first.")
            return pd.DataFrame()
        
        print(f"\nLinking trajectories with:")
        print(f"  search_range={search_range}, memory={memory}")
        
        self.trajectories = tp.link(
            self.features,
            search_range=search_range,
            memory=memory,
            adaptive_stop=adaptive_stop,
            adaptive_step=adaptive_step
        )
        
        # Add some useful info
        num_tracks = self.trajectories['particle'].nunique()
        print(f"\nLinked {len(self.features)} features into {num_tracks} trajectories")
        
        return self.trajectories


class TrackingEvaluator:
    """Evaluates tracking quality using quantitative metrics."""
    
    def __init__(self, trajectories: pd.DataFrame, video_fps: float = 8.0):
        """
        Initialize evaluator.
        
        Args:
            trajectories: DataFrame with linked trajectories (from tp.link)
            video_fps: Frames per second of video
        """
        self.trajectories = trajectories
        self.fps = video_fps
        self.metrics = {}
        
    def compute_all_metrics(self) -> Dict:
        """
        Compute all tracking quality metrics.
        
        Returns:
            Dictionary of metrics and composite score
        """
        if len(self.trajectories) == 0:
            return {
                'score': 0.0,
                'error': 'No trajectories to evaluate',
                'metrics': {}
            }
        
        self.metrics = {
            'total_detections': len(self.trajectories),
            'num_tracks': self.trajectories['particle'].nunique(),
            'num_frames': self.trajectories['frame'].nunique(),
        }
        
        # Track length metrics
        self._compute_track_lengths()
        
        # Motion quality metrics
        self._compute_motion_metrics()
        
        # Coverage metrics
        self._compute_coverage_metrics()
        
        # Compute composite score
        score = self._compute_composite_score()
        
        return {
            'score': score,
            'metrics': self.metrics
        }
    
    def _compute_track_lengths(self) -> None:
        """Compute track length distribution metrics."""
        track_lengths = self.trajectories.groupby('particle').size()
        
        self.metrics['track_length_mean'] = track_lengths.mean()
        self.metrics['track_length_median'] = track_lengths.median()
        self.metrics['track_length_std'] = track_lengths.std()
        self.metrics['track_length_max'] = track_lengths.max()
        
        # Categorize tracks
        self.metrics['very_short_tracks'] = (track_lengths < 5).sum()
        self.metrics['short_tracks'] = ((track_lengths >= 5) & (track_lengths < 20)).sum()
        self.metrics['medium_tracks'] = ((track_lengths >= 20) & (track_lengths < 40)).sum()
        self.metrics['long_tracks'] = (track_lengths >= 40).sum()
        
        # Ratios
        total_tracks = len(track_lengths)
        self.metrics['long_track_ratio'] = self.metrics['long_tracks'] / total_tracks if total_tracks > 0 else 0
        self.metrics['noise_ratio'] = self.metrics['very_short_tracks'] / total_tracks if total_tracks > 0 else 0
        
    def _compute_motion_metrics(self) -> None:
        """Compute metrics related to motion smoothness and realism."""
        motion_scores = []
        velocity_list = []
        acceleration_list = []
        
        for particle_id in self.trajectories['particle'].unique():
            track = self.trajectories[self.trajectories['particle'] == particle_id].sort_values('frame')
            
            if len(track) < 3:
                continue
            
            # Compute frame-to-frame displacements
            dx = track['x'].diff()
            dy = track['y'].diff()
            displacements = np.sqrt(dx**2 + dy**2)
            
            # Velocity (pixels/frame)
            velocities = displacements / track['frame'].diff()
            velocities = velocities[~np.isnan(velocities)]
            
            if len(velocities) > 0:
                velocity_list.extend(velocities.tolist())
                
                # Motion smoothness (lower std = smoother)
                motion_scores.append(velocities.std())
                
                # Acceleration (change in velocity)
                if len(velocities) > 1:
                    accelerations = np.abs(velocities.diff())
                    acceleration_list.extend(accelerations[~np.isnan(accelerations)].tolist())
        
        if motion_scores:
            self.metrics['motion_smoothness_mean'] = np.mean(motion_scores)
            self.metrics['motion_smoothness_std'] = np.std(motion_scores)
        else:
            self.metrics['motion_smoothness_mean'] = 0
            self.metrics['motion_smoothness_std'] = 0
        
        if velocity_list:
            self.metrics['velocity_mean'] = np.mean(velocity_list)
            self.metrics['velocity_median'] = np.median(velocity_list)
            self.metrics['velocity_std'] = np.std(velocity_list)
            self.metrics['velocity_max'] = np.max(velocity_list)
            
            # Detect unrealistic jumps (likely tracking errors)
            # Miracidia typically move < 50 pixels/frame at 8 fps
            self.metrics['unrealistic_velocities'] = np.sum(np.array(velocity_list) > 50)
        else:
            self.metrics['velocity_mean'] = 0
            self.metrics['velocity_median'] = 0
            self.metrics['velocity_std'] = 0
            self.metrics['velocity_max'] = 0
            self.metrics['unrealistic_velocities'] = 0
        
        if acceleration_list:
            self.metrics['acceleration_mean'] = np.mean(acceleration_list)
        else:
            self.metrics['acceleration_mean'] = 0
    
    def _compute_coverage_metrics(self) -> None:
        """Compute metrics about temporal coverage."""
        total_frames = self.trajectories['frame'].max() - self.trajectories['frame'].min() + 1
        
        # Frame coverage
        frames_with_detections = self.trajectories['frame'].nunique()
        self.metrics['frame_coverage'] = frames_with_detections / total_frames if total_frames > 0 else 0
        
        # Detections per frame
        detections_per_frame = self.trajectories.groupby('frame').size()
        self.metrics['detections_per_frame_mean'] = detections_per_frame.mean()
        self.metrics['detections_per_frame_std'] = detections_per_frame.std()
        
    def _compute_composite_score(self) -> float:
        """
        Compute a weighted composite score for tracking quality.
        Higher is better.
        
        Weights are tuned for miracidia tracking goals:
        - Longer tracks are better
        - Smooth motion is better
        - Less noise (very short tracks) is better
        - Good frame coverage is better
        """
        m = self.metrics
        
        # Component scores (normalized to ~0-100 scale)
        
        # 1. Track length score (0-100)
        # Mean track length of 40+ frames is excellent
        length_score = min(m['track_length_mean'] / 40 * 100, 100)
        
        # 2. Long track ratio (0-100)
        long_ratio_score = m['long_track_ratio'] * 100
        
        # 3. Noise penalty (0-100, higher is better)
        # Less than 20% noise is good
        noise_score = (1 - min(m['noise_ratio'], 0.5)) * 100
        
        # 4. Motion smoothness (0-100, lower std is better)
        # Lower motion smoothness std indicates consistent, realistic motion
        # Typical values range from 0.5-5 for good tracking
        if m['motion_smoothness_mean'] > 0:
            smooth_score = max(0, 100 - m['motion_smoothness_mean'] * 20)
        else:
            smooth_score = 0
        
        # 5. Unrealistic motion penalty
        if m.get('unrealistic_velocities', 0) > 0:
            motion_penalty = -m['unrealistic_velocities'] * 5
        else:
            motion_penalty = 0
        
        # 6. Frame coverage (0-100)
        coverage_score = m['frame_coverage'] * 100
        
        # Weighted composite (adjust weights based on priorities)
        weights = {
            'length': 0.25,
            'long_ratio': 0.25,
            'noise': 0.15,
            'smooth': 0.15,
            'coverage': 0.20
        }
        
        score = (
            length_score * weights['length'] +
            long_ratio_score * weights['long_ratio'] +
            noise_score * weights['noise'] +
            smooth_score * weights['smooth'] +
            coverage_score * weights['coverage'] +
            motion_penalty
        )
        
        # Ensure non-negative
        score = max(0, score)
        
        return round(score, 2)
    
    def print_summary(self) -> None:
        """Print a human-readable summary of metrics."""
        if not self.metrics:
            self.compute_all_metrics()
        
        m = self.metrics
        
        print("\n" + "="*60)
        print("TRACKING QUALITY SUMMARY")
        print("="*60)
        
        print(f"\nBasic Stats:")
        print(f"  Total detections: {m['total_detections']}")
        print(f"  Number of tracks: {m['num_tracks']}")
        print(f"  Frames with detections: {m['num_frames']}")
        
        print(f"\nTrack Lengths:")
        print(f"  Mean: {m['track_length_mean']:.1f} frames")
        print(f"  Median: {m['track_length_median']:.1f} frames")
        print(f"  Max: {m['track_length_max']} frames")
        print(f"  Very short (<5): {m['very_short_tracks']}")
        print(f"  Short (5-20): {m['short_tracks']}")
        print(f"  Medium (20-40): {m['medium_tracks']}")
        print(f"  Long (40+): {m['long_tracks']}")
        print(f"  Long track ratio: {m['long_track_ratio']:.2%}")
        
        print(f"\nMotion Quality:")
        print(f"  Mean velocity: {m['velocity_mean']:.2f} pixels/frame")
        print(f"  Velocity std: {m['velocity_std']:.2f}")
        print(f"  Motion smoothness: {m['motion_smoothness_mean']:.2f}")
        print(f"  Unrealistic velocities: {m.get('unrealistic_velocities', 0)}")
        
        print(f"\nCoverage:")
        print(f"  Frame coverage: {m['frame_coverage']:.2%}")
        print(f"  Detections per frame: {m['detections_per_frame_mean']:.1f}")
        
        print("\n" + "="*60)


def test_parameters(video_path: str,
                   diameter: int = 11,
                   minmass: float = 100,
                   separation: Optional[float] = None,
                   search_range: float = 5,
                   memory: int = 3,
                   save_plots: bool = True,
                   output_dir: str = "./tracking_results") -> Dict:
    """
    Test a set of tracking parameters and return quality metrics.
    
    This is the main function an agent should call to evaluate parameters.
    
    Args:
        video_path: Path to test video
        diameter: Feature diameter for detection
        minmass: Minimum mass threshold
        separation: Minimum separation (None = diameter + 1)
        search_range: Max distance for linking
        memory: Frames to remember lost features
        save_plots: Whether to save trajectory plots
        output_dir: Directory for outputs
        
    Returns:
        Dictionary with score and metrics
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Initialize tracker
    tracker = MiracidiaTracker(video_path)
    tracker.load_video()
    
    # Detect features
    features = tracker.detect_features(
        diameter=diameter,
        minmass=minmass,
        separation=separation
    )
    
    if len(features) == 0:
        return {
            'score': 0.0,
            'error': 'No features detected',
            'parameters': {
                'diameter': diameter,
                'minmass': minmass,
                'separation': separation,
                'search_range': search_range,
                'memory': memory
            }
        }
    
    # Link trajectories
    trajectories = tracker.link_trajectories(
        search_range=search_range,
        memory=memory
    )
    
    # Evaluate quality
    evaluator = TrackingEvaluator(trajectories)
    results = evaluator.compute_all_metrics()
    evaluator.print_summary()
    
    # Add parameters to results
    results['parameters'] = {
        'diameter': diameter,
        'minmass': minmass,
        'separation': separation,
        'search_range': search_range,
        'memory': memory
    }
    
    # Save plots if requested
    if save_plots and len(trajectories) > 0:
        save_trajectory_plots(trajectories, output_path, diameter, minmass)
    
    # Save results to JSON
    results_file = output_path / f"results_d{diameter}_m{int(minmass)}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")
    
    return results


def save_trajectory_plots(trajectories: pd.DataFrame, 
                          output_dir: Path,
                          diameter: int,
                          minmass: float) -> None:
    """Save visualization plots of trajectories."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: All trajectories colored by particle
    ax = axes[0]
    for particle_id in trajectories['particle'].unique():
        track = trajectories[trajectories['particle'] == particle_id]
        ax.plot(track['x'], track['y'], alpha=0.5, linewidth=1)
    ax.set_xlabel('X (pixels)')
    ax.set_ylabel('Y (pixels)')
    ax.set_title(f'All Trajectories (n={trajectories["particle"].nunique()})')
    ax.invert_yaxis()  # Match image coordinates
    ax.set_aspect('equal')
    
    # Plot 2: Track length histogram
    ax = axes[1]
    track_lengths = trajectories.groupby('particle').size()
    ax.hist(track_lengths, bins=50, edgecolor='black')
    ax.set_xlabel('Track Length (frames)')
    ax.set_ylabel('Count')
    ax.set_title('Track Length Distribution')
    ax.axvline(track_lengths.mean(), color='r', linestyle='--', 
               label=f'Mean: {track_lengths.mean():.1f}')
    ax.legend()
    
    plt.tight_layout()
    
    plot_file = output_dir / f"trajectories_d{diameter}_m{int(minmass)}.png"
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Trajectory plot saved to: {plot_file}")


def batch_parameter_search(video_path: str,
                           diameter_range: list = [7, 9, 11, 13, 15],
                           minmass_range: list = [50, 100, 200, 300, 500],
                           output_dir: str = "./batch_results") -> pd.DataFrame:
    """
    Test multiple parameter combinations and return results.
    
    This is useful for an initial broad search.
    
    Args:
        video_path: Path to test video
        diameter_range: List of diameter values to test
        minmass_range: List of minmass values to test
        output_dir: Directory for outputs
        
    Returns:
        DataFrame with all results sorted by score
    """
    results_list = []
    
    total_tests = len(diameter_range) * len(minmass_range)
    test_num = 0
    
    for diameter in diameter_range:
        for minmass in minmass_range:
            test_num += 1
            print(f"\n{'='*60}")
            print(f"TEST {test_num}/{total_tests}: diameter={diameter}, minmass={minmass}")
            print(f"{'='*60}")
            
            try:
                result = test_parameters(
                    video_path=video_path,
                    diameter=diameter,
                    minmass=minmass,
                    output_dir=output_dir,
                    save_plots=False  # Save plots only for best
                )
                
                results_list.append({
                    'diameter': diameter,
                    'minmass': minmass,
                    'score': result['score'],
                    'num_tracks': result['metrics'].get('num_tracks', 0),
                    'track_length_mean': result['metrics'].get('track_length_mean', 0),
                    'long_track_ratio': result['metrics'].get('long_track_ratio', 0),
                    'noise_ratio': result['metrics'].get('noise_ratio', 0)
                })
                
            except Exception as e:
                print(f"ERROR: Test failed: {e}")
                results_list.append({
                    'diameter': diameter,
                    'minmass': minmass,
                    'score': 0,
                    'error': str(e)
                })
    
    # Create results DataFrame
    results_df = pd.DataFrame(results_list)
    results_df = results_df.sort_values('score', ascending=False)
    
    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    results_file = output_path / "batch_results.csv"
    results_df.to_csv(results_file, index=False)
    
    print(f"\n{'='*60}")
    print("BATCH RESULTS SUMMARY")
    print(f"{'='*60}")
    print(results_df.head(10))
    print(f"\nFull results saved to: {results_file}")
    
    return results_df


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize miracidia tracking parameters")
    parser.add_argument("--video", required=True, help="Path to test video")
    parser.add_argument("--diameter", type=int, default=11, help="Feature diameter")
    parser.add_argument("--minmass", type=float, default=100, help="Minimum mass")
    parser.add_argument("--separation", type=float, default=None, help="Minimum separation")
    parser.add_argument("--search-range", type=float, default=5, help="Linking search range")
    parser.add_argument("--memory", type=int, default=3, help="Linking memory")
    parser.add_argument("--output", default="./tracking_results", help="Output directory")
    parser.add_argument("--batch", action="store_true", help="Run batch parameter search")
    
    args = parser.parse_args()
    
    if args.batch:
        # Run batch search
        results = batch_parameter_search(
            video_path=args.video,
            output_dir=args.output
        )
    else:
        # Run single test
        results = test_parameters(
            video_path=args.video,
            diameter=args.diameter,
            minmass=args.minmass,
            separation=args.separation,
            search_range=args.search_range,
            memory=args.memory,
            output_dir=args.output
        )
        
        print(f"\n{'='*60}")
        print(f"FINAL SCORE: {results['score']:.2f}")
        print(f"{'='*60}")
