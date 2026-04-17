from __future__ import annotations

import hmac
import time
from collections import deque

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

SESSION_COOKIE = "perfin_session"
SESSION_TTL_SECONDS = 30 * 24 * 3600


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().PERFIN_SESSION_SECRET, salt="perfin-session")


def issue_session(response: Response) -> None:
    token = _serializer().dumps({"ok": True})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def verify_session(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=SESSION_TTL_SECONDS)
        return True
    except (BadSignature, SignatureExpired):
        return False


def check_passphrase(submitted: str) -> bool:
    return hmac.compare_digest(submitted or "", get_settings().PERFIN_PASSPHRASE or "")


_login_attempts: deque[float] = deque(maxlen=20)


def rate_limit_login() -> bool:
    now = time.monotonic()
    while _login_attempts and now - _login_attempts[0] > 60:
        _login_attempts.popleft()
    if len(_login_attempts) >= 10:
        return False
    _login_attempts.append(now)
    return True


PUBLIC_PREFIXES = ("/login", "/static", "/healthz")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        if verify_session(request):
            return await call_next(request)
        if request.headers.get("hx-request"):
            return Response(status_code=401, headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login", status_code=303)
