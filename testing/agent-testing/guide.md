# Miracidia Tracking Optimization: Agent Setup Guide

This guide explains how to set up an optimal environment for an AI agent to optimize TrackPy parameters for miracidia tracking.

## Overview

The script (`optimize_tracking.py`) provides quantitative metrics that allow an agent to evaluate tracking quality without needing to visually inspect plots. The agent can iterate on parameters and use the composite score to find optimal settings.

## Key Features

### 1. Quantitative Evaluation Metrics

The script computes these metrics automatically:

**Track Length Metrics:**
- Average, median, and max track lengths
- Distribution of very short (<5), short (5-20), medium (20-40), and long (40+) tracks
- Long track ratio (% of tracks >40 frames)
- Noise ratio (% of very short tracks)

**Motion Quality Metrics:**
- Mean velocity and standard deviation
- Motion smoothness (lower = better)
- Detection of unrealistic velocities (likely tracking errors)
- Acceleration patterns

**Coverage Metrics:**
- Frame coverage (% of frames with detections)
- Detections per frame

**Composite Score:**
- Single number (0-100+) that summarizes overall quality
- Higher is better
- Weighted combination of all metrics

### 2. Agent-Friendly Interface

The main function for agents to use:

```python
results = test_parameters(
    video_path="test_video.mp4",
    diameter=11,           # Feature size
    minmass=100,          # Brightness threshold
    separation=None,      # Min separation (default: diameter+1)
    search_range=5,       # Linking distance
    memory=3,             # Frames to remember lost features
    save_plots=True,      # Save trajectory visualizations
    output_dir="./results"
)

# Returns a dictionary with:
# - results['score']: Composite quality score (higher = better)
# - results['metrics']: Detailed metrics dictionary
# - results['parameters']: Parameters used
```

### 3. JSON Output

All results are saved to JSON files that the agent can read:

```json
{
  "score": 67.35,
  "metrics": {
    "total_detections": 15234,
    "num_tracks": 847,
    "track_length_mean": 35.2,
    "long_track_ratio": 0.42,
    "noise_ratio": 0.15,
    "motion_smoothness_mean": 2.1,
    "velocity_mean": 3.5,
    "frame_coverage": 0.89
  },
  "parameters": {
    "diameter": 11,
    "minmass": 100,
    "separation": 12,
    "search_range": 5,
    "memory": 3
  }
}
```

## Setup Instructions

### Directory Structure

```
project/
├── optimize_tracking.py       # Main script
├── test_video.mp4             # Your test video
└── tracking_results/          # Output directory (auto-created)
    ├── results_d11_m100.json
    ├── trajectories_d11_m100.png
    └── batch_results.csv
```

## Usage for Agents

### Option 1: Claude Code or Similar (Recommended)

**Setup:**
1. Place the script and test video in a project directory
2. Ensure the conda environment is activated

**Agent Workflow:**
```python
# Agent modifies these parameters and runs the script
import json
import subprocess

params = {
    'diameter': 11,
    'minmass': 150,
    'search_range': 6
}

# Run tracking
cmd = f"python optimize_tracking.py --video test_video.mp4 " \
      f"--diameter {params['diameter']} " \
      f"--minmass {params['minmass']} " \
      f"--search-range {params['search_range']}"
      
subprocess.run(cmd, shell=True)

# Read results
with open(f"./tracking_results/results_d{params['diameter']}_m{int(params['minmass'])}.json") as f:
    results = json.load(f)

score = results['score']
metrics = results['metrics']

# Agent decides next parameters based on score and metrics
# Iterate until satisfied with score
```

**What the Agent Should Look For:**
- **Score > 60**: Decent tracking
- **Score > 70**: Good tracking
- **Score > 80**: Excellent tracking
- **Long track ratio > 0.4**: Good proportion of useful tracks
- **Noise ratio < 0.2**: Low false positives
- **Motion smoothness < 3**: Realistic, smooth motion

### Option 2: Jupyter Notebook (Interactive)

```python
# Import the script functions
from optimize_tracking import test_parameters

# Test parameters
results = test_parameters(
    video_path="test_video.mp4",
    diameter=11,
    minmass=100
)

print(f"Score: {results['score']}")
print(f"Long tracks: {results['metrics']['long_track_ratio']:.2%}")

# Iterate based on results
```

### Option 3: Batch Search

For an initial broad search:

```bash
python optimize_tracking.py --video test_video.mp4 --batch
```

This tests multiple combinations:
- Diameters: [7, 9, 11, 13, 15]
- Minmass: [50, 100, 200, 300, 500]

Results are saved to `batch_results.csv` sorted by score.

## Parameter Guidelines

### Detection Parameters

**`diameter`** (odd integer, typically 7-15):
- Too small: Misses miracidia, many false positives
- Too large: Loses detail, merges nearby organisms
- Start with 11, adjust based on actual miracidia size in pixels

**`minmass`** (float, typically 50-500):
- Too low: Many false positives (noise)
- Too high: Misses real miracidia
- Check histogram of detected masses in initial runs

**`separation`** (float, default: diameter + 1):
- Minimum distance between detected features
- Prevents detecting same organism twice

### Linking Parameters

**`search_range`** (float, typically 3-10):
- Maximum distance (pixels) a feature can move between frames
- Too small: Breaks tracks frequently
- Too large: May link wrong features

**`memory`** (int, typically 1-5):
- Frames to remember "disappeared" features
- Helps when miracidia temporarily disappear (occlusion)

## Optimization Strategy for Agents

### Phase 1: Coarse Search
```python
# Test broad ranges
diameters = [7, 9, 11, 13, 15]
minmasses = [50, 100, 200, 500]
# Find approximate best region
```

### Phase 2: Fine Tuning
```python
# Once you find best range (e.g., diameter=11, minmass=100)
# Test nearby values
diameters = [9, 10, 11, 12, 13]
minmasses = [75, 100, 125, 150, 175]
```

### Phase 3: Linking Optimization
```python
# With best detection params, optimize linking
search_ranges = [3, 4, 5, 6, 7]
memories = [1, 2, 3, 4, 5]
```

### Phase 4: Validation
```python
# Test best parameters on multiple videos
# Ensure consistency
```

## Interpreting Results

### Good Tracking Indicators:
- Score > 70
- Long track ratio > 0.40
- Noise ratio < 0.20
- Mean track length > 30 frames
- Motion smoothness < 3
- Unrealistic velocities = 0

### Poor Tracking Indicators:
- Score < 40
- High noise ratio (>0.30)
- Many very short tracks
- High motion smoothness (>5)
- Many unrealistic velocities

### Common Issues:

**Low Score, High Noise:**
- Increase `minmass` to filter out dim false positives
- Increase `separation` to prevent double-detections

**Low Score, Few Detections:**
- Decrease `minmass` to detect dimmer miracidia
- Adjust `diameter` to match actual size

**Fragmented Tracks:**
- Increase `search_range` (miracidia moving faster than expected)
- Increase `memory` (temporary disappearances)

**Merged Tracks (unrealistic jumps):**
- Decrease `search_range`
- Increase `separation` in detection

## Visual Verification

While the agent optimizes using metrics, you should periodically check the saved plots:

- `trajectories_d{diameter}_m{minmass}.png`: Shows all tracks and length distribution
- Look for smooth, continuous tracks
- Verify tracks look realistic (not erratic jumps)

## Advanced: Custom Metric Weights

If you want to prioritize certain aspects, modify the `_compute_composite_score()` function:

```python
weights = {
    'length': 0.25,      # Average track length
    'long_ratio': 0.25,  # Proportion of long tracks
    'noise': 0.15,       # Penalty for short tracks
    'smooth': 0.15,      # Motion smoothness
    'coverage': 0.20     # Frame coverage
}
```

Adjust these based on your priorities:
- Need fewer but longer tracks? Increase `'long_ratio'`
- Worried about noise? Increase `'noise'`
- Need better temporal coverage? Increase `'coverage'`

## Example Agent Conversation

**Agent:** "I'll start by testing the default parameters."
```python
results = test_parameters(video_path="test.mp4", diameter=11, minmass=100)
# Score: 45.2, noise_ratio: 0.35, long_track_ratio: 0.18
```

**Agent:** "Score is low with high noise. Let me increase minmass to reduce false positives."
```python
results = test_parameters(video_path="test.mp4", diameter=11, minmass=200)
# Score: 62.3, noise_ratio: 0.15, long_track_ratio: 0.38
```

**Agent:** "Better! Let me try slightly larger diameter to match organism size."
```python
results = test_parameters(video_path="test.mp4", diameter=13, minmass=200)
# Score: 71.5, noise_ratio: 0.12, long_track_ratio: 0.45
```

**Agent:** "Great! Now let me optimize linking to connect tracks better."
```python
results = test_parameters(video_path="test.mp4", diameter=13, minmass=200, 
                         search_range=7, memory=4)
# Score: 76.8, noise_ratio: 0.11, long_track_ratio: 0.51
```

**Agent:** "Excellent! Final parameters: diameter=13, minmass=200, search_range=7, memory=4"

## Troubleshooting

**"No features detected":**
- `minmass` is too high
- `diameter` is wrong size
- Video might need preprocessing

**"Too many features detected":**
- `minmass` is too low
- Background subtraction not working well

**Script is slow:**
- Process only first 1000 frames for testing
- Reduce video resolution if possible

**Memory errors:**
- Process video in smaller chunks
- Reduce number of frames in batch

## Next Steps

Once the agent finds optimal parameters:

1. Validate on additional test videos
2. Apply to full dataset using the Snakemake workflow
3. Consider video-specific parameter sets if conditions vary
4. Document the optimal parameters for future use

## Contact

If you encounter issues or need to modify the scoring function for your specific needs, adjust the weights in `_compute_composite_score()` or add custom metrics in the evaluator.
