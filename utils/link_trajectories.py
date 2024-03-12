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
import glob


def merge_data(hdf5s, input):

    all_data = []

    i = 0
    for file, i in zip(hdf5s, range(len(hdf5s))):
        with tp.PandasHDFStore(file, mode='r') as hdf5:
            print(f'Getting data from {Path(file).stem}')
            all_results = hdf5.dump()
            if i == 0:
                zero_records = int(all_results['frame'].max())
                print(f'{zero_records} frames in {Path(file).stem}')
            elif i == 1:
                one_records = int(all_results['frame'].max())
                all_results['frame'] += (zero_records + 1)
                print(f'{one_records} frames in {Path(file).stem}')
            elif i == 2:
                two_records = int(all_results['frame'].max())
                all_results['frame'] += (zero_records + one_records + 1)
                print(f'{two_records} frames in {Path(file).stem}')
            all_data.append(all_results)
            i += 1

    all_data = pd.concat(all_data)
    all_records = int(len(all_data['frame']))
    print(f'{all_records} rows in merged data frame.')

    if 'particle' in all_data.columns:
        all_data = all_data.drop(columns=['particle'])

    pickle_path = Path(input, Path(input).stem + '_tracks.pkl.gz')
    with gzip.open(pickle_path, 'wb') as f:
        print('Writing pickle file.')
        pickle.dump(all_data, f)

    return all_data


def generate_tracks(df, input):

    if 'miracidia' in input:
        search_range = 100
        memory = 100
    elif 'mosquito' in input:
        search_range = 1000
        memory = 1000
    print('Linking particles.')
    t = tp.link(df, search_range=search_range, memory=memory)
    pickle_path = Path(input, Path(input).stem + '_tracks.pkl.gz')
    with gzip.open(pickle_path, 'wb') as f:
        print('Writing pickle file.')
        pickle.dump(t, f)
    print('Filtering stubs.')
    t1 = tp.filter_stubs(t, 200)

    return t1


def plot_tracks(tracks, input):

    print('Plotting trajectories.')
    save_path = Path(input, Path(input).stem + '.pdf')
    fig = plt.figure()
    ax = plt.gca()
    tp.plot_traj(tracks, ax=ax)
    fig.savefig(save_path)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')
    parser.add_argument('input',
                        type=str, help='Path to input directory containing .pkl.gz or .hdf5')
    parser.add_argument('--pickle', action='store_true')
    parser.add_argument('--hdf5', action='store_true')

    args = parser.parse_args()

    if args.pickle:
        pkl_file = glob.glob(f'{args.input}/*.pkl.gz')
        df = pd.read_pickle(pkl_file[0])

        tracks = generate_tracks(df, args.input)
        plot_tracks(tracks, args.input)

    elif args.hdf5:
        hdf5_files = glob.glob(f'{args.input}/*.hdf5')
        merged = merge_data(sorted(hdf5_files), args.input)
        tracks = generate_tracks(merged, args.input)
        plot_tracks(tracks, args.input)
