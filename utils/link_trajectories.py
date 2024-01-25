import argparse
import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trackpy as tp
from pathlib import Path


def plot_tracks(hd5):

    base = Path(hd5).stem

    with tp.PandasHDFStore(hd5) as s:
        for linked in tp.link_df_iter(s, 10, memory=10):
            s.put(linked)
        trajectories = pd.concat(iter(s))

    t1 = tp.filter_stubs(trajectories, 20)
    ax = tp.plot_traj(t1)
    plt.savefig(f"{base}.pdf")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')

    parser.add_argument('hd5', type=str,
                        help='Path to the hd5 of features.')
    args = parser.parse_args()

    plot_tracks(args.hd5)
