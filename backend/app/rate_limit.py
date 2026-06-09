from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import ceil
from time import monotonic

from fastapi import Depends, HTTPException, Request, status

from app.auth.service import get_current_user
from app.models import User


@dataclass(frozen=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int
    label: str


LOGIN_IP_RULE = RateLimitRule("login-ip", 30, 300, "login")
LOGIN_ACCOUNT_RULE = RateLimitRule("login-account", 8, 300, "login")
REGISTER_RULE = RateLimitRule("register", 10, 3600, "registration")
MESSAGE_RULE = RateLimitRule("message-send", 30, 60, "message sending")
TYPING_RULE = RateLimitRule("typing", 120, 60, "typing updates")
UPLOAD_RULE = RateLimitRule("upload", 12, 600, "uploads")
ACCESS_REQUEST_RULE = RateLimitRule("access-request", 10, 600, "access requests")
SENSITIVE_ACTION_RULE = RateLimitRule("sensitive-action", 60, 300, "sensitive actions")
PUBLIC_WRITE_RULE = RateLimitRule("public-write", 20, 300, "public writes")

_buckets: dict[str, deque[float]] = defaultdict(deque)
_last_cleanup = 0.0


def client_ip(request: Request | None) -> str:
    if not request:
        return "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "unknown"
    return request.client.host if request.client and request.client.host else "unknown"


def reset_rate_limits() -> None:
    _buckets.clear()
    global _last_cleanup
    _last_cleanup = 0.0


def assert_rate_limit(rule: RateLimitRule, identity: str) -> None:
    now = monotonic()
    cleanup_buckets(now)
    key = f"{rule.scope}:{identity}"
    bucket = _buckets[key]
    cutoff = now - rule.window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= rule.limit:
        retry_after = max(1, ceil(rule.window_seconds - (now - bucket[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many {rule.label}. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)


def cleanup_buckets(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 60:
        return
    _last_cleanup = now
    for key in list(_buckets):
        bucket = _buckets[key]
        if not bucket:
            _buckets.pop(key, None)
            continue
        newest_allowed_age = max(
            LOGIN_IP_RULE.window_seconds,
            LOGIN_ACCOUNT_RULE.window_seconds,
            REGISTER_RULE.window_seconds,
            MESSAGE_RULE.window_seconds,
            TYPING_RULE.window_seconds,
            UPLOAD_RULE.window_seconds,
            ACCESS_REQUEST_RULE.window_seconds,
            SENSITIVE_ACTION_RULE.window_seconds,
            PUBLIC_WRITE_RULE.window_seconds,
        )
        if bucket[-1] <= now - newest_allowed_age:
            _buckets.pop(key, None)


def user_identity(user: User, request: Request | None) -> str:
    return f"user:{user.id}:ip:{client_ip(request)}"


def check_login_rate_limit(request: Request | None, login: str | None) -> None:
    ip = client_ip(request)
    assert_rate_limit(LOGIN_IP_RULE, f"ip:{ip}")
    login_key = str(login or "").strip().lower() or "unknown"
    assert_rate_limit(LOGIN_ACCOUNT_RULE, f"ip:{ip}:login:{login_key}")


def login_ip_rate_limit_dependency(request: Request) -> None:
    assert_rate_limit(LOGIN_IP_RULE, f"ip:{client_ip(request)}")


def register_rate_limit_dependency(request: Request) -> None:
    assert_rate_limit(REGISTER_RULE, f"ip:{client_ip(request)}")


def message_rate_limit_dependency(request: Request, current_user: User = Depends(get_current_user)) -> None:
    assert_rate_limit(MESSAGE_RULE, user_identity(current_user, request))


def typing_rate_limit_dependency(request: Request, current_user: User = Depends(get_current_user)) -> None:
    assert_rate_limit(TYPING_RULE, user_identity(current_user, request))


def upload_rate_limit_dependency(request: Request, current_user: User = Depends(get_current_user)) -> None:
    assert_rate_limit(UPLOAD_RULE, user_identity(current_user, request))


def access_request_rate_limit_dependency(request: Request, current_user: User = Depends(get_current_user)) -> None:
    assert_rate_limit(ACCESS_REQUEST_RULE, user_identity(current_user, request))


def sensitive_action_rate_limit_dependency(request: Request, current_user: User = Depends(get_current_user)) -> None:
    assert_rate_limit(SENSITIVE_ACTION_RULE, user_identity(current_user, request))


def public_write_rate_limit_dependency(request: Request) -> None:
    assert_rate_limit(PUBLIC_WRITE_RULE, f"ip:{client_ip(request)}")
