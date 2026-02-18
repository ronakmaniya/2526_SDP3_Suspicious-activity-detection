"""
Dataset Preparation Utility.
Extracts frames from video files and organizes them for training.

Usage:
    python prepare_dataset.py --input_dir /path/to/raw_videos --output_dir /path/to/dataset

Expected input structure:
    raw_videos/
    ├── normal/
    │   ├── video1.mp4
    │   ├── video2.mp4
    │   └── ...
    └── suspicious/
        ├── video1.mp4
        └── ...

Output structure:
    dataset/
    ├── train/
    │   ├── normal/
    │   │   ├── video1/
    │   │   │   ├── frame_0001.jpg
    │   │   │   └── ...
    │   │   └── video2/
    │   └── suspicious/
    └── val/
        ├── normal/
        └── suspicious/
"""
import argparse
import os
import random
from pathlib import Path

import cv2


def extract_frames(video_path, output_dir, max_frames=None, target_fps=None):
    """Extract frames from a video file."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  ERROR: Cannot open {video_path}")
        return 0

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 24
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate frame sampling interval
    if target_fps and target_fps < video_fps:
        sample_interval = int(video_fps / target_fps)
    else:
        sample_interval = 1

    os.makedirs(output_dir, exist_ok=True)

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        if frame_count % sample_interval != 0:
            continue

        if max_frames and saved_count >= max_frames:
            break

        saved_count += 1
        frame_path = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
        cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    cap.release()
    return saved_count


def main():
    parser = argparse.ArgumentParser(description='Prepare video dataset for training')
    parser.add_argument('--input_dir', type=str, required=True, help='Input directory with raw videos')
    parser.add_argument('--output_dir', type=str, required=True, help='Output directory for extracted frames')
    parser.add_argument('--val_split', type=float, default=0.2, help='Validation split ratio')
    parser.add_argument('--target_fps', type=float, default=8, help='Target FPS for frame extraction')
    parser.add_argument('--max_frames', type=int, default=300, help='Max frames per video')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    random.seed(args.seed)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    for label in ['normal', 'suspicious']:
        label_dir = input_dir / label
        if not label_dir.exists():
            print(f"Warning: {label_dir} not found, skipping")
            continue

        videos = sorted([
            f for f in label_dir.iterdir()
            if f.suffix.lower() in ('.mp4', '.avi', '.mov', '.mkv', '.wmv')
        ])

        print(f"\n{'='*50}")
        print(f"Processing {label}: {len(videos)} videos")
        print(f"{'='*50}")

        # Split into train/val
        random.shuffle(videos)
        val_count = max(1, int(len(videos) * args.val_split))
        val_videos = videos[:val_count]
        train_videos = videos[val_count:]

        for split, video_list in [('train', train_videos), ('val', val_videos)]:
            for video_path in video_list:
                video_name = video_path.stem
                frame_output = output_dir / split / label / video_name

                print(f"  [{split}] {video_path.name} -> {frame_output}")
                count = extract_frames(
                    video_path, str(frame_output),
                    max_frames=args.max_frames,
                    target_fps=args.target_fps
                )
                print(f"    Extracted {count} frames")

    print(f"\n✅ Dataset prepared at: {output_dir}")
    print(f"Structure:")
    for split in ['train', 'val']:
        for label in ['normal', 'suspicious']:
            p = output_dir / split / label
            if p.exists():
                dirs = list(p.iterdir())
                print(f"  {split}/{label}: {len(dirs)} clips")


if __name__ == '__main__':
    main()
