
from types import SimpleNamespace

from mcp.types import RequestParams

from app.mcp.correlation import get_mcp_request_id


def make_context(metadata):
    return SimpleNamespace(
        request_context=SimpleNamespace(meta=metadata)
    )


def test_valid_mcp_request_id():
    metadata = RequestParams.Meta.model_validate(
        {"request_id": "resolveops-123"}
    )

    ctx = make_context(metadata)

    assert get_mcp_request_id(ctx) == "resolveops-123"


def test_missing_mcp_request_id():
    ctx = make_context(None)

    assert get_mcp_request_id(ctx) is None


def test_invalid_mcp_request_id():
    metadata = RequestParams.Meta.model_validate(
        {"request_id": "invalid request id!"}
    )

    ctx = make_context(metadata)

    assert get_mcp_request_id(ctx) is None


def test_non_string_mcp_request_id():
    metadata = RequestParams.Meta.model_validate(
        {"request_id": 123}
    )

    ctx = make_context(metadata)

    assert get_mcp_request_id(ctx) is None
