"""Local batch runner for the refactored Aussie EcoLens ML pipeline.

This script is intentionally small. The reusable logic lives in `ecolens_core.py`
so that Lambda handlers, Docker containers, and local tests use the same code.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ecolens_core import (
    DEFAULT_LABELS_PATH,
    DEFAULT_MD_MODEL_PATH,
    DEFAULT_SPECIES_MODEL_PATH,
    file_type_from_key,
    generate_thumbnail,
    tag_image,
    tag_video,
    write_json,
)


def process_path(input_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_type = file_type_from_key(input_path.name)
    work_dir = output_dir / input_path.stem

    thumbnail = None
    if file_type == "image":
        thumbnail_path = output_dir / "thumbnails" / f"{input_path.stem}.jpg"
        thumbnail = generate_thumbnail(input_path, thumbnail_path)
        ml_result = tag_image(
            input_path,
            md_model_path=DEFAULT_MD_MODEL_PATH,
            species_model_path=DEFAULT_SPECIES_MODEL_PATH,
            labels_path=DEFAULT_LABELS_PATH,
            work_dir=work_dir,
        )
    elif file_type == "video":
        ml_result = tag_video(
            input_path,
            work_dir=work_dir,
            md_model_path=DEFAULT_MD_MODEL_PATH,
            species_model_path=DEFAULT_SPECIES_MODEL_PATH,
            labels_path=DEFAULT_LABELS_PATH,
        )
    else:
        return {
            "file": str(input_path),
            "status": "skipped",
            "reason": "unsupported file type",
        }

    return {
        "file": str(input_path),
        "status": "ok",
        "file_type": file_type,
        "thumbnail": thumbnail,
        "tags": ml_result["tags"],
        "predictions": ml_result["predictions"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Aussie EcoLens ML locally.")
    parser.add_argument("--input-dir", default="../test_images", help="Directory of media files")
    parser.add_argument("--output-dir", default="./batch_output", help="Output directory")
    parser.add_argument("--limit", type=int, default=0, help="Optional number of files to process")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    files = sorted(path for path in input_dir.iterdir() if path.is_file())
    if args.limit:
        files = files[: args.limit]

    results = [process_path(path, output_dir) for path in files]
    write_json(output_dir / "batch_results.json", results)
    print(f"Processed {len(results)} files. Results: {output_dir / 'batch_results.json'}")


if __name__ == "__main__":
    main()
