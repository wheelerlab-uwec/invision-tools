# Agent Guidelines for Miracidia Tracking Optimization

## Build/Test Commands
- **Run script**: `python optimize_tracking.py --video <path> --diameter <int> --minmass <float> --search-range <float> --memory <int> --output <dir>`
- **Batch search**: `python optimize_tracking.py --video <path> --batch`
- **Single test**: See `test_parameters()` function in optimize_tracking.py

## Code Style
- **Language**: Python 3.x with type hints
- **Imports**: Standard library first, then third-party (numpy, pandas, trackpy, pims), grouped and alphabetical
- **Formatting**: 4-space indentation, 100-char line length preferred
- **Types**: Use type hints for function parameters and returns (e.g., `Dict`, `Optional[float]`, `pd.DataFrame`)
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Docstrings**: Google-style with Args/Returns sections for all public functions
- **Error handling**: Use try/except with specific exceptions, print warnings for non-fatal errors

## Key Conventions
- Functions return dictionaries with 'score' and 'metrics' keys for evaluation
- All results save to JSON files named `results_d{diameter}_m{minmass}.json`
- Target scores: >60 decent, >70 good, >80 excellent tracking quality
- Parameters: diameter (odd int, 7-15), minmass (50-500), search_range (3-10), memory (1-5)
