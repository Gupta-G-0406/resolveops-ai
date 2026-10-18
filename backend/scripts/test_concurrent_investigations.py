
import asyncio
import time

import httpx


BASE_URL = "http://127.0.0.1:8000"
TICKET_ID = 2

REQUEST_IDS = [
    "resolveops-concurrent-A",
    "resolveops-concurrent-B",
]


async def investigate(
    client: httpx.AsyncClient,
    request_id: str,
) -> dict:
    started = time.perf_counter()

    try:
        response = await client.post(
            f"/api/tickets/{TICKET_ID}/investigate",
            headers={"X-Request-ID": request_id},
        )

        duration = time.perf_counter() - started

        return {
            "request_id": request_id,
            "response_request_id": response.headers.get(
                "X-Request-ID"
            ),
            "status_code": response.status_code,
            "duration_seconds": round(duration, 2),
            "response_preview": response.text[:300],
        }

    except Exception as exc:
        return {
            "request_id": request_id,
            "error": str(exc),
        }


async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=120.0,
    ) as client:

        results = await asyncio.gather(
            *[
                investigate(client, request_id)
                for request_id in REQUEST_IDS
            ]
        )

    for result in results:
        print(result)

    for result in results:
        assert "error" not in result, result
        assert result["status_code"] == 200, result
        assert (
            result["request_id"]
            == result["response_request_id"]
        ), result

    print("HTTP concurrent request isolation passed")


if __name__ == "__main__":
    asyncio.run(main())
