"""Middleware: structured request logging (request_id + latency) + security headers."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s method=%s path=%s — unhandled error",
                             request_id, request.method, request.url.path)
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_id=%s method=%s path=%s status=%s ms=%.1f",
            request_id, request.method, request.url.path, response.status_code, elapsed_ms,
        )
        response.headers["X-Request-Id"] = request_id
        return response
