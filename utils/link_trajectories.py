import argparse
import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trackpy as tp
from pathlib import Path
import argparse
import gzip
import pickle


def plot_tracks(hd5s):

    all_data = []

    i = 0
    for file in hd5s:
        with tp.PandasHDFStore(file, mode='r') as hdf5:
            print(f'Getting data from {Path(file).stem}')
            if i == 0:
                all_results = hdf5.dump()
                zero_records = int(len(all_results['frame']))
                print(f'{zero_records} rows in {Path(file).stem}')
                all_data.append(all_results)
            elif i == 1:
                all_results = hdf5.dump()
                all_results['frame'] += (zero_records + 1)
                one_records = int(len(all_results['frame']))
                print(f'{one_records} rows in {Path(file).stem}')
                all_data.append(all_results)
            elif i == 2:
                all_results = hdf5.dump()
                all_results['frame'] += (zero_records + one_records + 1)
                two_records = int(len(all_results['frame']))
                print(f'{two_records} rows in {Path(file).stem}')
                all_data.append(all_results)
            i += 1

    all_data = pd.concat(all_data)
    all_records = int(len(all_data['frame']))
    print(f'{all_records} rows in merged data frame.')

    if 'particle' in all_data.columns:
        all_data = all_data.drop(columns=['particle'])

    parent = Path(hd5s[0]).parent
    pickle_path = Path(parent, Path(hd5s[0]).stem + '.pkl.gz')
    with gzip.open(pickle_path, 'wb') as f:
        print('Writing pickle file.')
        pickle.dump(all_data, f)

    print('Linking particles.')
    t = tp.link(all_data, 50, memory=100)
    print('Filtering stubs.')
    t1 = tp.filter_stubs(t, 200)
    plt.figure()
    print('Plotting trajectories.')
    ax = tp.plot_traj(t1)

    save_path = Path(parent, Path(hd5s[0]).stem + '.pdf')
    plt.savefig(save_path)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')
    parser.add_argument('hd5s', nargs='+',
                        type=str, help='List of strings')
    args = parser.parse_args()

    plot_tracks(args.hd5s)
