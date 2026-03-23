"""Split the Arion Rufus dataset into train/valid/test sets (80/15/5)."""

import random
import shutil
from pathlib import Path

SEED = 42
TRAIN_RATIO = 0.80
VALID_RATIO = 0.15

RAW_DIR = Path(__file__).resolve().parent.parent / "datasets" / "arion-rufus" / "raw"
OUT_DIR = Path(__file__).resolve().parent.parent / "datasets" / "slug-detection"

random.seed(SEED)

stems = sorted(
    s.stem for s in RAW_DIR.glob("*.jpg") if (RAW_DIR / f"{s.stem}.txt").exists()
)
random.shuffle(stems)

n = len(stems)
train_end = int(n * TRAIN_RATIO)
valid_end = int(n * (TRAIN_RATIO + VALID_RATIO))

splits = {
    "train": stems[:train_end],
    "valid": stems[train_end:valid_end],
    "test": stems[valid_end:],
}

for split, split_stems in splits.items():
    img_dir = OUT_DIR / split / "images"
    lbl_dir = OUT_DIR / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    for stem in split_stems:
        shutil.copy2(RAW_DIR / f"{stem}.jpg", img_dir / f"{stem}.jpg")
        shutil.copy2(RAW_DIR / f"{stem}.txt", lbl_dir / f"{stem}.txt")

    print(f"{split}: {len(split_stems)} images")

print(f"\nDataset written to {OUT_DIR}")
