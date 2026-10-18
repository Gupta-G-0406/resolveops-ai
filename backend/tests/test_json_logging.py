
import json
import logging

from app.core.logging_config import (
    JSONFormatter,
    RequestContextFilter,
    request_id_var,
)


def test_json_formatter():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="resolveops.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Investigation started",
        args=(),
        exc_info=None,
    )

    record.request_id = "test-request-123"

    result = json.loads(formatter.format(record))

    assert result["level"] == "INFO"
    assert result["logger"] == "resolveops.test"
    assert result["message"] == "Investigation started"
    assert result["request_id"] == "test-request-123"
    assert "timestamp" in result


def test_request_context_filter():
    token = request_id_var.set("resolveops-456")

    try:
        record = logging.LogRecord(
            name="resolveops.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Testing context",
            args=(),
            exc_info=None,
        )

        context_filter = RequestContextFilter()

        assert context_filter.filter(record) is True
        assert record.request_id == "resolveops-456"

    finally:
        request_id_var.reset(token)


def test_json_formatter_without_request_id():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="resolveops.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="Background worker started",
        args=(),
        exc_info=None,
    )

    result = json.loads(formatter.format(record))

    assert result["request_id"] is None
    assert result["level"] == "WARNING"
