import cv2
import argparse
import imgstore as im
import numpy as np
from PIL import Image
import time
import shutil
import argparse
from pathlib import Path
from skimage import exposure
import os
from tqdm import tqdm


def cat_stores(left, right, output, length, skip, annotate, resize, rescale):

    right = im.new_for_filename(str(Path.joinpath(Path.cwd(), right)))
    left = im.new_for_filename(str(Path.joinpath(Path.cwd(), left)))

    if length == -1:
        length = right.frame_count

    print(
        f"Concatenating imgstores. Final array will include {int(length / skip)} frames.")

    with tqdm(total=length/skip) as pbar:

        first_frame, (frame_number, frame_timestamp) = left.get_next_image()
        left_width, height = (
            int(first_frame.shape[1]), int(first_frame.shape[0]))
        right_width = int(right.get_next_image()[0].shape[1])
        vid_shape = (int(length / skip), left_width + right_width, height)

        merged_store = im.new_for_format('tif',
                                         mode='w',
                                         basedir=f'{output}',
                                         imgshape=vid_shape, imgdtype='uint16',
                                         chunksize=1000)

        for i in range(0, length, skip):
            left_frame, (frame_number, frame_timestamp) = left.get_image(
                frame_number=None, frame_index=i)
            right_frame, (frame_number, frame_timestamp) = right.get_image(
                frame_number=None, frame_index=i)
            if rescale:
                rescaled_left = exposure.rescale_intensity(
                    left_frame, (0, np.amax(right_frame)))
                merged_array = np.uint16(
                    np.hstack((rescaled_left, right_frame)))
            else:
                merged_array = np.uint16(np.hstack((left_frame, right_frame)))

            if resize and annotate:
                res = cv2.resize(merged_array, dsize=(800, 267),
                                 interpolation=cv2.INTER_LINEAR)
                hours, remainder = divmod(i, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                cv2.putText(res, f"t = {time_str}", (25, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, 1)
            elif resize and not annotate:
                res = cv2.resize(merged_array, dsize=(800, 267),
                                 interpolation=cv2.INTER_LINEAR)
            elif annotate and not resize:
                res = merged_array
                hours, remainder = divmod(i, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                cv2.putText(merged_array, f"t = {time_str}", (25, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, 1)
            else:
                res = merged_array

            merged_store.add_image(res, i, time.time())

            pbar.update(1)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Concatenate two imgstores from tandem cameras.')

    # Add command line arguments here
    parser.add_argument('left', type=str,
                        help='Path to the imgstore (directory) from the left camera.')
    parser.add_argument('right', type=str,
                        help='Path to the imgstore (directory) from the right camera.')
    parser.add_argument('output', type=str,
                        help='Name of the directory to write the new imgstore.')
    parser.add_argument('-l', '--length', type=int, default=-1,
                        help='Specify the number of frames to concatenate.')
    parser.add_argument('-s', '--skip', type=int, default=1,
                        help='Specify the interval of frames to skip (for down-sampling long videos).')
    parser.add_argument('-a', '--annotate', action='store_true', default=False,
                        help='Specify the interval of frames to skip (for down-sampling long videos).')
    parser.add_argument('-r', '--resize', action='store_true', default=False,
                        help='Resize the concatenated output to 800x267.')
    parser.add_argument('--rescale', action='store_true', default=False,
                        help='Attempt to rescale the image histograms to match each other.')

    args = parser.parse_args()

    if os.path.exists(args.output):
        shutil.rmtree(args.output)

    cat_stores(args.left,
               args.right,
               args.output,
               args.length,
               args.skip,
               args.annotate,
               args.resize,
               args.rescale)
