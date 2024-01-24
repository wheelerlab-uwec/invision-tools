import argparse
import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import trackpy as tp
import numba
import pims
from PIL import Image
from pathlib import Path
import os
from skimage.filters import threshold_otsu, gaussian
from skimage.exposure import rescale_intensity

########################################################################
####                                                                ####
####                             tracking                           ####
####                                                                ####
########################################################################


# convert RGB image to greyscale uint8
def rgb2gray(rgb):
    gray = np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140])
    return gray.astype(np.uint8)


def get_background(video, output, camera):

    # output base
    base = Path(output).stem

    # read video
    worm_vid = pims.PyAVVideoReader(video)

    # np array slicing to remove pixels from top, bottom, and left side
    if camera == 'left':
        test_frame = rgb2gray(worm_vid[0][500:-100, 250:])
    else:
        test_frame = rgb2gray(worm_vid[0][300:-300, :])

    # grab the first 25 frames and get the maximum projection
    first_bit = np.zeros(
        (25, test_frame.shape[0], test_frame.shape[1]), np.uint8)
    for i in range(0, 25):
        if camera == 'left':
            frame = rgb2gray(worm_vid[i][500:-100, 250:])
        else:
            frame = rgb2gray(worm_vid[i][300:-300, :])
        first_bit[i] = frame
    max = np.amax(first_bit, axis=0)
    im = Image.fromarray(max)
    im = im.convert("L")
    save_path = Path(base, f"{base}_background.png")
    im.save(save_path)

    return max, test_frame


def process_image(video, output, camera):

    # output base
    base = Path(output).stem
    os.mkdir(base)

    # read video
    worm_vid = pims.PyAVVideoReader(video)

    max, test_frame = get_background(video, output, camera)

    arr = np.zeros(
        (len(worm_vid), test_frame.shape[0], test_frame.shape[1]), np.uint8)
    for i in range(0, len(worm_vid)):
        print(f"Processing frame {i}.")
        if camera == 'left':
            frame = rgb2gray(worm_vid[i][500:-100, 250:])
        else:
            frame = rgb2gray(worm_vid[i][300:-300, :])
        sub = (frame - max).astype(np.int8)
        rescale = rescale_intensity(sub, out_range=(0, 255))
        inv = (255 - rescale).astype(np.uint8)
        smooth = gaussian(inv, sigma=5, preserve_range=True)
        arr[i] = smooth
        if i % 900 == 0:
            im = Image.fromarray(smooth)
            im = im.convert("L")
            save_path = Path(base, f"{base}_{i}.png")
            im.save(save_path)

    return arr


def track_batch(video, output, camera):

    arr = process_image(video, output, camera)

    with tp.PandasHDFStoreBig(output) as s:
        tp.batch(arr, 35, invert=True,
                 maxsize=9, minmass=1000, topn=50,
                 output=s)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')

    parser.add_argument('video', type=str,
                        help='Path to the video.')
    parser.add_argument('output', type=str,
                        help='Path to the output.')
    parser.add_argument('camera', type=str,
                        help='"left" or "right" camera.')
    args = parser.parse_args()

    track_batch(args.video,
                args.output,
                args.camera)
