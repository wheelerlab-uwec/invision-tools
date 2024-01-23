import argparse
import imgstore as im
import time
import shutil
from pathlib import Path
import os
from tqdm import tqdm


def store_to_seq(store, output):

    store = im.new_for_filename(str(Path.joinpath(Path.cwd(), store)))
    length = store.frame_count

    with tqdm(total=length) as pbar:

        first_frame, (frame_number, frame_timestamp) = store.get_next_image()
        width, height = (
            int(first_frame.shape[1]), int(first_frame.shape[0]))
        vid_shape = (int(length), width, height)

        merged_store = im.new_for_format('tif',
                                         mode='w',
                                         basedir=f'{output}',
                                         imgshape=vid_shape, imgdtype='uint8',
                                         chunksize=1000)

        for i in range(0, length):
            frame, (frame_number, frame_timestamp) = store.get_image(
                frame_number=None, frame_index=i)

            merged_store.add_image(frame, i, time.time())
            pbar.update(1)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Convert a store to a TIFF sequence.')

    # Add command line arguments here
    parser.add_argument('store', type=str,
                        help='Path to the imgstore (directory).')
    parser.add_argument('output', type=str,
                        help='Path to the output.')

    args = parser.parse_args()

    store_to_seq(args.store,
                 args.output)
