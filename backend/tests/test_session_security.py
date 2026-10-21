from app.services.session_service import (
    generate_session_token,
    hash_session_token,
)


def test_session_tokens_are_random():
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert len(first) >= 40


def test_session_token_hash_is_deterministic():
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)


def test_session_token_hash_is_not_raw_token():
    token = generate_session_token()

    hashed = hash_session_token(token)

    assert hashed != token
    assert len(hashed) == 64


def test_different_tokens_produce_different_hashes():
    first = generate_session_token()
    second = generate_session_token()

    assert hash_session_token(first) != hash_session_token(second)