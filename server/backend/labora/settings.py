"""
Django settings for LABORA.

All secrets and deployment-specific values come from environment variables.
See backend/.env.example for the full list.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if present (simple KEY=VALUE lines; real environment wins).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me-in-production-0000")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "accounts",
    "labs",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "labora.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "labora.wsgi.application"

# PostgreSQL when POSTGRES_DB is set, SQLite otherwise (local development).
if env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER", "labora"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"user": "600/min", "run": env("RUN_RATE", "20/min")},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=int(env("JWT_REFRESH_HOURS", "12"))),
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "x-labora-ts",
    "x-labora-signature",
    "x-labora-client",
]

# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------
# "judge0" (default, required in production) or "local" (DEVELOPMENT ONLY:
# runs student code on the server with a timeout and no sandbox).
CODE_EXECUTOR = env("CODE_EXECUTOR", "judge0")
JUDGE0_URL = env("JUDGE0_URL", "http://localhost:2358")
JUDGE0_API_KEY = env("JUDGE0_API_KEY", "")          # X-Auth-Token for self-hosted, or RapidAPI key
JUDGE0_RAPIDAPI_HOST = env("JUDGE0_RAPIDAPI_HOST", "")  # e.g. judge0-ce.p.rapidapi.com
JUDGE0_LANGUAGE_IDS = {
    "c": int(env("JUDGE0_LANG_C", "50")),          # C (GCC 9.2.0)
    "java": int(env("JUDGE0_LANG_JAVA", "62")),    # Java (OpenJDK 13.0.1)
    "python": int(env("JUDGE0_LANG_PYTHON", "71")),  # Python (3.8.1)
}
EXECUTION_TIMEOUT_SECONDS = float(env("EXECUTION_TIMEOUT_SECONDS", "5"))

# ---------------------------------------------------------------------------
# LABORA Secure Browser
# ---------------------------------------------------------------------------
# Shared key baked into the college's build of the secure browser. Requests
# from the secure browser carry an HMAC of (timestamp, method, path) made with
# this key. Practicals marked "require_secure_browser" only accept such requests.
SECURE_BROWSER_KEY = env("LABORA_SECURE_BROWSER_KEY", "change-this-shared-browser-key")
SECURE_BROWSER_MAX_SKEW_SECONDS = int(env("LABORA_SECURE_BROWSER_MAX_SKEW", "300"))

# ---------------------------------------------------------------------------
# Optional teacher-side AI review (OpenAI-compatible chat API; works with
# OpenAI or Gemini's OpenAI-compatible endpoint). Students never see this.
# ---------------------------------------------------------------------------
AI_API_KEY = env("AI_API_KEY", "")
AI_BASE_URL = env("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = env("AI_MODEL", "gpt-4o-mini")

# Activity indicator thresholds (teacher-side review hints, not proof).
INDICATOR_LARGE_INSERT_CHARS = int(env("INDICATOR_LARGE_INSERT_CHARS", "120"))
INDICATOR_LATE_CHANGE_MINUTES = int(env("INDICATOR_LATE_CHANGE_MINUTES", "2"))
INDICATOR_LATE_CHANGE_RATIO = float(env("INDICATOR_LATE_CHANGE_RATIO", "0.5"))

# Built React app served by Django when present (set FRONTEND_DIST="" to disable).
_fd = env("FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist"))
FRONTEND_DIST = Path(_fd) if _fd else None
