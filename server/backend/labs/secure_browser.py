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
import time

from django.conf import settings


def compute_signature(key: str, ts: str, method: str, path: str) -> str:
    msg = f"{ts}\n{method.upper()}\n{path}".encode()
    return hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()


def is_secure_browser_request(request) -> bool:
    ts = request.headers.get("X-Labora-Ts", "")
    sig = request.headers.get("X-Labora-Signature", "")
    if not ts or not sig:
        return False
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs(time.time() - ts_int) > settings.SECURE_BROWSER_MAX_SKEW_SECONDS:
        return False
    expected = compute_signature(settings.SECURE_BROWSER_KEY, ts, request.method, request.get_full_path())
    return hmac.compare_digest(expected, sig)
