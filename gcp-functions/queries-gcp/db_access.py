from __future__ import annotations

import os
from decimal import Decimal
from typing import Any
from urllib.parse import unquote, urlparse

import boto3


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return dynamodb.Table(os.getenv("FILES_TABLE", "AussieEcoLensFiles"))


def _s3_client():
    return boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))


def normalise_species(species: str) -> str:
    return species.strip().lower().replace(" ", "_")


def normalise_tags(tags: dict[str, Any] | None) -> dict[str, Decimal]:
    if not tags:
        return {}
    return {normalise_species(str(key)): Decimal(str(value)) for key, value in tags.items() if str(key).strip()}


def json_safe(value: Any) -> Any:
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def _s3_location_from_url(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme == "s3" and parsed.netloc and parsed.path:
        return parsed.netloc, unquote(parsed.path.lstrip("/"))

    host = parsed.netloc
    path = unquote(parsed.path.lstrip("/"))
    if not host or not path:
        return None
    if ".s3." in host:
        return host.split(".s3.", 1)[0], path
    if host.endswith(".s3.amazonaws.com"):
        return host.split(".s3.amazonaws.com", 1)[0], path
    if host.startswith("s3.") or host == "s3.amazonaws.com":
        parts = path.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    return None


def _s3_location_from_record(item: dict[str, Any], prefix: str) -> tuple[str, str] | None:
    key = item.get(f"{prefix}_s3_key")
    if key:
        bucket_env = "ORIGINAL_BUCKET" if prefix == "original" else "THUMBNAIL_BUCKET"
        bucket = item.get(f"{prefix}_bucket") or os.getenv(bucket_env)
        if bucket:
            return str(bucket), str(key)
    return _s3_location_from_url(item.get(f"{prefix}_url"))


def _presigned_get_url(bucket: str, key: str) -> str | None:
    if os.getenv("PRESIGN_MEDIA_URLS", "true").lower() in {"0", "false", "no"}:
        return None
    expires = int(os.getenv("PRESIGNED_URL_EXPIRES_SECONDS", "900"))
    try:
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )
    except Exception:
        return None


def attach_presigned_media_urls(item: dict[str, Any]) -> dict[str, Any]:
    output = json_safe(item)
    for prefix in ("original", "thumbnail"):
        url_field = f"{prefix}_url"
        raw_url = output.get(f"{prefix}_raw_url") or output.get(url_field)
        location = _s3_location_from_record(output, prefix)
        signed_url = _presigned_get_url(*location) if location else None
        if signed_url:
            if raw_url:
                output[f"{prefix}_raw_url"] = raw_url
            output[f"{prefix}_access_url"] = signed_url
            output[url_field] = signed_url
        elif raw_url:
            output[f"{prefix}_access_url"] = raw_url
    return output


def _scan_all() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    response = _table().scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = _table().scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def query_by_tag_counts(required_tags: dict[str, Any], *, limit: int = 100) -> list[dict[str, Any]]:
    required = normalise_tags(required_tags)
    matches: list[dict[str, Any]] = []

    for item in _scan_all():
        tags = normalise_tags(item.get("tags", {}))
        if all(tags.get(species, Decimal(0)) >= count for species, count in required.items()):
            matches.append(attach_presigned_media_urls(item))
        if len(matches) >= limit:
            break

    return matches


def query_by_species(species: str, *, limit: int = 100) -> list[dict[str, Any]]:
    species_key = normalise_species(species)
    matches: list[dict[str, Any]] = []

    for item in _scan_all():
        tags = normalise_tags(item.get("tags", {}))
        if tags.get(species_key, Decimal(0)) > 0:
            matches.append(attach_presigned_media_urls(item))
        if len(matches) >= limit:
            break

    return matches
