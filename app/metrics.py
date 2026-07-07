"""Prometheus metrics definitions for the CTI Summarizer API.

All counters and histograms are module-level singletons so they survive
across requests. Import this module exactly once (from main.py) to avoid
duplicate-registration errors.
"""

import re
import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    Info,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

# Re-export for use in main.py
__all__ = ["CONTENT_TYPE_LATEST", "generate_latest", "MetricsMiddleware"]

# ── Application info ──────────────────────────────────────────────────────────
APP_INFO = Info("cti_app", "Application metadata")
APP_INFO.info({"version": "0.2.0", "environment": "unknown"})

# ── HTTP request counters ─────────────────────────────────────────────────────
HTTP_REQUESTS = Counter(
    "cti_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

HTTP_DURATION = Histogram(
    "cti_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Domain counters (incremented by services) ─────────────────────────────────
ALERTS_INGESTED = Counter(
    "cti_alerts_ingested_total",
    "Alerts ingested and normalized",
    ["source", "severity"],
)

INGESTION_RUNS = Counter(
    "cti_ingestion_runs_total",
    "Ingestion runs completed",
    ["source", "status"],
)

SUMMARIES_GENERATED = Counter(
    "cti_summaries_generated_total",
    "LLM summaries generated",
    ["summary_type"],
)

# ── Path normalization (prevent high cardinality from numeric IDs) ─────────────
_ID_RE = re.compile(r"/\d+")


def _normalize_path(path: str) -> str:
    return _ID_RE.sub("/{id}", path)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record per-request HTTP metrics without blocking the event loop."""

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = _normalize_path(request.url.path)
        method = request.method
        status = str(response.status_code)

        HTTP_REQUESTS.labels(method=method, endpoint=path, status_code=status).inc()
        HTTP_DURATION.labels(method=method, endpoint=path).observe(duration)

        return response
