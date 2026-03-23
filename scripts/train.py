"""Fine-tune YOLOv8n on the slug detection dataset."""

from pathlib import Path

import yaml
from ultralytics import YOLO  # type: ignore[attr-defined]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "datasets" / "slug-detection"
DATASET_YAML_SRC = DATASET_DIR / "dataset.yaml"

resolved_yaml = DATASET_DIR / "dataset.resolved.yaml"
with open(DATASET_YAML_SRC) as f:
    cfg = yaml.safe_load(f)
cfg["path"] = str(DATASET_DIR)
with open(resolved_yaml, "w") as f:
    yaml.dump(cfg, f, default_flow_style=False)

model = YOLO("yolov8n.pt")

model.train(
    data=str(resolved_yaml),
    epochs=50,
    imgsz=640,
    batch=16,
    project=str(PROJECT_ROOT / "runs"),
    name="slug-detect",
    exist_ok=True,
)
