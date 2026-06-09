import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rate_limit import (
    LOGIN_ACCOUNT_RULE,
    MESSAGE_RULE,
    UPLOAD_RULE,
    assert_rate_limit,
    check_login_rate_limit,
    reset_rate_limits,
)


@pytest.fixture(autouse=True)
def clean_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


def request_from(ip: str = "203.0.113.10") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": (ip, 48152),
        }
    )


def test_login_rate_limit_blocks_repeated_account_attempts():
    request = request_from()

    for _ in range(LOGIN_ACCOUNT_RULE.limit):
        check_login_rate_limit(request, "admin@example.com")

    with pytest.raises(HTTPException) as exc:
        check_login_rate_limit(request, "admin@example.com")

    assert exc.value.status_code == 429
    assert "Too many login" in exc.value.detail
    assert exc.value.headers["Retry-After"].isdigit()


def test_message_rate_limit_is_per_identity():
    identity = "user:1:ip:203.0.113.10"

    for _ in range(MESSAGE_RULE.limit):
        assert_rate_limit(MESSAGE_RULE, identity)

    with pytest.raises(HTTPException) as exc:
        assert_rate_limit(MESSAGE_RULE, identity)

    assert exc.value.status_code == 429
    assert_rate_limit(MESSAGE_RULE, "user:2:ip:203.0.113.10")
    assert_rate_limit(MESSAGE_RULE, "user:1:ip:203.0.113.11")


def test_upload_rate_limit_does_not_block_message_scope():
    identity = "user:1:ip:203.0.113.10"

    for _ in range(UPLOAD_RULE.limit):
        assert_rate_limit(UPLOAD_RULE, identity)

    with pytest.raises(HTTPException):
        assert_rate_limit(UPLOAD_RULE, identity)

    assert_rate_limit(MESSAGE_RULE, identity)
