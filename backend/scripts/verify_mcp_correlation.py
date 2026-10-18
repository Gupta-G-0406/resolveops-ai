
import json
from collections import defaultdict
from pathlib import Path


LOG_FILE = Path(__file__).resolve().parents[1] / "mcp_debug.log"

REQUEST_IDS = {
    "resolveops-concurrent-A",
    "resolveops-concurrent-B",
}


def main():
    results = defaultdict(list)

    with LOG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            request_id = entry.get("request_id")
            message = entry.get("message", "")

            if (
                request_id in REQUEST_IDS
                and message.startswith("MCP tool completed")
            ):
                results[request_id].append(message)

    for request_id in sorted(REQUEST_IDS):
        print(f"\nRequest ID: {request_id}")

        messages = results[request_id]

        for message in messages:
            print(f"  {message}")

        assert messages, (
            f"No completed MCP tools found for {request_id}"
        )

    print("\nMCP correlation log verification passed")


if __name__ == "__main__":
    main()
