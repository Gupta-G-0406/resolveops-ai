
import logging
import json
from app.core.logging_config import SecureJSONFormatter
from app.core.log_security import (
    SensitiveDataFilter,
    redact_sensitive_data,
)



def test_redacts_bearer_token():
    message = "Authorization: Bearer abc123secret"

    result = redact_sensitive_data(message)

    assert "abc123secret" not in result
    assert "[REDACTED]" in result


def test_redacts_api_key():
    message = "api_key=super-secret-key"

    result = redact_sensitive_data(message)

    assert "super-secret-key" not in result
    assert "api_key=[REDACTED]" in result


def test_redacts_password():
    message = "password=my-password"

    result = redact_sensitive_data(message)

    assert "my-password" not in result


def test_preserves_safe_message():
    message = (
        "MCP tool completed tool=get_order "
        "duration_ms=24.50 status=success"
    )

    assert redact_sensitive_data(message) == message


def test_sensitive_data_filter():
    record = logging.LogRecord(
        name="resolveops.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="access_token=private-token",
        args=(),
        exc_info=None,
    )

    filter_instance = SensitiveDataFilter()

    assert filter_instance.filter(record) is True
    assert "private-token" not in record.getMessage()


def test_redacts_json_api_key():
    message = '{"api_key": "my-secret-api-key"}'

    result = redact_sensitive_data(message)

    assert "my-secret-api-key" not in result
    assert "[REDACTED]" in result


def test_redacts_json_password():
    message = '{"password": "my-password"}'

    result = redact_sensitive_data(message)

    assert "my-password" not in result
    assert "[REDACTED]" in result



def test_secure_json_formatter_redacts_secret():
    record = logging.LogRecord(
        name="resolveops.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="api_key=very-secret-key",
        args=(),
        exc_info=None,
    )

    formatter = SecureJSONFormatter()
    output = formatter.format(record)

    parsed = json.loads(output)

    assert "very-secret-key" not in output
    assert "[REDACTED]" in parsed["message"]


def test_secure_json_formatter_redacts_exception():
    import json
    import sys

    from app.core.logging_config import SecureJSONFormatter

    try:
        raise ValueError("api_key=exception-secret-123")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="resolveops.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="MCP tool failed",
        args=(),
        exc_info=exc_info,
    )

    output = SecureJSONFormatter().format(record)

    parsed = json.loads(output)

    assert "exception-secret-123" not in output
    assert "[REDACTED]" in output
    assert parsed["level"] == "ERROR"
