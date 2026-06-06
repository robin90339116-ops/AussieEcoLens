from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import boto3


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return dynamodb.Table(os.getenv("FILES_TABLE", "AussieEcoLensFiles"))


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


def _scan_all() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    response = _table().scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = _table().scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def query_by_tag_counts(required_tags: dict[str, Any], *, owner_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
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

