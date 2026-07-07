"""Security headers middleware.

Injects hardening headers on every HTTP response:
  - X-Content-Type-Options   : prevent MIME-type sniffing
  - X-Frame-Options          : block iframe embedding (clickjacking)
  - X-XSS-Protection        : legacy XSS filter hint for older browsers
  - Referrer-Policy          : limit referrer leakage
  - Permissions-Policy       : disable unneeded browser features
  - Content-Security-Policy  : tight policy for a JSON API origin
  - Strict-Transport-Security: HSTS (production only)
  - Cache-Control            : no-store on auth endpoints
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # Pure JSON API: no scripts, styles, images, or frames served from this origin.
    # frame-ancestors 'none' replaces X-Frame-Options for modern browsers.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

_HSTS = "max-age=31536000; includeSubDomains; preload"

_AUTH_PATHS = frozenset({"/api/v1/auth/login", "/api/v1/auth/register"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app, production: bool = False) -> None:
        super().__init__(app)
        self._production = production

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        for header, value in _HEADERS.items():
            response.headers[header] = value

        if self._production:
            response.headers["Strict-Transport-Security"] = _HSTS

        if request.url.path in _AUTH_PATHS:
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        return response
