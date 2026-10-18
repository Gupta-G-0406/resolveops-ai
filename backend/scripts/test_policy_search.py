
import time

from app.rag.policy_store import search_policies


def main():
    print("[TEST] Starting direct policy search", flush=True)

    started = time.perf_counter()

    policies = search_policies(
        "Customer says order delivered but not received",
        limit=3,
    )

    print(
        f"[TEST] Completed in "
        f"{time.perf_counter() - started:.2f}s",
        flush=True,
    )

    for policy in policies:
        print(
            policy["policy_id"],
            policy["title"],
        )


if __name__ == "__main__":
    main()
