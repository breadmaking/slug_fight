"""Run slug detection on a video file and save annotated output."""

import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = PROJECT_ROOT / "runs" / "slug-detect" / "weights" / "best.pt"


def main():
    parser = argparse.ArgumentParser(description="Detect slugs in a video")
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS), help="Path to YOLO weights")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--out", help="Output video path (default: <input>_detected.mp4)")
    parser.add_argument("--show", action="store_true", help="Show live preview window")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    out_path = Path(args.out) if args.out else video_path.with_stem(video_path.stem + "_detected").with_suffix(".mp4")

    model = YOLO(args.weights)

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    frame_num = 0
    detections_total = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1
        results = model(frame, conf=args.conf, verbose=False)[0]
        detections = len(results.boxes)
        detections_total += detections

        annotated = results.plot()

        writer.write(annotated)

        if args.show:
            cv2.imshow("Slug Detection", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if frame_num % 30 == 0 or frame_num == 1:
            print(f"Frame {frame_num}/{total_frames} | Detections this frame: {detections}")

    cap.release()
    writer.release()
    if args.show:
        cv2.destroyAllWindows()

    print(f"\nDone. {frame_num} frames processed, {detections_total} total detections.")
    print(f"Output saved to: {out_path}")


if __name__ == "__main__":
    main()
