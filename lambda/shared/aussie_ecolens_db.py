from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key


DEFAULT_FILES_TABLE = "AussieEcoLensFiles"
DEFAULT_NOTIFICATIONS_TABLE = "AussieEcoLensNotificationsSub"


def _resource():
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))


def files_table():
    return _resource().Table(os.getenv("FILES_TABLE", DEFAULT_FILES_TABLE))


def notifications_table():
    return _resource().Table(os.getenv("NOTIFICATIONS_TABLE", DEFAULT_NOTIFICATIONS_TABLE))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def normalise_species(species: str) -> str:
    return species.strip().lower().replace(" ", "_")


def normalise_tags(tags: dict[str, Any] | list[str] | None) -> dict[str, Decimal]:
    if not tags:
        return {}
    if isinstance(tags, list):
        return {normalise_species(tag): Decimal(1) for tag in tags if str(tag).strip()}

    cleaned: dict[str, Decimal] = {}
    for species, count in tags.items():
        key = normalise_species(str(species))
        if not key:
            continue
        cleaned[key] = Decimal(str(count))
    return cleaned


def write_record(
    *,
    checksum: str,
    file_type: str,
    original_url: str,
    thumbnail_url: str | None,
    tags: dict[str, Any] | list[str] | None,
    owner_id: str,
    file_id: str | None = None,
    original_s3_key: str | None = None,
    thumbnail_s3_key: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = now_iso()
    item: dict[str, Any] = {
        "file_id": file_id or str(uuid.uuid4()),
        "checksum": checksum,
        "type": file_type,
        "original_url": original_url,
        "thumbnail_url": thumbnail_url or "",
        "tags": normalise_tags(tags),
        "owner_id": owner_id,
        "upload_time": timestamp,
        "last_modified": timestamp,
    }
    if original_s3_key:
        item["original_s3_key"] = original_s3_key
    if thumbnail_s3_key:
        item["thumbnail_s3_key"] = thumbnail_s3_key
    if extra:
        item.update(extra)

    files_table().put_item(Item=item)
    return json_safe(item)


def get_by_checksum(checksum: str) -> dict[str, Any] | None:
    response = files_table().query(
        IndexName=os.getenv("CHECKSUM_INDEX", "checksum-index"),
        KeyConditionExpression=Key("checksum").eq(checksum),
        Limit=1,
    )
    items = response.get("Items", [])
    return json_safe(items[0]) if items else None


def get_by_file_id(file_id: str) -> dict[str, Any] | None:
    response = files_table().get_item(Key={"file_id": file_id})
    item = response.get("Item")
    return json_safe(item) if item else None


def _scan_all(**kwargs: Any) -> list[dict[str, Any]]:
    table = files_table()
    items: list[dict[str, Any]] = []
    response = table.scan(**kwargs)
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"], **kwargs)
        items.extend(response.get("Items", []))
    return items


def get_by_url(url: str) -> dict[str, Any] | None:
    for item in _scan_all():
        if item.get("original_url") == url or item.get("thumbnail_url") == url:
            return json_safe(item)
    return None


def get_by_thumbnail_url(thumbnail_url: str) -> dict[str, Any] | None:
    for item in _scan_all():
        if item.get("thumbnail_url") == thumbnail_url:
            return json_safe(item)
    return None


def query_by_tag_counts(
    required_tags: dict[str, Any],
    *,
    owner_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    required = normalise_tags(required_tags)
    matches: list[dict[str, Any]] = []

    for item in _scan_all():
        if owner_id and item.get("owner_id") != owner_id:
            continue
        tags = normalise_tags(item.get("tags", {}))
        if all(tags.get(species, Decimal(0)) >= count for species, count in required.items()):
            matches.append(json_safe(item))
        if len(matches) >= limit:
            break

    return matches


def query_by_species(species: str, *, owner_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    species_key = normalise_species(species)
    matches: list[dict[str, Any]] = []

    for item in _scan_all():
        if owner_id and item.get("owner_id") != owner_id:
            continue
        tags = normalise_tags(item.get("tags", {}))
        if tags.get(species_key, Decimal(0)) > 0:
            matches.append(json_safe(item))
        if len(matches) >= limit:
            break

    return matches


def update_tags(
    *,
    urls: list[str],
    tags: dict[str, Any] | list[str],
    operation: str | int,
) -> dict[str, Any]:
    op = str(operation).lower()
    if op in {"1", "add", "append", "upsert"}:
        mode = "add"
    elif op in {"0", "remove", "delete", "del"}:
        mode = "remove"
    else:
        raise ValueError("operation must be add/1 or remove/0")

    requested_tags = normalise_tags(tags)
    updated: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for url in urls:
        item = get_by_url(url)
        if not item:
            errors.append({"url": url, "error": "not_found"})
            continue

        current_tags = normalise_tags(item.get("tags", {}))
        if mode == "add":
            for species, count in requested_tags.items():
                current_tags[species] = max(current_tags.get(species, Decimal(0)), count)
        else:
            for species in requested_tags:
                current_tags.pop(species, None)

        timestamp = now_iso()
        files_table().update_item(
            Key={"file_id": item["file_id"]},
            UpdateExpression="SET tags = :tags, last_modified = :last_modified",
            ExpressionAttributeValues={
                ":tags": current_tags,
                ":last_modified": timestamp,
            },
        )
        item["tags"] = current_tags
        item["last_modified"] = timestamp
        updated.append(json_safe(item))

    return {"updated": updated, "errors": errors}


def delete_record(*, file_id: str | None = None, url: str | None = None) -> dict[str, Any] | None:
    item = get_by_file_id(file_id) if file_id else get_by_url(url or "")
    if not item:
        return None
    files_table().delete_item(Key={"file_id": item["file_id"]})
    return json_safe(item)


def save_subscription(*, user_email: str, species_list: list[str]) -> dict[str, Any]:
    item = {
        "user_email": user_email,
        "species_list": [normalise_species(species) for species in species_list],
        "created_at": now_iso(),
    }
    notifications_table().put_item(Item=item)
    return item


def delete_subscription(*, user_email: str, species_list: list[str] | None = None) -> dict[str, Any]:
    if species_list is None:
        notifications_table().delete_item(Key={"user_email": user_email})
        return {"user_email": user_email, "deleted": "all"}

    current = notifications_table().get_item(Key={"user_email": user_email}).get("Item")
    if not current:
        return {"user_email": user_email, "deleted": []}
    remove_set = {normalise_species(species) for species in species_list}
    remaining = [species for species in current.get("species_list", []) if species not in remove_set]
    notifications_table().update_item(
        Key={"user_email": user_email},
        UpdateExpression="SET species_list = :species_list",
        ExpressionAttributeValues={":species_list": remaining},
    )
    return {"user_email": user_email, "deleted": list(remove_set), "remaining": remaining}

