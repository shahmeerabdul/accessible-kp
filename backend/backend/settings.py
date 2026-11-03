import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


# Safe by default: DEBUG is off unless explicitly enabled. For local
# development set DJANGO_DEBUG=true in backend/.env (see .env.example).
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

INSECURE_SECRET_KEYS = {"", "dev-secret-key-change-me", "change-me-in-production"}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

if DEBUG:
    # Local development conveniences only.
    if SECRET_KEY in INSECURE_SECRET_KEYS:
        SECRET_KEY = "dev-secret-key-change-me"
    ALLOWED_HOSTS: list[str] = env_list("DJANGO_ALLOWED_HOSTS") or ["*"]
else:
    if SECRET_KEY in INSECURE_SECRET_KEYS:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set to a unique, secret value when DJANGO_DEBUG is not true."
        )
    ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must list your real host name(s), not '*', when DJANGO_DEBUG is not true."
        )

INSTALLED_APPS = [
    # The Django admin is intentionally not installed: the app has no models
    # and no staff users, so it would only add attack surface.
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "facilities",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Karachi"

USE_I18N = True

USE_TZ = True

# Let the browser frontend read these custom response headers (see FacilityListView).
CORS_EXPOSE_HEADERS = ["X-Total-Count", "X-Upstream-Capped"]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache for city results and the API throttle counters. In-memory by default,
# which is per process: with several gunicorn workers each one keeps its own
# copy. Set REDIS_URL (e.g. redis://localhost:6379/0, or an ElastiCache
# endpoint) to share one cache across workers and servers.
REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "facilities-cache",
        }
    }

# Log to stdout/stderr (collected by systemd, Docker or CloudWatch).
LOG_LEVEL = os.environ.get("LOG_LEVEL", "").strip().upper() or "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

# DRF basic config
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Every uncached city/limit combination triggers an upstream call, so cap
    # how often a single client can hit the API. Uses the Django cache.
    "DEFAULT_THROTTLE_CLASSES": [
        "facilities.throttling.FailOpenAnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("API_THROTTLE_RATE", "60/min"),
    },
}

# Behind a reverse proxy / load balancer (nginx, ALB) set this to the number of
# proxies in front of Django so throttling sees the real client IP.
if os.environ.get("API_NUM_PROXIES"):
    REST_FRAMEWORK["NUM_PROXIES"] = int(os.environ["API_NUM_PROXIES"])

# CORS: open to everyone only in local development. Outside DEBUG the allowed
# origins must be listed explicitly.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
if CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = False
elif DEBUG:
    CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "true").lower() == "true"
else:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must list the frontend origin(s) when DJANGO_DEBUG is not true."
    )


def env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# HTTPS hardening, on whenever DEBUG is off (i.e. in production).
if not DEBUG:
    # nginx / an ALB terminates TLS and forwards plain HTTP, so Django has to
    # trust X-Forwarded-Proto to know the original request was HTTPS. Only do
    # that when the app is reachable *only* through that proxy; otherwise a
    # client could fake the header. Set DJANGO_BEHIND_PROXY=false if Django is
    # exposed directly.
    if env_bool("DJANGO_BEHIND_PROXY", True):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    # Load-balancer health checks usually speak plain HTTP; don't redirect them.
    SECURE_REDIRECT_EXEMPT = [r"^api/health$"]

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Start small so a misconfiguration is recoverable; raise to 31536000 (one
    # year) once HTTPS is confirmed to work everywhere.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "3600"))

