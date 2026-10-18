
"""Load synthetic company policies into ChromaDB."""

import json
from pathlib import Path

from app.rag.policy_store import get_collection


def main():
    source = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "policies"
        / "demo_policies.json"
    )

    policies = json.loads(source.read_text(encoding="utf-8"))

    collection = get_collection()

    collection.upsert(
        ids=[policy["id"] for policy in policies],
        documents=[policy["content"] for policy in policies],
        metadatas=[
            {
                "title": policy["title"],
                "category": policy["category"],
            }
            for policy in policies
        ],
    )

    print(f"Ingested {len(policies)} policies.")
    print(f"Collection size: {collection.count()}")


if __name__ == "__main__":
    main()
