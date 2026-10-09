from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

import config

UNPROTECTED = {"/ucp/profile", "/login", "/favicon.ico"}


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not config.SECRET_TOKEN:
            return await call_next(request)
        if request.url.path in UNPROTECTED:
            return await call_next(request)
        if request.cookies.get("session_token") == config.SECRET_TOKEN:
            return await call_next(request)
        return RedirectResponse(url="/login")
