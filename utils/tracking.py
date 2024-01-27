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


def track_batch(video, output):
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

        print(f'Loading frame {i} to memory.')
        ret, frame = worm_vid.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        worm_arr[i] = frame

    print('Calculating background.')
    background = np.amax(worm_arr, axis=0)

    i = 0
    for frame in worm_arr:
        print(f'Processing frame {i}')
        arr = process_frame(frame, background)
        worm_arr[i] = arr
        if i % 450 == 0:
            save_path = Path(output, f"{base}_{i}.png")
            cv2.imwrite(str(save_path), arr)
        i += 1

    with tp.PandasHDFStoreBig(Path(output, f"{base}.hd5")) as s:
        for image in worm_arr:
            tp.batch(worm_arr, 19, minmass=1000,
                     output=s)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Track objects in an InVision video.')

    parser.add_argument('video', type=str,
                        help='Path to the video.')
    parser.add_argument('output', type=str,
                        help='Path to the output directory.')
    # parser.add_argument('camera', type=str,
    #                     help='"left" or "right" camera.')
    args = parser.parse_args()

    track_batch(args.video,
                args.output
                # args.camera
                )
