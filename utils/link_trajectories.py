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
    total_records = 0
    for file, i in zip(hdf5s, range(len(hdf5s))):
        with tp.PandasHDFStore(file, mode="r") as hdf5:
            print(f"Getting data from {Path(file).stem}")
            try:
                all_results = hdf5.dump()
                if i == 0:
                    records = int(all_results["frame"].max())
                    total_records = records
                    print(f"{records} frames in {Path(file).stem}")
                else:
                    new_records = int(all_results["frame"].max())
                    total_records = total_records + new_records + 1
                    all_results["frame"] += total_records - new_records
                    print(
                        f"{new_records} frames in {Path(file).stem}. {total_records} total records")
                all_data.append(all_results)
            except ValueError as e:
                if "No objects to concatenate" in str(e):
                    print(f"Skipping empty file: {Path(file).stem}")
                    if i == 0:
                        total_records = -1  # Reset to -1 so next non-empty file starts at 0
                    continue
                else:
                    raise e
            i += 1

    all_data = pd.concat(all_data)
    all_records = int(len(all_data["frame"]))
    print(f"{all_records} rows in merged data frame.")

    if "particle" in all_data.columns:
        all_data = all_data.drop(columns=["particle"])

    pickle_path = Path(input, Path(input).stem + "_tracks.pkl.gz")
    with gzip.open(pickle_path, "wb") as f:
        print("Writing pickle file.")
        pickle.dump(all_data, f)

    return all_data


def generate_tracks(df, input):

    if "miracidia" in input:
        search_range = 45
        memory = 25
        adaptive_stop = 30
    elif "mosquito" in input:
        search_range = 750
        memory = 100
        adaptive_stop = None
    elif "planaria" in input:
        search_range = 750
        memory = 100
        adaptive_stop = None

    print("Linking particles.")
    t = tp.link(df, search_range=search_range,
                memory=memory, adaptive_stop=adaptive_stop)
    pickle_path = Path(input, Path(input).stem + "_tracks.pkl.gz")
    with gzip.open(pickle_path, "wb") as f:
        print("Writing pickle file.")
        pickle.dump(t, f)
    print("Filtering stubs.")
    t1 = tp.filter_stubs(t, 200)

    return t1


def plot_tracks(tracks, input):

    print("Plotting trajectories.")
    save_path = Path(input, Path(input).stem + ".pdf")
    fig = plt.figure()
    ax = plt.gca()
    tp.plot_traj(tracks, ax=ax)
    fig.savefig(save_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Track objects in an InVision video.")
    parser.add_argument(
        "input", type=str, help="Path to input directory containing .pkl.gz or .hdf5"
    )
    parser.add_argument("--pickle", action="store_true")
    parser.add_argument("--hdf5", action="store_true")

    args = parser.parse_args()

    if args.pickle:
        pkl_file = glob.glob(f"{args.input}/*.pkl.gz")
        df = pd.read_pickle(pkl_file[0])

        tracks = generate_tracks(df, args.input)
        plot_tracks(tracks, args.input)

    elif args.hdf5:
        hdf5_files = glob.glob(f"{args.input}/*.hdf5")
        merged = merge_data(sorted(hdf5_files), args.input)
        tracks = generate_tracks(merged, args.input)
        plot_tracks(tracks, args.input)
