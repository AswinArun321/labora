"""
Verification of requests coming from the LABORA Secure Browser (Electron app).

The secure browser signs every request it sends to the LABORA API:

    X-Labora-Ts:        unix time in seconds
    X-Labora-Signature: hex HMAC-SHA256(key, f"{ts}\\n{METHOD}\\n{path_with_query}")

The key is configured in the college's build of the secure browser and in the
backend (LABORA_SECURE_BROWSER_KEY). A normal browser cannot produce the
signature, so practicals marked `require_secure_browser` refuse to open there.
This is the same idea as Safe Exam Browser's "Browser Exam Key".
"""
import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("labora.security")


def compute_signature(key: str, ts: str, method: str, path: str) -> str:
    msg = f"{ts}\n{method.upper()}\n{path}".encode()
    return hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()


def is_secure_browser_request(request) -> bool:
    # Memoize within the lifecycle of the same request object
    if hasattr(request, "_is_secure_browser_cached"):
        return request._is_secure_browser_cached

    ts = request.headers.get("X-Labora-Ts", "")
    sig = request.headers.get("X-Labora-Signature", "")
    if not ts or not sig:
        request._is_secure_browser_cached = False
        return False

    try:
        ts_int = int(ts)
    except ValueError:
        request._is_secure_browser_cached = False
        return False

    max_skew = getattr(settings, "SECURE_BROWSER_MAX_SKEW_SECONDS", 300)
    if abs(time.time() - ts_int) > max_skew:
        request._is_secure_browser_cached = False
        return False

    # Check for replay attack: has this exact signature been received in a previous request?
    cache_key = f"labora_sb_sig_{sig}"
    if cache.get(cache_key):
        logger.warning(f"Rejected replayed Secure Browser signature: {sig[:12]}...")
        request._is_secure_browser_cached = False
        return False

    expected = compute_signature(settings.SECURE_BROWSER_KEY, ts, request.method, request.get_full_path())
    if not hmac.compare_digest(expected, sig):
        request._is_secure_browser_cached = False
        return False

    # Store signature in cache until its skew window expires to block replay attacks across requests
    cache.set(cache_key, 1, timeout=max_skew * 2)
    request._is_secure_browser_cached = True
    return True
