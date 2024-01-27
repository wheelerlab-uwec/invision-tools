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
from skimage.exposure import rescale_intensity
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
    sub = (frame - background).astype(np.int8)
    rescale = rescale_intensity(sub, out_range=(0, 255))
    inv = (255 - rescale).astype(np.uint8)
    smooth = gaussian(inv, sigma=5, preserve_range=True)

    return smooth


def crop(frame, l, r, t, b):

    cropped = frame[t:-b, l:-r]

    return cropped


def track_batch(video, output, left, right, top, bottom):
    base = Path(output).stem
    os.mkdir(output)
    worm_vid = cv2.VideoCapture(video)
    num_frames = int(worm_vid.get(cv2.CAP_PROP_FRAME_COUNT))

    ret, frame = worm_vid.read()
    if ret:
        frame_shape = frame.shape

    # Reset the video capture to the first frame
    worm_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)

    worm_arr = np.zeros(
        (num_frames, frame_shape[0], frame_shape[1]), np.uint8)
    for i in range(num_frames):

        if i % 50 == 0:
            print(f'Loading frame {i} to memory.')
        ret, frame = worm_vid.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        frame = crop(frame, left, right, top, bottom)
        worm_arr[i] = frame

    i = 0
    for frame in worm_arr:
        if i % 50 == 0:
            print(f'Processing frame {i}')
            print(f'Regenerating background using frames {i} to {i+50}.')
            background = np.amax(worm_arr[i:i+50, :, :])
        arr = process_frame(frame, background)
        worm_arr[i] = arr
        if i % 450 == 0:
            save_path = Path(output, f"{base}_{i}.png")
            cv2.imwrite(str(save_path), arr)
        i += 1

    with tp.PandasHDFStoreBig(Path(output, f"{base}.hd5")) as s:
        tp.batch(worm_arr, 19, minmass=1000,
                 output=s)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')

    parser.add_argument('video', type=str,
                        help='Path to the video.')
    parser.add_argument('output', type=str,
                        help='Path to the output directory.')
    parser.add_argument('-l', '--left', type=int,
                        help='Number of cols to remove from the left.')
    parser.add_argument('-r', '--right', type=int,
                        help='Number of cols to remove from the right.')
    parser.add_argument('-t', '--top', type=int,
                        help='Number of cols to remove from the top.')
    parser.add_argument('-b', '--bottom', type=int,
                        help='Number of cols to remove from the bottom.')
    args = parser.parse_args()

    track_batch(args.video,
                args.output,
                args.left,
                args.right,
                args.top,
                args.bottom
                )
