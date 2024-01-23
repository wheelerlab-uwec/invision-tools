import argparse
import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import trackpy as tp
import imageio
import pims

########################################################################
####                                                                ####
####                             tracking                           ####
####                                                                ####
########################################################################


# convert RGB image to greyscale uint8
def rgb2gray(rgb):
    gray = np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140])
    return gray.astype(np.uint8)


def track(video, output):

    # read video
    worm_vid = pims.PyAVVideoReader(video)

    # np array slicing to remove pixels from top, bottom, and left side
    test_frame = rgb2gray(worm_vid[0][500:-100, 250:])

    # grab the first 25 frames and get the maximum projection
    first_bit = np.zeros((25, test_frame.shape[0], test_frame.shape[1]))
    for i in range(0, 25):
        frame = rgb2gray(worm_vid[i][500:-100, 250:])
        first_bit[i] = frame
    max = np.amax(first_bit, axis=0)

    # store data in an HDF5 file

    with tp.PandasHDFStore(output) as s:
        for i in range(0, len(video)):
            frame = rgb2gray(worm_vid[i][500:-100, 250:])
            sub = frame - max
            features = tp.locate(sub, 35, invert=True,
                                 maxsize=9, minmass=1000)
            s.put(features)
            print(i)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')

    parser.add_argument('video', type=str,
                        help='Path to the video.')
    parser.add_argument('output', type=str,
                        help='Path to the output.')

    args = parser.parse_args()

    track(args.video,
          args.output)
