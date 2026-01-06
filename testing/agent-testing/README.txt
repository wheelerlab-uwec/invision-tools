MIRACIDIA TRACKING OPTIMIZATION - STATUS & PLAN
================================================

COMPLETED WORK
--------------
1. Fixed 4 critical bugs in tracking code:
   - Changed from PIMS to CV2 (no memory issues)
   - Changed background from median to MAX projection
   - Fixed background subtraction to use absolute difference
   - Fixed invert parameter (False for bright objects)

2. Generated pre-computed backgrounds:
   - Location: ./backgrounds/
   - 3 chunks covering frames 0-75
   - Used by all future optimization runs

3. Verified working parameters:
   - diameter=7, minmass=50
   - Score: 47.67
   - 14 tracks with 2 moving long tracks (14.3%)
   - Trajectory plot shows proper swimming behavior

CURRENT FILES
-------------
- optimze_tracking.py      - Main tracking script (FIXED)
- generate_backgrounds.py  - Pre-computes max projection backgrounds
- run_parameter_sweep.py   - Systematic parameter optimization
- guide.md                 - Original optimization guide
- backgrounds/             - Pre-computed backgrounds (3 chunks)
- examples/                - Reference trajectory plots
  - good1.png             - Target (clean, ~15-20 organisms)
  - good3.png             - Target (dense, ~50-100 organisms)  
  - bad.png               - Old flawed result (stationary dots)
- tracking_results/        - Output directory for results

OPTIMIZATION PLAN
-----------------
Run: python run_parameter_sweep.py

This will test 24 parameter combinations:
- Diameter: 5, 7, 9, 11
- MinMass: 30, 40, 50, 60, 80, 100

For each combination:
- Uses pre-computed backgrounds (fast!)
- Tests 75 frames
- Generates trajectory plot
- Calculates movement-aware score

Output:
- tracking_results/parameter_sweep_results.csv
- Individual result JSON files
- Trajectory plots for each combination

Expected runtime: ~2-3 hours for 24 combinations

AFTER PARAMETER SWEEP
---------------------
1. Review results CSV to find best detection parameters
2. Run linking optimization with best params:
   - Test search_range: 3, 5, 7, 10
   - Test memory: 2, 3, 5, 7
3. Final validation on longer video segment
4. Apply to full video

KEY METRICS TO WATCH
--------------------
- Score: Higher is better (target >50)
- Moving long track ratio: Target >20%
- Total tracks: Should be 10-100 (not 1000+)
- Median velocity: Should be >0.3 px/frame
- Trajectory plot: Should show curved swimming paths

PRODUCTION PARAMETERS (REFERENCE)
----------------------------------
Full resolution (5496×3672):
- diameter: 23
- minmass: 550

4x downsampled (1374×918):
- diameter: 7 (23/4, rounded to odd)
- minmass: 40-60 (550/10-14 for area scaling)
