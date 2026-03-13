"""
Generate max projection backgrounds from video and save to disk.
This pre-computes backgrounds so optimization runs don't need to regenerate them.
"""

import cv2
import numpy as np
from pathlib import Path
from skimage.transform import rescale
import json

def generate_and_save_backgrounds(video_path, 
                                   output_dir,
                                   max_frames=75,
                                   chunk_size=25,
                                   downsample_factor=4):
    """
    Generate max projection backgrounds and save to disk.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save background files
        max_frames: Number of frames to process
        chunk_size: Frames per background chunk
        downsample_factor: Downsampling factor
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    print(f"Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_to_process = min(max_frames, total_frames)
    
    print(f"Total frames in video: {total_frames}")
    print(f"Processing: {frames_to_process} frames")
    print(f"Chunk size: {chunk_size} frames")
    print(f"Downsample factor: {downsample_factor}x")
    
    # Calculate number of chunks
    num_chunks = (frames_to_process + chunk_size - 1) // chunk_size
    print(f"Will generate {num_chunks} background images")
    
    backgrounds = {}
    
    for chunk_idx in range(num_chunks):
        start_frame = chunk_idx * chunk_size
        end_frame = min(start_frame + chunk_size, frames_to_process)
        
        print(f"\nChunk {chunk_idx}: frames {start_frame}-{end_frame}")
        
        # Load chunk frames
        chunk_frames = []
        for frame_num in range(start_frame, end_frame):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                print(f"  Warning: Could not read frame {frame_num}")
                continue
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Downsample
            if downsample_factor > 1:
                gray = rescale(gray, 1.0 / downsample_factor, 
                             anti_aliasing=True, 
                             preserve_range=True).astype(np.uint8)
            
            chunk_frames.append(gray)
        
        if len(chunk_frames) == 0:
            print(f"  ERROR: No frames loaded for chunk {chunk_idx}")
            continue
        
        # Generate max projection background
        background = np.max(chunk_frames, axis=0).astype(np.uint8)
        
        print(f"  Background shape: {background.shape}")
        print(f"  Background range: {background.min()} - {background.max()}")
        
        # Save background
        bg_filename = f"background_chunk{chunk_idx}_frames{start_frame}-{end_frame}.npy"
        bg_path = output_path / bg_filename
        np.save(bg_path, background)
        print(f"  Saved: {bg_filename}")
        
        backgrounds[chunk_idx] = {
            'filename': bg_filename,
            'start_frame': int(start_frame),
            'end_frame': int(end_frame),
            'shape': background.shape
        }
    
    cap.release()
    
    # Save metadata
    metadata = {
        'video_path': str(video_path),
        'max_frames': max_frames,
        'chunk_size': chunk_size,
        'downsample_factor': downsample_factor,
        'num_chunks': num_chunks,
        'backgrounds': backgrounds
    }
    
    metadata_path = output_path / 'backgrounds_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"SUCCESS: Generated {num_chunks} background images")
    print(f"Metadata saved to: {metadata_path}")
    print(f"{'='*60}")
    
    return metadata


if __name__ == "__main__":
    # Generate backgrounds for the test video
    metadata = generate_and_save_backgrounds(
        video_path="test_video.mp4",
        output_dir="./backgrounds",
        max_frames=75,
        chunk_size=25,
        downsample_factor=4
    )
    
    print("\nBackground files created:")
    for chunk_idx, info in metadata['backgrounds'].items():
        print(f"  Chunk {chunk_idx}: {info['filename']}")
