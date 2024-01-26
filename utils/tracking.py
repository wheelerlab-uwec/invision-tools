import argparse
import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import trackpy as tp
from PIL import Image
from pathlib import Path
import os
from skimage.filters import gaussian
from skimage.exposure import rescale_intensity
import cv2
import decord

########################################################################
####                                                                ####
####                             tracking                           ####
####                                                                ####
########################################################################


def rgb2gray(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY).astype(np.uint8)
    return gray


def get_background(video, output, i):

    first_frame = video[i]

    first_bit = np.zeros(
        (50, first_frame.shape[0], first_frame.shape[1]), np.uint8)
    j = 0
    for k in range(i, i + 50):
        frame = video[k].asnumpy()
        first_bit[j] = rgb2gray(frame)
        j += 1
        del frame
    max = np.amax(first_bit, axis=0)
    save_path = Path(output, f"background_{i}.png")
    cv2.imwrite(str(save_path), max)

    return max


def process_frame(frame, background):
    gray = rgb2gray(frame)
    sub = (gray - background).astype(np.int8)
    rescale = rescale_intensity(sub,
                                out_range='dtype')
    inv = (255 - rescale).astype(np.uint8)
    smooth = gaussian(inv, sigma=5, preserve_range=True)

    return smooth


def track_batch(video, output):
    base = Path(output).stem
    os.mkdir(output)
    worm_vid = decord.VideoReader(video, ctx=decord.cpu(0))

    # get an initial background
    background = get_background(worm_vid, output, 0)

    vid_arr = np.zeros(
        (len(worm_vid), background.shape[0], background.shape[1]), np.uint8)
    i = 0
    for i in range(len(worm_vid)):
        print(f'Processing frame {i}.')
        frame = worm_vid[i].asnumpy()
        # refresh the background every 50 frames
        if i % 50 == 0:
            background = get_background(worm_vid, output, i)
        arr = process_frame(frame, background)
        vid_arr[i] = arr
        if i % 225 == 0:
            save_path = Path(output, f"{base}_{i}.png")
            cv2.imwrite(str(save_path), arr)
        i += 1

    with tp.PandasHDFStoreBig(Path(output, f"{base}.hd5")) as s:
        tp.batch(vid_arr, 19, minmass=1000,
                 output=s)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')

    parser.add_argument('video', type=str,
                        help='Path to the video.')
    parser.add_argument('output', type=str,
                        help='Path to the output directory.')
    args = parser.parse_args()

    track_batch(args.video,
                args.output
                )
