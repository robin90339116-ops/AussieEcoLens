"""Local utilities for testing the B module without AWS."""

from __future__ import annotations

import argparse
from pathlib import Path

from ecolens_core import build_metadata_record, file_type_from_key, sha256_file, write_json
from ml_lambda import process_local_file
from thumbnail_lambda import create_thumbnail_for_local_file


def run_thumbnail_test(image_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = output_dir / f"thumbnail_{image_path.stem}.jpg"
    thumbnail = create_thumbnail_for_local_file(image_path, thumbnail_path)
    return {
        "source": str(image_path),
        "source_bytes": image_path.stat().st_size,
        "thumbnail": thumbnail,
        "thumbnail_bytes": thumbnail_path.stat().st_size,
        "compression_ratio": round(thumbnail_path.stat().st_size / image_path.stat().st_size, 4),
    }


def run_metadata_sample(image_path: Path) -> dict:
    checksum = sha256_file(image_path)
    return build_metadata_record(
        bucket="local-demo-bucket",
        key=f"uploads/{image_path.name}",
        checksum=checksum,
        original_url=f"file://{image_path}",
        thumbnail_url=f"file://thumbnail_{image_path.stem}.jpg",
        tags={"example species": 1},
        predictions=[
            {
                "scientific_name": "Example_species",
                "common_name": "example species",
                "confidence": 0.99,
                "source": image_path.stem,
            }
        ],
    )


def run_ml_test(image_path: Path, output_dir: Path) -> dict:
    checksum = sha256_file(image_path)
    return process_local_file(
        image_path,
        bucket="local-demo-bucket",
        key=f"uploads/{image_path.name}",
        checksum=checksum,
        original_url=f"file://{image_path}",
        thumbnail_url=f"file://{output_dir / f'thumbnail_{image_path.stem}.jpg'}",
        persist=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Local tests for Aussie EcoLens B module.")
    parser.add_argument("--image", default="../test_images/Alectura_lathami_1.JPG")
    parser.add_argument("--output-dir", default="./local_test_output")
    parser.add_argument(
        "--mode",
        choices=["thumbnail", "metadata-sample", "ml"],
        default="thumbnail",
        help="Use 'ml' only when model dependencies are installed.",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    output_dir = Path(args.output_dir)
    if file_type_from_key(image_path.name) != "image":
        raise ValueError("local_test.py expects an image for thumbnail and metadata tests")

    if args.mode == "thumbnail":
        result = run_thumbnail_test(image_path, output_dir)
    elif args.mode == "metadata-sample":
        result = run_metadata_sample(image_path)
    else:
        result = run_ml_test(image_path, output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.mode}_result.json"
    write_json(output_file, result)
    print(f"Wrote {output_file}")
    print(result)


if __name__ == "__main__":
    main()
