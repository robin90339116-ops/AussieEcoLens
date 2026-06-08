"""FastAPI ML inference service for the Aussie EcoLens B module (Oracle/OCI deployment).

This service runs the heavy MegaDetector + SpeciesNet inference on an Oracle Cloud
compute instance instead of AWS Lambda. A lightweight AWS Lambda (see
`s3_trigger_lambda.py`) is still triggered by S3 ObjectCreated events and forwards
work here, keeping the "upload triggers a serverless function" requirement while
moving the expensive compute to Oracle.

Endpoints:
- GET  /health            : liveness + model load status
- POST /v1/tag/s3         : tag an image/video referenced by a (presigned) URL
- POST /v1/tag/upload     : tag an uploaded file directly (used for query-by-file)
- POST /v1/thumbnail/s3   : generate a thumbnail from a (presigned) URL

Authentication:
- All /v1/* routes require `Authorization: Bearer <token>`.
- The expected token is `API_AUTH_TOKEN`. This is where the AWS Cognito token (or a
  shared secret derived from the authenticated session) is passed through from the
  AWS side to authorise cross-cloud requests.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ecolens_core import (
    DEFAULT_LABELS_PATH,
    DEFAULT_MD_MODEL_PATH,
    DEFAULT_SPECIES_MODEL_PATH,
    build_metadata_record,
    error_response,
    file_type_from_key,
    generate_thumbnail,
    load_md_detector,
    load_species_model,
    public_s3_url,
    sha256_file,
    tag_image,
    tag_video,
)

MD_MODEL_PATH = Path(os.getenv("MD_MODEL_PATH", str(DEFAULT_MD_MODEL_PATH)))
SPECIES_MODEL_PATH = Path(os.getenv("SPECIES_MODEL_PATH", str(DEFAULT_SPECIES_MODEL_PATH)))
LABELS_PATH = Path(os.getenv("LABELS_PATH", str(DEFAULT_LABELS_PATH)))
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")
THUMBNAIL_BUCKET = os.getenv("THUMBNAIL_BUCKET")
THUMBNAIL_PREFIX = os.getenv("THUMBNAIL_PREFIX", "thumbnails/")
METADATA_API_URL = os.getenv("METADATA_API_URL")
PRELOAD_MODELS = os.getenv("PRELOAD_MODELS", "true").lower() == "true"
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))

MODEL_CACHE: dict[str, Any] = {}


def _preload_models() -> None:
    load_md_detector(MD_MODEL_PATH, MODEL_CACHE)
    MODEL_CACHE["species_model"], MODEL_CACHE["device"] = load_species_model(SPECIES_MODEL_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if PRELOAD_MODELS:
        try:
            _preload_models()
            MODEL_CACHE["loaded"] = True
        except Exception as exc:  # pragma: no cover - startup diagnostics
            MODEL_CACHE["loaded"] = False
            MODEL_CACHE["load_error"] = str(exc)
    yield
    MODEL_CACHE.clear()


app = FastAPI(title="Aussie EcoLens ML Service", version="1.0.0", lifespan=lifespan)


def require_token(authorization: str | None = Header(default=None)) -> None:
    """Validate the bearer token passed from the AWS side."""
    if not API_AUTH_TOKEN:
        # No token configured: allow (development only). Production should always set one.
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def _persist_metadata(record: dict[str, Any]) -> bool:
    if not METADATA_API_URL:
        return False
    import json
    from urllib.request import Request

    body = json.dumps(record).encode("utf-8")
    request = Request(
        METADATA_API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        response.read()
    return True


def _download_to_temp(url: str, suffix: str, tmp_dir: Path) -> Path:
    local_path = tmp_dir / f"{uuid.uuid4().hex}{suffix}"
    with urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response, open(local_path, "wb") as out:
        out.write(response.read())
    return local_path


def _thumbnail_url_for(bucket: str, key: str, provided: str | None) -> str | None:
    if provided:
        return provided
    if file_type_from_key(key) != "image":
        return None
    thumb_bucket = THUMBNAIL_BUCKET or bucket
    thumb_key = f"{THUMBNAIL_PREFIX.rstrip('/')}/{Path(key).stem}.jpg"
    return public_s3_url(thumb_bucket, thumb_key)


def _run_inference(local_path: Path, work_dir: Path) -> dict[str, Any]:
    file_type = file_type_from_key(local_path.name)
    if file_type == "image":
        return tag_image(
            local_path,
            md_model_path=MD_MODEL_PATH,
            species_model_path=SPECIES_MODEL_PATH,
            labels_path=LABELS_PATH,
            work_dir=work_dir,
            model_cache=MODEL_CACHE,
        )
    return tag_video(
        local_path,
        work_dir=work_dir,
        md_model_path=MD_MODEL_PATH,
        species_model_path=SPECIES_MODEL_PATH,
        labels_path=LABELS_PATH,
        model_cache=MODEL_CACHE,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "models_loaded": bool(MODEL_CACHE.get("loaded")),
        "load_error": MODEL_CACHE.get("load_error"),
        "auth_required": bool(API_AUTH_TOKEN),
    }


@app.post("/v1/tag/s3", dependencies=[Depends(require_token)])
def tag_s3(payload: dict[str, Any]) -> JSONResponse:
    bucket = payload.get("bucket")
    key = payload.get("key")
    image_url = payload.get("image_url") or payload.get("presigned_url")
    if not bucket or not key:
        return JSONResponse(status_code=400, content=error_response("InvalidRequest", "bucket and key are required"))

    file_type = file_type_from_key(key)
    if file_type == "unsupported":
        return JSONResponse(status_code=415, content=error_response("UnsupportedFileType", "Only image and video files are supported", bucket, key))
    if not image_url:
        return JSONResponse(status_code=400, content=error_response("InvalidRequest", "image_url (presigned URL) is required", bucket, key))

    with tempfile.TemporaryDirectory(prefix="ecolens-svc-") as tmp:
        tmp_dir = Path(tmp)
        try:
            local_path = _download_to_temp(image_url, Path(key).suffix, tmp_dir)
        except Exception as exc:
            return JSONResponse(status_code=502, content=error_response("DownloadFailed", str(exc), bucket, key))

        # Compute the SHA-256 checksum over the exact bytes stored in S3 so it
        # matches the frontend's SHA-256 (used for cross-module de-duplication).
        # A caller-provided checksum (if any) takes precedence.
        checksum = payload.get("checksum") or sha256_file(local_path)

        try:
            ml_result = _run_inference(local_path, tmp_dir / "work")
        except Exception as exc:
            return JSONResponse(status_code=500, content=error_response(type(exc).__name__, str(exc), bucket, key))

        record = build_metadata_record(
            bucket=bucket,
            key=key,
            tags=ml_result["tags"],
            predictions=ml_result["predictions"],
            checksum=checksum,
            original_url=payload.get("original_url"),
            thumbnail_url=_thumbnail_url_for(bucket, key, payload.get("thumbnail_url")),
        )
        if file_type == "video":
            record["frames_processed"] = ml_result.get("frames_processed", 0)
        else:
            record["detections"] = ml_result.get("detections", 0)

        try:
            record["persisted"] = _persist_metadata(record)
        except Exception as exc:
            record["persisted"] = False
            record["persist_error"] = str(exc)

    return JSONResponse(content=record)


@app.post("/v1/tag/upload", dependencies=[Depends(require_token)])
async def tag_upload(file: UploadFile = File(...), persist: bool = Form(default=False)) -> JSONResponse:
    """Tag a directly uploaded file. Used for the query-by-file feature.

    The uploaded file is never stored permanently here and is not persisted to the
    database unless `persist` is explicitly true.
    """
    filename = file.filename or "upload.jpg"
    file_type = file_type_from_key(filename)
    if file_type == "unsupported":
        return JSONResponse(status_code=415, content=error_response("UnsupportedFileType", "Only image and video files are supported", key=filename))

    with tempfile.TemporaryDirectory(prefix="ecolens-upload-") as tmp:
        tmp_dir = Path(tmp)
        local_path = tmp_dir / Path(filename).name
        local_path.write_bytes(await file.read())
        checksum = sha256_file(local_path)
        try:
            ml_result = _run_inference(local_path, tmp_dir / "work")
        except Exception as exc:
            return JSONResponse(status_code=500, content=error_response(type(exc).__name__, str(exc), key=filename))

    return JSONResponse(
        content={
            "status": "ok",
            "file_type": file_type,
            "checksum": checksum,
            "tags": ml_result["tags"],
            "predictions": ml_result["predictions"],
        }
    )


@app.post("/v1/thumbnail/s3", dependencies=[Depends(require_token)])
def thumbnail_s3(payload: dict[str, Any]) -> JSONResponse:
    bucket = payload.get("bucket")
    key = payload.get("key")
    image_url = payload.get("image_url") or payload.get("presigned_url")
    if not bucket or not key or not image_url:
        return JSONResponse(status_code=400, content=error_response("InvalidRequest", "bucket, key and image_url are required"))
    if file_type_from_key(key) != "image":
        return JSONResponse(status_code=415, content=error_response("UnsupportedFileType", "Thumbnails support images only", bucket, key))

    with tempfile.TemporaryDirectory(prefix="ecolens-thumb-") as tmp:
        tmp_dir = Path(tmp)
        try:
            local_path = _download_to_temp(image_url, Path(key).suffix, tmp_dir)
            thumb = generate_thumbnail(local_path, tmp_dir / "thumb.jpg")
        except Exception as exc:
            return JSONResponse(status_code=500, content=error_response(type(exc).__name__, str(exc), bucket, key))

    return JSONResponse(
        content={
            "status": "ok",
            "bucket": bucket,
            "key": key,
            "thumbnail_url": _thumbnail_url_for(bucket, key, payload.get("thumbnail_url")),
            "width": thumb["width"],
            "height": thumb["height"],
            "content_type": thumb["content_type"],
            "note": "Thumbnail bytes generated. Upload to storage is handled by the caller/trigger on OCI or AWS.",
        }
    )
