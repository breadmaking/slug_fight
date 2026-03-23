"""Merge Arion Rufus + Roboflow datasets into a single unified dataset.

Roboflow datasets may have multiple classes (e.g. slug=0, snail=1).
We remap everything to a single class 0 (slug) since the model only
needs to detect things to salt.
"""

import random
import shutil
from pathlib import Path

SEED = 42
TRAIN_RATIO = 0.80
VALID_RATIO = 0.15

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "datasets" / "slug-detection"

SOURCES = [
    # (image_dir, label_dir, description)
    # Arion Rufus — raw images and labels side by side
    (
        PROJECT_ROOT / "datasets" / "arion-rufus" / "raw",
        PROJECT_ROOT / "datasets" / "arion-rufus" / "raw",
        "arion-rufus",
    ),
]

# Roboflow datasets have train/valid/test splits already — gather all of them
ROBOFLOW_DIR = PROJECT_ROOT / "datasets" / "roboflow"
for ds_dir in sorted(ROBOFLOW_DIR.iterdir()) if ROBOFLOW_DIR.exists() else []:
    if not ds_dir.is_dir():
        continue
    for split in ("train", "valid", "test"):
        img_dir = ds_dir / split / "images"
        lbl_dir = ds_dir / split / "labels"
        if img_dir.exists() and lbl_dir.exists():
            SOURCES.append((img_dir, lbl_dir, f"roboflow-{ds_dir.name}-{split}"))


def remap_labels(label_path: Path) -> str:
    """Remap all class IDs to 0 (slug)."""
    lines = label_path.read_text().strip().splitlines()
    remapped = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            parts[0] = "0"
            remapped.append(" ".join(parts))
    return "\n".join(remapped) + "\n" if remapped else ""


def collect_all_samples() -> list[tuple[Path, Path, str]]:
    """Return list of (image_path, label_path, unique_prefix) tuples."""
    samples = []
    for img_dir, lbl_dir, source_name in SOURCES:
        for img_path in sorted(img_dir.glob("*.jpg")):
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            if lbl_path.exists():
                prefix = f"{source_name}_{img_path.stem}"
                samples.append((img_path, lbl_path, prefix))
        # Also check for png images (some Roboflow datasets use png)
        for img_path in sorted(img_dir.glob("*.png")):
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            if lbl_path.exists():
                prefix = f"{source_name}_{img_path.stem}"
                samples.append((img_path, lbl_path, prefix))
    return samples


def main():
    samples = collect_all_samples()
    print(f"Total samples found: {len(samples)}")

    random.seed(SEED)
    random.shuffle(samples)

    n = len(samples)
    train_end = int(n * TRAIN_RATIO)
    valid_end = int(n * (TRAIN_RATIO + VALID_RATIO))

    splits = {
        "train": samples[:train_end],
        "valid": samples[train_end:valid_end],
        "test": samples[valid_end:],
    }

    # Clean existing split directories
    for split in splits:
        for sub in ("images", "labels"):
            d = OUT_DIR / split / sub
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)

    for split, split_samples in splits.items():
        for img_path, lbl_path, prefix in split_samples:
            suffix = img_path.suffix
            dst_img = OUT_DIR / split / "images" / f"{prefix}{suffix}"
            dst_lbl = OUT_DIR / split / "labels" / f"{prefix}.txt"

            shutil.copy2(img_path, dst_img)
            # Write remapped labels (all classes → 0)
            dst_lbl.write_text(remap_labels(lbl_path))

        print(f"{split}: {len(split_samples)} images")

    print(f"\nMerged dataset written to {OUT_DIR}")
    print("Run 'uv run python scripts/train.py' to retrain.")


if __name__ == "__main__":
    main()
