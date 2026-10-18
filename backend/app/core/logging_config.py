import os
import sys
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from app.core.log_security import SensitiveDataFilter
from app.core.log_security import redact_sensitive_data

request_id_var: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(payload, default=str)




class SecureJSONFormatter(JSONFormatter):
    def format(self, record: logging.LogRecord) -> str:
        # Parent formatter generates valid JSON first.
        formatted = super().format(record)

        # Parse JSON into Python dictionary.
        payload = json.loads(formatted)

        # Redact values before JSON serialization.
        def sanitize(value):
            if isinstance(value, str):
                return redact_sensitive_data(value)

            if isinstance(value, dict):
                return {
                    key: sanitize(item)
                    for key, item in value.items()
                }

            if isinstance(value, list):
                return [
                    sanitize(item)
                    for item in value
                ]

            return value

        safe_payload = sanitize(payload)

        # json.dumps safely escapes quotes and newlines.
        return json.dumps(
            safe_payload,
            ensure_ascii=False,
        )

def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestContextFilter())
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(SecureJSONFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
