from __future__ import annotations

import time
import uuid
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUESTS = Counter("taxledger_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("taxledger_http_request_duration_seconds", "HTTP latency", ["method", "route"])


class OperationsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            REQUESTS.labels(request.method, request.url.path, "500").inc()
            raise
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        REQUESTS.labels(request.method, route_path, str(response.status_code)).inc()
        LATENCY.labels(request.method, route_path).observe(time.perf_counter() - started)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
