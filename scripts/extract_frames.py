"""Extract frames from videos at a given interval for annotation."""

import argparse
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "videos"
OUTPUT_DIR = PROJECT_ROOT / "datasets" / "slug-detection" / "new_frames"


def main():
    parser = argparse.ArgumentParser(description="Extract frames from videos")
    parser.add_argument("--interval", type=int, default=30, help="Extract every Nth frame (default: 30)")
    parser.add_argument("--videos", nargs="*", help="Specific video files (default: all in videos/)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.videos:
        video_paths = [Path(v) for v in args.videos]
    else:
        video_paths = sorted(p for p in VIDEOS_DIR.glob("*.mp4") if "_detected" not in p.stem)

    total_extracted = 0

    for video_path in video_paths:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_num = 0
        extracted = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % args.interval == 0:
                out_name = f"{video_path.stem}_{frame_num:06d}.jpg"
                cv2.imwrite(str(OUTPUT_DIR / out_name), frame)
                extracted += 1

            frame_num += 1

        cap.release()
        print(f"{video_path.name}: {extracted} frames extracted (every {args.interval} frames, {fps:.0f} fps source)")
        total_extracted += extracted

    print(f"\nTotal: {total_extracted} frames saved to {OUTPUT_DIR}")
    print("Next step: annotate these frames with bounding boxes (e.g. Label Studio, Roboflow, CVAT)")


if __name__ == "__main__":
    main()
