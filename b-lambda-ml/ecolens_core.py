"""Reusable image, video, and ML helpers for the Aussie EcoLens B module."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MD_MODEL_PATH = BASE_DIR / "mdv5a.pt"
DEFAULT_SPECIES_MODEL_PATH = BASE_DIR / "model.pt"
DEFAULT_LABELS_PATH = BASE_DIR / "labels.txt"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

SPECIES_CLASSES = [
    "Alectura_lathami",
    "Antechinus_agilis",
    "Bos_taurus",
    "Burhinus_grallarius",
    "Canis_familiaris",
    "Chalcophaps_longirostris",
    "Colluricincla_harmonica",
    "Corcorax_melanorhamphos",
    "Dacelo_novaeguineae",
    "Dama_dama",
    "Eopsaltria_australis",
    "Felis_catus",
    "Geopelia_humeralis",
    "Gymnorhina_tibicen",
    "Homo_sapiens",
    "Isoodon_macrourus",
    "Lepus_europaeus",
    "Macropus_giganteus",
    "Menura_novaehollandiae",
    "Mus_musculus",
    "Oryctolagus_cuniculus",
    "Perameles_nasuta",
    "Pitta_versicolor",
    "Rattus",
    "Rattus_fuscipes",
    "Rattus_rattus",
    "Strepera_graculina",
    "Sus_scrofa",
    "Tachyglossus_aculeatus",
    "Thylogale_stigmatica",
    "Trichosurus_caninus",
    "Trichosurus_cunninghami",
    "Trichosurus_vulpecula",
    "Varanus_varius",
    "Vombatus_ursinus",
    "Vulpes_vulpes",
    "Wallabia_bicolor",
    "Canis_dingo",
    "Capra_hircus",
    "Casuarius_casuarius",
    "Heteromyias_cinereifrons",
    "Hypsiprymnodon_moschatus",
    "Megapodius_reinwardt",
    "Notamacropus_rufogriseus",
    "Orthonyx_spaldingii",
    "Uromys_caudimaculatus",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def file_type_from_key(key: str) -> str:
    suffix = Path(key).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "unsupported"


def stable_file_id(bucket: str, key: str, checksum: str | None = None) -> str:
    source = checksum if checksum else f"{bucket}/{key}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_s3_url(bucket: str, key: str) -> str:
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def content_type_for_key(key: str) -> str:
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


def parse_s3_event(event: dict[str, Any]) -> list[dict[str, str | None]]:
    """Support both real S3 events and simplified local test events."""
    if "Records" not in event:
        return [
            {
                "bucket": event["bucket"],
                "key": event["key"],
                "checksum": event.get("checksum"),
                "original_url": event.get("original_url"),
                "thumbnail_url": event.get("thumbnail_url"),
            }
        ]

    records = []
    for record in event["Records"]:
        s3 = record["s3"]
        records.append(
            {
                "bucket": s3["bucket"]["name"],
                "key": s3["object"]["key"].replace("+", " "),
                "checksum": record.get("checksum"),
                "original_url": record.get("original_url"),
                "thumbnail_url": record.get("thumbnail_url"),
            }
        )
    return records


def load_label_map(labels_path: str | Path = DEFAULT_LABELS_PATH) -> dict[str, str]:
    label_map: dict[str, str] = {}
    with open(labels_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = [part.strip() for part in line.split(";")]
            if len(parts) < 7:
                continue
            genus, species, common_name = parts[4], parts[5], parts[6]
            if not genus or not species:
                continue
            label_map[f"{genus}_{species}".lower()] = common_name or f"{genus} {species}"
    return label_map


def common_name_for(scientific_name: str, label_map: dict[str, str]) -> str:
    return label_map.get(scientific_name.lower(), scientific_name.replace("_", " ").lower())


def generate_thumbnail(
    source_path: str | Path,
    output_path: str | Path,
    max_dimension: int = 320,
    quality: int = 82,
) -> dict[str, Any]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(output, format="JPEG", quality=quality, optimize=True)
        width, height = image.size

    return {
        "thumbnail_path": str(output),
        "width": width,
        "height": height,
        "content_type": "image/jpeg",
    }


def extract_video_frames(
    video_path: str | Path,
    output_dir: str | Path,
    frames_per_second: int = 1,
) -> list[Path]:
    """Extract frames at 1 fps by default, as required by the assignment."""
    import cv2

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    source_fps = capture.get(cv2.CAP_PROP_FPS) or 1
    frame_interval = max(int(round(source_fps / frames_per_second)), 1)
    frames: list[Path] = []
    frame_index = 0
    saved_index = 0

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % frame_interval == 0:
            frame_path = output / f"frame_{saved_index:04d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            frames.append(frame_path)
            saved_index += 1
        frame_index += 1

    capture.release()
    return frames


def load_md_detector(
    model_path: str | Path = DEFAULT_MD_MODEL_PATH,
    model_cache: dict[str, Any] | None = None,
) -> Any:
    """Load the MegaDetector once and reuse it across warm invocations."""
    from megadetector.detection import run_detector

    if model_cache is not None and "md_detector" in model_cache:
        return model_cache["md_detector"]

    detector = run_detector.load_detector(str(model_path))
    if model_cache is not None:
        model_cache["md_detector"] = detector
    return detector


def run_megadetector(
    image_paths: list[str | Path],
    model_path: str | Path = DEFAULT_MD_MODEL_PATH,
    confidence_threshold: float = 0.05,
    model_cache: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run MegaDetector per image and return batch-style detection entries.

    The output keeps the original `{file, detections:[{category, conf, bbox}]}`
    structure so `crop_detections` works unchanged, but a cached detector is
    reused to avoid reloading the model on every call.
    """
    from megadetector.visualization import visualization_utils as vis_utils

    detector = load_md_detector(model_path, model_cache)
    results: list[dict[str, Any]] = []
    for path in image_paths:
        image = vis_utils.load_image(str(path))
        entry = detector.generate_detections_one_image(
            image,
            image_id=str(path),
            detection_threshold=confidence_threshold,
        )
        entry["file"] = str(path)
        results.append(entry)
    return results


def crop_detections(
    md_entry: dict[str, Any],
    output_dir: str | Path,
    confidence_threshold: float = 0.05,
    snip_size: int = 600,
) -> list[Path]:
    image_path = Path(md_entry["file"])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    crop_paths: list[Path] = []

    with Image.open(image_path).convert("RGB") as image:
        width, height = image.size
        crop_index = 0
        for detection in md_entry.get("detections", []):
            if detection.get("category") != "1":
                continue
            if float(detection.get("conf", 0.0)) < confidence_threshold:
                continue

            x, y, w, h = detection["bbox"]
            left = max(int(x * width), 0)
            top = max(int(y * height), 0)
            right = min(int((x + w) * width), width)
            bottom = min(int((y + h) * height), height)
            if right <= left or bottom <= top:
                continue

            crop = image.crop((left, top, right, bottom)).resize(
                (snip_size, snip_size),
                Image.Resampling.BILINEAR,
            )
            crop_path = output / f"{image_path.stem}-{crop_index}.jpg"
            crop.save(crop_path, format="JPEG", quality=90)
            crop_paths.append(crop_path)
            crop_index += 1

    return crop_paths


def get_torch_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_species_model(
    model_path: str | Path = DEFAULT_SPECIES_MODEL_PATH,
    device: str | None = None,
) -> tuple[Any, str]:
    import torch

    selected_device = device or get_torch_device()
    model = torch.load(model_path, map_location=selected_device, weights_only=False)
    model.eval()
    model.to(selected_device)
    return model, selected_device


def classify_crop(
    image_path: str | Path,
    model: Any,
    device: str,
    classes: list[str] = SPECIES_CLASSES,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    import numpy as np
    import torch
    import torchvision.transforms as transforms

    transform = transforms.Compose(
        [
            transforms.Resize((480, 480)),
            transforms.ToTensor(),
        ]
    )

    with Image.open(image_path).convert("RGB") as image:
        tensor = transform(image).unsqueeze(0).permute(0, 2, 3, 1).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0].cpu().numpy()

    order = np.argsort(probabilities)[::-1][:top_k]
    return [
        {
            "scientific_name": classes[index],
            "confidence": float(probabilities[index]),
            "source": Path(image_path).stem,
        }
        for index in order
    ]


def tag_image(
    image_path: str | Path,
    md_model_path: str | Path = DEFAULT_MD_MODEL_PATH,
    species_model_path: str | Path = DEFAULT_SPECIES_MODEL_PATH,
    labels_path: str | Path = DEFAULT_LABELS_PATH,
    work_dir: str | Path | None = None,
    confidence_threshold: float = 0.05,
    min_species_confidence: float = 0.0,
    model_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    label_map = load_label_map(labels_path)
    owns_tmp = work_dir is None
    tmp_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="ecolens-ml-"))
    crop_dir = tmp_dir / "crops"

    cache = model_cache if model_cache is not None else {}

    md_results = run_megadetector(
        [image_path],
        md_model_path,
        confidence_threshold=confidence_threshold,
        model_cache=cache,
    )
    crop_paths = []
    for entry in md_results:
        crop_paths.extend(crop_detections(entry, crop_dir, confidence_threshold))

    if "species_model" not in cache or "device" not in cache:
        cache["species_model"], cache["device"] = load_species_model(species_model_path)

    predictions: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for crop_path in crop_paths:
        crop_predictions = classify_crop(crop_path, cache["species_model"], cache["device"])
        if not crop_predictions:
            continue
        best = crop_predictions[0]
        common_name = common_name_for(best["scientific_name"], label_map)
        best["common_name"] = common_name
        predictions.append(best)
        if best["confidence"] >= min_species_confidence:
            counts[common_name] += 1

    result = {
        "tags": dict(counts),
        "predictions": predictions,
        "detections": len(crop_paths),
    }

    if owns_tmp:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


def tag_video(
    video_path: str | Path,
    work_dir: str | Path,
    md_model_path: str | Path = DEFAULT_MD_MODEL_PATH,
    species_model_path: str | Path = DEFAULT_SPECIES_MODEL_PATH,
    labels_path: str | Path = DEFAULT_LABELS_PATH,
    model_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frame_dir = Path(work_dir) / "frames"
    frames = extract_video_frames(video_path, frame_dir, frames_per_second=1)
    aggregate_counts: Counter[str] = Counter()
    all_predictions: list[dict[str, Any]] = []

    for frame in frames:
        frame_result = tag_image(
            frame,
            md_model_path=md_model_path,
            species_model_path=species_model_path,
            labels_path=labels_path,
            work_dir=Path(work_dir) / f"ml_{frame.stem}",
            model_cache=model_cache,
        )
        aggregate_counts.update(frame_result["tags"])
        all_predictions.extend(frame_result["predictions"])

    return {
        "tags": dict(aggregate_counts),
        "predictions": all_predictions,
        "frames_processed": len(frames),
    }


def build_metadata_record(
    *,
    bucket: str,
    key: str,
    tags: dict[str, int],
    predictions: list[dict[str, Any]],
    checksum: str | None = None,
    original_url: str | None = None,
    thumbnail_url: str | None = None,
) -> dict[str, Any]:
    file_type = file_type_from_key(key)
    return {
        "status": "ok",
        "file_id": stable_file_id(bucket, key, checksum),
        "file_type": file_type,
        "original_bucket": bucket,
        "original_key": key,
        "original_url": original_url or public_s3_url(bucket, key),
        "thumbnail_url": thumbnail_url,
        "checksum": checksum,
        "tags": tags,
        "predictions": predictions,
        "created_at": utc_now(),
    }


def error_response(error_type: str, message: str, bucket: str | None = None, key: str | None = None) -> dict[str, Any]:
    return {
        "status": "error",
        "error_type": error_type,
        "message": message,
        "bucket": bucket,
        "key": key,
        "created_at": utc_now(),
    }


def write_json(path: str | Path, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
