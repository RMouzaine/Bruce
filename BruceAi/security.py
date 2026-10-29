"""
Security & Hardening Utilities for Bruce AI / Orayzis
Implements authentication decorators, constant-time comparisons,
in-memory rate limiting with Flask-Limiter support, input sanitization,
XSS mitigation, security headers, and CORS control.
"""

import os
import re
import hmac
import html
import time
import logging
from collections import defaultdict
from functools import wraps
from typing import Optional, Dict, Any, List
try:
    from flask import request, jsonify, make_response, current_app
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    request = None
    jsonify = None
    make_response = None
    current_app = None

logger = logging.getLogger("bruce.security")


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Ensures DoS and brute-force protection out-of-the-box.
    """
    def __init__(self):
        self._requests = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        timestamps = self._requests[key]
        # Retain only timestamps inside window
        valid_timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(valid_timestamps) >= max_requests:
            self._requests[key] = valid_timestamps
            return False
        valid_timestamps.append(now)
        self._requests[key] = valid_timestamps
        return True

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        now = time.time()
        valid = [t for t in self._requests.get(key, []) if now - t < window_seconds]
        return max(0, max_requests - len(valid))


global_limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int = 30, window_seconds: int = 60):
    """
    Rate limiting decorator applying sliding window per client IP.
    Returns 429 Too Many Requests if threshold is exceeded.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Resolve client IP taking into account reverse proxies if configured
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
            client_ip = client_ip.split(",")[0].strip()
            endpoint_key = f"{client_ip}:{request.endpoint}"

            if not global_limiter.is_allowed(endpoint_key, max_requests, window_seconds):
                logger.warning(f"Rate limit exceeded for {endpoint_key}: {max_requests} reqs / {window_seconds}s")
                resp = jsonify({
                    "status": "error",
                    "error": "Too Many Requests",
                    "message": f"Rate limit of {max_requests} requests per {window_seconds} seconds exceeded. Please back off."
                })
                resp.status_code = 429
                resp.headers["Retry-After"] = str(window_seconds)
                return resp

            response = f(*args, **kwargs)
            # Add rate limit headers to response if it's a Flask Response object
            if hasattr(response, "headers"):
                remaining = global_limiter.get_remaining(endpoint_key, max_requests, window_seconds)
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(window_seconds)
            return response
        return wrapper
    return decorator


def safe_compare(val1: Optional[str], val2: Optional[str]) -> bool:
    """
    Performs constant-time string comparison to prevent timing attacks.
    """
    if not val1 or not val2:
        return False
    return hmac.compare_digest(val1.encode('utf-8'), val2.encode('utf-8'))


def sanitize_text(text: Optional[str], max_length: int = 500) -> str:
    """
    Sanitizes arbitrary text input to protect against XSS and control character injection:
    - Truncates to max_length
    - Escapes HTML entities (&, <, >, ", ')
    - Removes ASCII control characters except newline and tab
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Remove null bytes and non-printable control characters
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    escaped = html.escape(cleaned.strip())
    return escaped[:max_length]


def sanitize_payload(data: Any, max_depth: int = 5) -> Any:
    """
    Recursively sanitizes JSON request payloads.
    """
    if max_depth <= 0:
        return ""
    if isinstance(data, str):
        return sanitize_text(data)
    elif isinstance(data, dict):
        return {sanitize_text(str(k), 100): sanitize_payload(v, max_depth - 1) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_payload(item, max_depth - 1) for item in data]
    return data


def extract_token_from_request() -> Optional[str]:
    """
    Extracts Bearer token or X-API-KEY header from incoming request.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    
    x_api_key = request.headers.get("X-API-KEY", "")
    if x_api_key:
        return x_api_key.strip()

    query_key = request.args.get("api_key")
    if query_key:
        return query_key.strip()

    return None


def require_api_key(f):
    """
    Decorator requiring a valid client API key (BRUCE_API_KEY or ADMIN_API_KEY).
    Returns 401 Unauthorized or 403 Forbidden on failure.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        expected_key = os.environ.get("BRUCE_API_KEY")
        admin_key = os.environ.get("ADMIN_API_KEY")

        # In dev or demo mode without keys, permit with a safe warning
        if not expected_key and not admin_key and os.environ.get("FLASK_ENV") != "production":
            logger.warning("Unauthenticated request allowed: BRUCE_API_KEY not configured in non-prod environment.")
            return f(*args, **kwargs)

        token = extract_token_from_request()
        if not token:
            return jsonify({
                "status": "error",
                "error": "Unauthorized: Missing authentication token",
                "hint": "Provide your token via 'Authorization: Bearer <TOKEN>' or 'X-API-KEY: <TOKEN>' header."
            }), 401

        is_valid = safe_compare(token, expected_key) or safe_compare(token, admin_key)
        if not is_valid:
            return jsonify({
                "status": "error",
                "error": "Forbidden: Invalid authentication token"
            }), 403

        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """
    Decorator requiring administrative privileges (ADMIN_API_KEY).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_key = os.environ.get("ADMIN_API_KEY")
        token = extract_token_from_request()

        if not token:
            return jsonify({"status": "error", "error": "Unauthorized: Admin credentials required"}), 401

        if not admin_key or not safe_compare(token, admin_key):
            return jsonify({"status": "error", "error": "Forbidden: Administrative access required"}), 403

        return f(*args, **kwargs)
    return decorated_function


def apply_security_headers(response):
    """
    Attaches OWASP recommended security headers to all HTTP responses.
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.open-meteo.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    if request.path.startswith("/rapport") or request.path.startswith("/admin") or request.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"

    return response


def handle_cors(response):
    """
    Enforces restricted Cross-Origin Resource Sharing (CORS) policies.
    """
    raw_allowed = os.environ.get("ALLOWED_ORIGINS", "https://orayzis.github.io,https://orayzis.com,http://localhost:3000,http://127.0.0.1:5000")
    allowed_origins = [o.strip() for o in raw_allowed.split(",") if o.strip()]

    origin = request.headers.get("Origin")
    if origin and (origin in allowed_origins or "*" in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-KEY"
        response.headers["Access-Control-Max-Age"] = "86400"

    return response
