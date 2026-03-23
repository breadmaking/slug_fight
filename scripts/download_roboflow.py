"""Download Roboflow slug datasets and merge with existing Arion Rufus data."""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from roboflow import Roboflow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = PROJECT_ROOT / "datasets" / "roboflow"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.environ.get("ROBOFLOW_API_KEY")
if not api_key:
    raise SystemExit(
        "Set ROBOFLOW_API_KEY first:\n"
        "  export ROBOFLOW_API_KEY=your_key_here\n\n"
        "Get your key at https://app.roboflow.com/settings/api"
    )

rf = Roboflow(api_key=api_key)

datasets = [
    ("projects-gcdfw", "slug-and-snails", 1),  # 1,597 images
    ("f9ki3", "slug-detection", 1),              # 1,139 images
]

for workspace, project, version in datasets:
    print(f"\nDownloading {workspace}/{project} v{version}...")
    ds = rf.workspace(workspace).project(project).version(version)
    ds.download("yolov8", location=str(DOWNLOAD_DIR / project))

print(f"\nDatasets downloaded to {DOWNLOAD_DIR}")
print("Run scripts/merge_datasets.py next to combine everything.")
