"""
Logging Middleware for FastAPI
Logs all API requests and responses with timing and error tracking
"""

import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from utils.logger import get_logger, log_api_request

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Extract user_id if present in query params or body
        user_id = request.query_params.get("user_id")
        if not user_id and method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_json = json.loads(body.decode("utf-8"))
                    user_id = body_json.get("user_id")
            except:
                pass

        # Log request with detailed info
        query_params = dict(request.query_params) if request.query_params else {}
        headers = dict(request.headers)

        logger.info(
            f"→ {method} {path} from {client_host}",
            extra={
                'extra_data': {
                    'type': 'request_start',
                    'method': method,
                    'path': path,
                    'client_host': client_host,
                    'user_agent': user_agent,
                    'user_id': user_id,
                    'query_params': query_params
                }
            }
        )

        # DEBUG level: log headers (excluding sensitive ones)
        safe_headers = {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
        logger.debug(f"Request headers: {safe_headers}")
        if query_params:
            logger.debug(f"Query params: {query_params}")

        # Process request
        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log response
            log_api_request(
                logger=logger,
                method=method,
                path=path,
                user_id=user_id,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            # Log slow requests
            if duration_ms > 1000:  # > 1 second
                logger.warning(
                    f"Slow request: {method} {path} took {duration_ms}ms",
                    extra={
                        'extra_data': {
                            'type': 'slow_request',
                            'method': method,
                            'path': path,
                            'duration_ms': duration_ms
                        }
                    }
                )

            return response

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log error
            logger.error(
                f"✗ {method} {path} - Error: {str(e)}",
                exc_info=True,
                extra={
                    'extra_data': {
                        'type': 'request_error',
                        'method': method,
                        'path': path,
                        'error': str(e),
                        'duration_ms': duration_ms
                    }
                }
            )

            raise
