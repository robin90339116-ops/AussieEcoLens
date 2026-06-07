from __future__ import annotations

import os
import json
from typing import Any

import boto3

from aussie_ecolens_db import delete_subscription, get_subscription, normalise_species, save_subscription


def sns_client():
    return boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1"))


def topic_arn() -> str:
    arn = os.getenv("SNS_TOPIC_ARN")
    if not arn:
        raise RuntimeError("SNS_TOPIC_ARN is not configured")
    return arn


def publish_new_file_notification(
    *,
    file_id: str,
    original_url: str,
    tags: dict[str, Any],
) -> dict[str, Any]:
    species = [normalise_species(name) for name in tags.keys()]
    response = sns_client().publish(
        TopicArn=topic_arn(),
        Subject="AussieEcoLens new wildlife observation",
        Message=f"New observation uploaded: {original_url}",
        MessageAttributes={
            "species": {
                "DataType": "String.Array",
                "StringValue": str(species).replace("'", '"'),
            },
            "file_id": {"DataType": "String", "StringValue": file_id},
        },
    )
    return {"message_id": response["MessageId"], "species": species}


def _filter_policy(species: list[str]) -> str:
    return json.dumps({"species": sorted(set(species))})


def _is_real_subscription_arn(subscription_arn: str | None) -> bool:
    return bool(subscription_arn and subscription_arn.startswith("arn:"))


def _set_filter_policy(subscription_arn: str, species: list[str]) -> None:
    sns_client().set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="FilterPolicy",
        AttributeValue=_filter_policy(species),
    )


def _find_subscription_arn(user_email: str) -> str | None:
    paginator = sns_client().get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=topic_arn()):
        for subscription in page.get("Subscriptions", []):
            if subscription.get("Protocol") == "email" and subscription.get("Endpoint") == user_email:
                arn = subscription.get("SubscriptionArn")
                if _is_real_subscription_arn(arn):
                    return arn
    return None


def subscribe_email(*, user_email: str, species_list: list[str]) -> dict[str, Any]:
    species = [normalise_species(item) for item in species_list]
    current = get_subscription(user_email=user_email)
    if current:
        existing_species = [normalise_species(item) for item in current.get("species_list", [])]
        merged_species = sorted(set(existing_species) | set(species))
        subscription_arn = current.get("subscription_arn")

        if set(existing_species) == set(merged_species):
            return {
                "subscription_arn": subscription_arn,
                "subscription": current,
                "duplicate": True,
                "confirmation_required": not _is_real_subscription_arn(subscription_arn),
            }

        if _is_real_subscription_arn(subscription_arn):
            _set_filter_policy(subscription_arn, merged_species)
        saved = save_subscription(
            user_email=user_email,
            species_list=merged_species,
            subscription_arn=subscription_arn,
        )
        return {
            "subscription_arn": subscription_arn,
            "subscription": saved,
            "updated_filter_policy": _is_real_subscription_arn(subscription_arn),
            "confirmation_required": not _is_real_subscription_arn(subscription_arn),
        }

    response = sns_client().subscribe(
        TopicArn=topic_arn(),
        Protocol="email",
        Endpoint=user_email,
        Attributes={
            "FilterPolicy": _filter_policy(species),
        },
        ReturnSubscriptionArn=True,
    )
    subscription_arn = response.get("SubscriptionArn")
    saved = save_subscription(user_email=user_email, species_list=species, subscription_arn=subscription_arn)
    return {
        "subscription_arn": subscription_arn,
        "subscription": saved,
        "confirmation_required": not _is_real_subscription_arn(subscription_arn),
    }


def unsubscribe_email(*, user_email: str, subscription_arn: str | None = None, species_list: list[str] | None = None) -> dict[str, Any]:
    current = get_subscription(user_email=user_email)
    species = [normalise_species(item) for item in species_list] if species_list else None
    arn = subscription_arn or (current or {}).get("subscription_arn") or _find_subscription_arn(user_email)
    result: dict[str, Any] = {"subscription_arn": arn}

    if current and species:
        remaining = [item for item in current.get("species_list", []) if item not in set(species)]
        if remaining:
            if _is_real_subscription_arn(arn):
                _set_filter_policy(arn, remaining)
                result["updated_filter_policy"] = True
            result["local_subscription"] = save_subscription(
                user_email=user_email,
                species_list=remaining,
                subscription_arn=arn,
            )
            result["remaining"] = remaining
            return result

    if _is_real_subscription_arn(arn):
        sns_client().unsubscribe(SubscriptionArn=arn)
        result["sns_unsubscribed"] = arn
    elif arn:
        result["sns_unsubscribe_skipped"] = "subscription is still pending confirmation"

    result["local_subscription"] = delete_subscription(user_email=user_email, species_list=None)
    return result
