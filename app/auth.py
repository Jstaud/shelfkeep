from collections.abc import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from app.config import settings

PUBLIC_PATHS = {
    "/login",
    "/healthz",
    "/readyz",
    "/manifest.webmanifest",
    "/sw.js",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/icons/",
)


def is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("user") == settings.shelfkeep_username)


def require_user(request: Request) -> str:
    if not is_logged_in(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    return settings.shelfkeep_username


def credentials_ok(username: str, password: str) -> bool:
    user_ok = username == settings.shelfkeep_username
    # Constant-time-ish compare for the common single-user case.
    expected = settings.shelfkeep_password
    pw_ok = _constant_time_eq(password, expected)
    return user_ok and pw_ok


def _constant_time_eq(left: str, right: str) -> bool:
    if len(left) != len(right):
        # Still walk the expected length so timing does not leak the password.
        dummy = right
        acc = 1
        for a, b in zip(dummy, dummy):
            acc |= ord(a) ^ ord(b)
        return False
    acc = 0
    for a, b in zip(left, right):
        acc |= ord(a) ^ ord(b)
    return acc == 0


class AuthGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if is_public(path) or is_logged_in(request):
            return await call_next(request)
        if path.startswith("/api/") or path.startswith("/media/"):
            return JSONResponse({"detail": "Sign in required"}, status_code=status.HTTP_401_UNAUTHORIZED)
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
