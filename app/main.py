"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1 import api_v1_router
from app.api.v1.ws import router as ws_router
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.metrics import CONTENT_TYPE_LATEST, MetricsMiddleware, generate_latest
from app.middleware.security_headers import SecurityHeadersMiddleware

# Logging setup - JSON in production, human-readable in development
if settings.app_env == "production":
    from pythonjsonlogger import jsonlogger

    _handler = logging.StreamHandler()
    _handler.setFormatter(
        jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logging.root.handlers = [_handler]
    logging.root.setLevel(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    )
else:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "JWT authentication: login, register, user management.",
    },
    {
        "name": "alerts",
        "description": (
            "Normalized threat alerts from all ingested CTI feeds. "
            "Supports filtering, pagination, CSV/STIX export, correlation, "
            "and semantic similarity search."
        ),
    },
    {
        "name": "sources",
        "description": "CTI feed source registry and ingestion health endpoints.",
    },
    {
        "name": "dashboard",
        "description": "Aggregated overview and timeline data for the dashboard.",
    },
    {
        "name": "summaries",
        "description": "LLM-generated per-alert and daily digest summaries (via Grok).",
    },
    {
        "name": "predictions",
        "description": (
            "14-day threat volume forecasts per severity using Prophet. "
            "Includes anomaly detection and Celery task status polling."
        ),
    },
    {
        "name": "categories",
        "description": "Threat category registry used for automatic alert classification.",
    },
    {
        "name": "websocket",
        "description": "WebSocket endpoint for real-time critical alert streaming.",
    },
]

APP_VERSION = "0.2.0"

app = FastAPI(
    title="CTI Summarizer + Trend Predictor",
    description=(
        "Threat intelligence platform that ingests public CTI feeds (NVD, CISA KEV, "
        "AlienVault OTX, MITRE ATT&CK, RSS blogs, URLhaus), generates executive "
        "summaries via LLM (Grok), predicts threat trends with Prophet, and provides "
        "semantic search over alerts.\n\n"
        "## Authentication\n"
        "Write endpoints (`POST`) require either a **Bearer JWT token** "
        "(from `POST /api/v1/auth/login`) or the legacy **X-API-Key** header.\n"
        "Read endpoints (`GET`) are public.\n\n"
        "## Sources\n"
        "- **NVD** (CVE database)\n"
        "- **CISA KEV** (Known Exploited Vulnerabilities)\n"
        "- **AlienVault OTX** (threat pulses)\n"
        "- **MITRE ATT&CK** (technique reference)\n"
        "- **RSS** (security blogs)\n"
        "- **URLhaus** (malicious URLs)"
    ),
    version=APP_VERSION,
    contact={
        "name": "Enrique",
        "url": "https://github.com/cc22n/cti-summarizer",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=_OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Prometheus instrumentation (must be added before CORS so it sees all requests)
app.add_middleware(MetricsMiddleware)

# CORS — include PATCH for alert annotation endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# Security headers on every response
app.add_middleware(
    SecurityHeadersMiddleware,
    production=settings.app_env == "production",
)

# ── Error handlers ────────────────────────────────────────────────────────────
# In production: hide internal details (field names, stack traces, module paths).
# In development: return full error info to help debugging.

_prod = settings.app_env == "production"
_err_log = logging.getLogger("app.errors")


def _safe_validation_errors(exc: RequestValidationError) -> list:
    """Serialize Pydantic v2 errors to JSON-safe dicts.

    Pydantic v2 field_validator errors put the raw exception object in
    ctx['error'], which is not JSON-serializable.  Convert any Exception
    values to their string representation.
    """
    result = []
    for err in exc.errors():
        e = dict(err)
        ctx = e.get("ctx")
        if isinstance(ctx, dict):
            e["ctx"] = {
                k: str(v) if isinstance(v, Exception) else v
                for k, v in ctx.items()
            }
        result.append(e)
    return result


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Sanitize 422 validation errors — never expose field structure in prod."""
    if _prod:
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request. Check parameters and try again."},
        )
    return JSONResponse(status_code=422, content={"detail": _safe_validation_errors(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Catch-all 500 handler — log the real error, return a generic message."""
    _err_log.exception(
        "[500] %s %s raised %s", request.method, request.url.path, type(exc).__name__
    )
    if _prod:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


# Include API routers
app.include_router(api_v1_router)
app.include_router(ws_router)


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics(request: Request):
    """Prometheus metrics scrape endpoint.

    In production, restricted to localhost so that the Prometheus scraper
    must run on the same host or reach the service through a private network.
    Configure a reverse-proxy (e.g. nginx) to forward /metrics only from
    trusted scraper IPs when a remote Prometheus setup is needed.
    """
    if settings.app_env == "production":
        client_host = request.client.host if request.client else ""
        if client_host not in ("127.0.0.1", "::1"):
            from fastapi import HTTPException as _HTTPException
            raise _HTTPException(
                status_code=403,
                detail="Metrics endpoint is restricted to localhost in production",
            )
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health", tags=["health"], summary="Deep dependency health check")
def health_check(db: Session = Depends(get_db)):
    """Verify database and Redis connectivity.

    Returns HTTP 503 if the database is down, HTTP 200 with status=degraded
    if Redis is unavailable (cache is non-critical).
    """
    from app import cache

    checks: dict = {}
    overall = "ok"

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "error"
        overall = "error"
        logging.getLogger(__name__).error("[health] DB check failed: %s", exc)

    try:
        r = cache._client()
        if r is None:
            checks["redis"] = "unavailable"
            if overall == "ok":
                overall = "degraded"
        else:
            r.ping()
            checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = "unavailable"
        if overall == "ok":
            overall = "degraded"
        logging.getLogger(__name__).warning(
            "[health] Redis check failed: %s", exc
        )

    http_status = 503 if overall == "error" else 200
    return JSONResponse(
        content={"status": overall, "checks": checks, "version": APP_VERSION},
        status_code=http_status,
    )
