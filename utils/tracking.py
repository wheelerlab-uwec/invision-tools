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


def process_frame(frame, background):
    # gray = rgb2gray(frame)
    sub = (frame - background).astype(np.int8)
    rescale = rescale_intensity(sub,
                                out_range='dtype')
    inv = (255 - rescale).astype(np.uint8)
    smooth = gaussian(inv, sigma=5, preserve_range=True)

    return smooth


def process_chunk(chunk, output):

    background = np.amax(chunk, axis=0)

    for i in range(chunk.shape[0]):
        print(f'Processing {i}th frame of chunk.')
        frame = chunk[i]
        arr = process_frame(frame, background)
        chunk[i] = arr
        if i == 50:
            save_path = Path(output, f'{i}.png')
            cv2.imwrite(str(save_path), arr)

    return chunk


def track_batch(video, output):
    base = Path(output).stem
    os.mkdir(output)
    worm_vid = decord.VideoReader(video, ctx=decord.cpu(0))
    shape = worm_vid[0].shape

    # initialize array of entire video
    vid_arr = np.empty((1, shape[0], shape[1]), np.uint8)

    # load 50 frames into memory
    chunk_size = 100
    chunk = np.zeros((chunk_size, shape[0], shape[1]), np.uint8)
    for c in range(0, int(len(worm_vid) / chunk_size)):
        print(
            f"Processing frames {c * chunk_size + 1} - {c * chunk_size + chunk_size}")
        frame_numbers = range(c * chunk_size + 1, c * chunk_size + chunk_size)
        i = 0
        for frame_number in frame_numbers:
            frame = rgb2gray(worm_vid[frame_number].asnumpy())
            chunk[i] = frame
            i += 1
        processed = process_chunk(chunk, output)
        vid_arr = np.vstack((vid_arr, processed))
        print(vid_arr.shape)

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
