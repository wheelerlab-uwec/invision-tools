"""
Parameter optimization plan for miracidia tracking.
Runs systematic tests with pre-computed backgrounds.
"""

from optimze_tracking import test_parameters
import pandas as pd
from pathlib import Path
import json

def run_parameter_sweep():
    """
    Run systematic parameter sweep to find optimal tracking parameters.
    """
    
    # Test parameters
    diameters = [5, 7, 9, 11]
    minmass_values = [30, 40, 50, 60, 80, 100]
    
    results = []
    
    print("="*80)
    print("MIRACIDIA TRACKING PARAMETER OPTIMIZATION")
    print("="*80)
    print(f"Testing {len(diameters)} diameters × {len(minmass_values)} minmass values")
    print(f"Total combinations: {len(diameters) * len(minmass_values)}")
    print(f"Using pre-computed max projection backgrounds")
    print("="*80)
    
    for diameter in diameters:
        for minmass in minmass_values:
            print(f"\n{'='*80}")
            print(f"Testing: diameter={diameter}, minmass={minmass}")
            print(f"{'='*80}")
            
            try:
                result = test_parameters(
                    video_path="test_video.mp4",
                    diameter=diameter,
                    minmass=minmass,
                    separation=None,
                    search_range=5,
                    memory=3,
                    save_plots=True,
                    output_dir="./tracking_results",
                    max_frames=75,
                    run_version=f"sweep_d{diameter}_m{int(minmass)}",
                    downsample_factor=4
                )
                
                # Extract key metrics
                metrics = result.get('metrics', {})
                result_summary = {
                    'diameter': diameter,
                    'minmass': minmass,
                    'score': result.get('score', 0),
                    'total_tracks': metrics.get('num_tracks', 0),
                    'long_tracks': metrics.get('long_tracks', 0),
                    'long_tracks_moving': metrics.get('long_tracks_moving', 0),
                    'moving_ratio': metrics.get('moving_long_track_ratio', 0),
                    'median_velocity': metrics.get('velocity_median', 0),
                    'detections_per_frame': metrics.get('detections_per_frame_mean', 0),
                }
                
                results.append(result_summary)
                
                print(f"\nRESULT: Score={result_summary['score']:.2f}")
                print(f"  Tracks: {result_summary['total_tracks']} total, "
                      f"{result_summary['long_tracks_moving']} moving long tracks")
                print(f"  Moving ratio: {result_summary['moving_ratio']:.1%}")
                
            except Exception as e:
                print(f"ERROR: {e}")
                results.append({
                    'diameter': diameter,
                    'minmass': minmass,
                    'score': 0,
                    'error': str(e)
                })
    
    # Save results
    df = pd.DataFrame(results)
    output_file = Path("tracking_results/parameter_sweep_results.csv")
    df.to_csv(output_file, index=False)
    
    print(f"\n{'='*80}")
    print("PARAMETER SWEEP COMPLETE")
    print(f"{'='*80}")
    print(f"Results saved to: {output_file}")
    
    # Print summary
    print(f"\nTOP 10 PARAMETER SETS BY SCORE:")
    print("-"*80)
    top_results = df.nlargest(10, 'score')
    print(top_results[['diameter', 'minmass', 'score', 'total_tracks', 
                       'long_tracks_moving', 'moving_ratio']].to_string(index=False))
    
    return df


if __name__ == "__main__":
    results_df = run_parameter_sweep()
