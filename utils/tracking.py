import argparse
import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import trackpy as tp
from pathlib import Path
import os
from skimage.filters import gaussian
from skimage.exposure import rescale_intensity, adjust_gamma
import cv2

########################################################################
####                                                                ####
####                             tracking                           ####
####                                                                ####
########################################################################


# convert RGB image to greyscale uint8
def rgb2gray(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    return gray.astype(np.uint8)


def process_frame(frame, background):
    # gray = rgb2gray(frame)
    sub = np.absolute((frame - background).astype(np.int8))
    # rescale = rescale_intensity(sub, out_range=(0, 255))
    # inv = (255 - rescale).astype(np.uint8)
    # smooth = gaussian(sub, sigma=5, preserve_range=True)

    return sub


def crop(frame, l, r, t, b):

    cropped = frame[t:-b, l:-r]

    return cropped


def track_batch(video, output):
    base = Path(output).stem
    os.makedirs(output, exist_ok=True)

    worm_vid = cv2.VideoCapture(video)
    num_frames = int(worm_vid.get(cv2.CAP_PROP_FRAME_COUNT))

    ret, frame = worm_vid.read()
    if ret == True:
        frame_shape = frame.shape

    # Reset the video capture to the first frame
    worm_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)

    worm_arr = np.zeros((num_frames, frame_shape[0], frame_shape[1]), np.uint8)
    for i in range(num_frames):

        if i % 50 == 0:
            print(f"Loading frame {i} to memory.")
        ret, frame = worm_vid.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        worm_arr[i] = frame

    if "planaria" not in output:
        i = 0
        chunk = 25
        for frame in worm_arr:
            if i % chunk == 0:
                print(f"Processing frame {i}")
                print(
                    f"Regenerating background using frames {i} to {i+chunk}.")
                background = np.amax(worm_arr[i: i + chunk, :, :], axis=0)
                save_path = Path(output, f"background_{chunk}.png")
                cv2.imwrite(str(save_path), background)
            arr = process_frame(frame, background)
            worm_arr[i] = arr
            if i % 450 == 0:
                save_path = Path(output, f"{base}_{i}.png")
                cv2.imwrite(str(save_path), arr)
            i += 1
        if "miracidia" in output:
            diameter = 23
            minmass = 550
            noise_size = 1
            topn = None
            with tp.PandasHDFStoreBig(Path(output, f"{base}.hdf5")) as s:
                tp.batch(worm_arr, diameter=diameter, minmass=minmass,
                         topn=topn, noise_size=noise_size, output=s)
        elif "mosquito" in output:
            diameter = 95
            minmass = 50000
            with tp.PandasHDFStoreBig(Path(output, f"{base}.hdf5")) as s:
                tp.batch(worm_arr, diameter=diameter,
                         minmass=minmass, output=s)
        else:
            print("Something went wrong.")
    else:
        diameter = 83
        minmass = 148000

        with tp.PandasHDFStoreBig(Path(output, f"{base}.hdf5")) as s:
            tp.batch(worm_arr, diameter=diameter, minmass=minmass, output=s)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Track objects in an InVision video.")

    parser.add_argument("video", type=str, help="Path to the video.")
    parser.add_argument("output", type=str,
                        help="Path to the output directory.")
    # parser.add_argument('-l', '--left', type=int,
    #                     help='Number of cols to remove from the left.')
    # parser.add_argument('-r', '--right', type=int,
    #                     help='Number of cols to remove from the right.')
    # parser.add_argument('-t', '--top', type=int,
    #                     help='Number of cols to remove from the top.')
    # parser.add_argument('-b', '--bottom', type=int,
    #                     help='Number of cols to remove from the bottom.')
    args = parser.parse_args()

    track_batch(args.video, args.output)
