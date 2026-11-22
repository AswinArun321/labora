"""
Security Headers & Content Security Policy (CSP) Middleware for LABORA.
"""
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Prevent MIME type sniffing
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Anti-clickjacking
        response.headers.setdefault("X-Frame-Options", "DENY")

        # Referrer policy
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Restrict dangerous browser features
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")

        # Content Security Policy (CSP)
        # Compatible with locally bundled Monaco Editor, Monaco Web Workers (self / blob:), and Tailwind
        extra_connect = getattr(settings, "CSP_EXTRA_CONNECT_SRC", [])
        connect_src = ["'self'"] + [s for s in extra_connect if s]
        if settings.DEBUG:
            connect_src.extend([
                "ws://localhost:5173",
                "ws://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ])

        connect_src_str = " ".join(dict.fromkeys(connect_src))

        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "worker-src 'self' blob:",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            f"connect-src {connect_src_str}",
            "frame-ancestors 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        response.headers.setdefault("Content-Security-Policy", "; ".join(csp_directives))
        return response
