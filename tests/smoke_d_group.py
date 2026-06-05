from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "gcp-functions" / "queries-gcp"))

import db_access


def main() -> None:
    sample_items = [
        {
            "file_id": "a",
            "owner_id": "user-1",
            "thumbnail_url": "thumb-a",
            "original_url": "orig-a",
            "tags": {"wombat": 2, "magpie": 1},
        },
        {
            "file_id": "b",
            "owner_id": "user-1",
            "thumbnail_url": "thumb-b",
            "original_url": "orig-b",
            "tags": {"wombat": 2},
        },
        {
            "file_id": "c",
            "owner_id": "user-2",
            "thumbnail_url": "thumb-c",
            "original_url": "orig-c",
            "tags": {"magpie": 1},
        },
    ]

    db_access._scan_all = lambda: sample_items

    q1 = db_access.query_by_tag_counts({"wombat": 2, "magpie": 1})
    assert [item["file_id"] for item in q1] == ["a"], q1

    q1_owner = db_access.query_by_tag_counts({"wombat": 2}, owner_id="user-1")
    assert [item["file_id"] for item in q1_owner] == ["a", "b"], q1_owner

    q2 = db_access.query_by_species("magpie")
    assert [item["file_id"] for item in q2] == ["a", "c"], q2

    print("D group smoke test passed")


if __name__ == "__main__":
    main()

