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
@pims.pipeline
def rgb2gray(rgb):
    gray = np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140])
    return gray.astype(np.uint8)


@pims.pipeline
def crop(video, camera):
    if camera == 'left':
        cropped = pims.process.crop(video, ((300, 100), (250, 0)))
    else:
        cropped = pims.process.crop(video, ((200, 200), (0, 0)))
    return cropped


def get_background(video, output):

    base = Path(output).stem
    first_frame = video[0]

    first_bit = np.zeros(
        (25, first_frame.shape[0], first_frame.shape[1]), np.uint8)
    for i in range(0, 25):
        first_bit[i] = rgb2gray(video[i])
    max = np.amax(first_bit, axis=0)
    im = Image.fromarray(max)
    im = im.convert("L")
    save_path = Path(output, f"{base}_background.png")
    im.save(save_path)

    return max


def process_frame(frame, camera, background):
    gray = rgb2gray(frame)
    cropped = crop(gray, camera)
    sub = (cropped - background).astype(np.int8)
    rescale = rescale_intensity(sub, out_range=(0, 255))
    inv = (255 - rescale).astype(np.uint8)
    smooth = gaussian(inv, sigma=5, preserve_range=True)

    return smooth


def track_batch(video, output, camera):
    base = Path(output).stem
    os.mkdir(output)
    worm_vid = pims.PyAVVideoReader(video)
    worm_vid = worm_vid[0:50]

    background = get_background(worm_vid, output)
    background = crop(background, camera)

    vid_arr = np.zeros(
        (len(worm_vid), background.shape[0], background.shape[1]))
    i = 0
    for frame in worm_vid:
        print(f'Processing frame {i}.')
        arr = process_frame(frame, camera, background)
        vid_arr[i] = arr
        if i % 1 == 0:
            im = Image.fromarray(arr)
            im = im.convert("L")
            save_path = Path(output, f"{base}_{i}.png")
            im.save(save_path)
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
    parser.add_argument('camera', type=str,
                        help='"left" or "right" camera.')
    args = parser.parse_args()

    track_batch(args.video,
                args.output,
                args.camera)
