# convert_pickle_to_feather.py

import os
import sys
import gzip
import pickle
import pandas as pd
from pathlib import Path
import argparse

def convert_pickle_to_feather(target_dir):
    """Convert pkl.gz files in the specified directory to feather format.
    
    Args:
        target_dir (str or Path): Directory containing pkl.gz files to convert
    """
    target_path = Path(target_dir)
    
    if not target_path.exists():
        print(f"Error: Directory '{target_dir}' does not exist.")
        return
    
    if not target_path.is_dir():
        print(f"Error: '{target_dir}' is not a directory.")
        return
    
    # Find all pkl.gz files in the specified directory (non-recursive)
    pkl_files = list(target_path.glob('*.pkl.gz'))
    
    if not pkl_files:
        print(f"No pkl.gz files found in directory: {target_dir}")
        return
    
    print(f"Found {len(pkl_files)} pkl.gz file(s) in {target_dir}")
    
    for pkl_path in pkl_files:
        print(f'Converting {pkl_path.name}')
        feather_path = pkl_path.with_suffix('').with_suffix('.feather')
        
        try:
            with gzip.open(pkl_path, 'rb') as f:
                obj = pickle.load(f)
            if isinstance(obj, pd.DataFrame):
                obj.reset_index(drop=True, inplace=True)
                obj.to_feather(feather_path)
                print(f"Converted: {pkl_path} -> {feather_path}")
            else:
                print(f"Skipped (not a DataFrame): {pkl_path}")
        except Exception as e:
            print(f"Error converting {pkl_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert pkl.gz files in a specified directory to feather format."
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help="Directory containing pkl.gz files to convert (default: current directory)"
    )
    
    args = parser.parse_args()
    target_dir = Path(args.directory).resolve()
    
    print(f"Converting pkl.gz files in: {target_dir}")
    convert_pickle_to_feather(target_dir)


