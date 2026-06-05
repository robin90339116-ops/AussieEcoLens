from __future__ import annotations

import os
from typing import Any

import boto3

from aussie_ecolens_db import normalise_species, save_subscription, delete_subscription


def sns_client():
    return boto3.client("sns", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))


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


def subscribe_email(*, user_email: str, species_list: list[str]) -> dict[str, Any]:
    species = [normalise_species(item) for item in species_list]
    response = sns_client().subscribe(
        TopicArn=topic_arn(),
        Protocol="email",
        Endpoint=user_email,
        Attributes={
            "FilterPolicy": str({"species": species}).replace("'", '"'),
        },
        ReturnSubscriptionArn=True,
    )
    saved = save_subscription(user_email=user_email, species_list=species)
    return {
        "subscription_arn": response.get("SubscriptionArn"),
        "subscription": saved,
        "confirmation_required": True,
    }


def unsubscribe_email(*, user_email: str, subscription_arn: str | None = None, species_list: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if subscription_arn:
        sns_client().unsubscribe(SubscriptionArn=subscription_arn)
        result["sns_unsubscribed"] = subscription_arn
    result["local_subscription"] = delete_subscription(user_email=user_email, species_list=species_list)
    return result

