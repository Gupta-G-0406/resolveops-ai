
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import request_id_var


logger = logging.getLogger("resolveops.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_request_id = request.headers.get("X-Request-ID")

        # Generate a trusted ID unless the incoming one is
        # short and limited to safe characters.
        if (
            incoming_request_id
            and len(incoming_request_id) <= 64
            and all(
                char.isalnum() or char in "-_"
                for char in incoming_request_id
            )
        ):
            request_id = incoming_request_id
        else:
            request_id = str(uuid.uuid4())

        token = request_id_var.set(request_id)
        started = time.perf_counter()

        try:
            logger.info(
                "HTTP request started method=%s path=%s",
                request.method,
                request.url.path,
            )

            response = await call_next(request)

            response.headers["X-Request-ID"] = request_id

            logger.info(
                "HTTP request completed method=%s path=%s "
                "status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                (time.perf_counter() - started) * 1000,
            )

            return response

        except Exception:
            logger.exception(
                "HTTP request failed method=%s path=%s",
                request.method,
                request.url.path,
            )
            raise

        finally:
            request_id_var.reset(token)
