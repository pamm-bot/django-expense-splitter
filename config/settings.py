"""
Django settings for the Split Expenses project.
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key-not-for-production")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "corsheaders",
    "expenses",
    "frontend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"


# Database. DATABASE_URL is set in production (Heroku) and read from .env
# locally. Using dj_database_url.parse() on a value from decouple's config()
# (rather than dj_database_url.config(), which reads os.environ directly)
# is what actually makes the .env file take effect here.
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL", default="postgres:///split_expenses"),
        conn_max_age=600,
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    # Scoped throttling: only views that set `throttle_scope` are limited
    # (the auth endpoints), everything else is untouched.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "20/hour",
        "password_reset": "5/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Split Expenses API",
    "DESCRIPTION": (
        "A Splitwise-style expense splitter: groups, shared expenses, "
        "net balances, and greedy debt simplification."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Password reset emails, via Gmail SMTP (an App Password, not the account
# password). Django 6.1's MAILERS setting replaces the older flat
# EMAIL_* settings, which are deprecated as of this version. Left blank,
# the username/password make Django's SMTP backend fail loudly on send —
# acceptable locally if reset isn't being tested; production always has
# these set.
_EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": config("EMAIL_HOST", default="smtp.gmail.com"),
            "port": config("EMAIL_PORT", default=587, cast=int),
            "username": _EMAIL_HOST_USER,
            "password": config("EMAIL_HOST_PASSWORD", default=""),
            "use_tls": config("EMAIL_USE_TLS", default=True, cast=bool),
        },
    },
}
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=_EMAIL_HOST_USER or "noreply@example.com")

# The frontend is served from the same origin (Django templates + fetch),
# so CORS only needs to be opened up for local development against a
# separately-served frontend if that's ever added.
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 7, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
