"""
Django settings for otto project.

Generated by 'django-admin startproject' using Django 4.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

import structlog
import yaml
from dotenv import load_dotenv
from storages.backends.azure_storage import AzureStorage

from .utils import logging as logging_utils

BASE_DIR = Path(__file__).resolve().parent.parent

# Set the logging level for all azure-* libraries
logger = logging.getLogger("azure.identity")
logger.setLevel(logging.ERROR)

OTTO_VERSION = "v0"

# Load the version from the version.yaml file
version_file_path = os.path.join(BASE_DIR, "version.yaml")
if os.path.exists(version_file_path):
    with open(version_file_path, "r") as file:
        data = yaml.safe_load(file)
        OTTO_VERSION = data.get("version")

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))
# Check for a variable we only set in the .env file to see if it exists
if os.environ.get("DJANGODB_NAME") is None:
    try:
        # These are enough to run the CI tests
        load_dotenv(os.path.join(BASE_DIR, ".env.example"))
        print("Using .env.example")
    except:
        raise Exception("No .env or .env.example file found. Shutting down.")

ENVIRONMENT = os.environ.get("ENV", "LOCAL").upper()
IS_RUNNING_IN_CELERY = sys.argv and "celery" in sys.argv[0]
IS_RUNNING_IN_GITHUB = "GITHUB_ACTIONS" in os.environ
IS_RUNNING_IN_DEVOPS = "DEVOPS_PIPELINES" in os.environ
IS_RUNNING_TESTS = "test" in sys.argv or any("pytest" in arg for arg in sys.argv)
# Needs to be here for some rules checks. Just keep False for now.
IS_PROD = False

SITE_URL = urlparse(os.environ.get("SITE_URL"))

AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_COGNITIVE_SERVICE_KEY = os.environ.get("AZURE_COGNITIVE_SERVICE_KEY")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-secret-key")
AZURE_ACCOUNT_KEY = os.environ.get(
    "AZURE_ACCOUNT_KEY"
)  # Azure as default storage requires this name to be AZURE_ACCOUNT_KEY

# AC-2, AC-19: Entra Integration
ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
ENTRA_CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET")
ENTRA_AUTHORITY = os.environ.get("ENTRA_AUTHORITY")
ENTRA_REDIRECT_URI = SITE_URL.geturl() + os.environ.get("ENTRA_REDIRECT_URI")
AZURE_AUTH = {
    "CLIENT_ID": ENTRA_CLIENT_ID,
    "CLIENT_SECRET": ENTRA_CLIENT_SECRET,
    "REDIRECT_URI": ENTRA_REDIRECT_URI,
    "SCOPES": ["User.Read"],
    "AUTHORITY": ENTRA_AUTHORITY,
    "USERNAME_ATTRIBUTE": "userPrincipalName",  # The AAD attribute or ID token claim you want to use as the value for the user model `USERNAME_FIELD`
    "PUBLIC_PATHS": [os.environ.get("ENTRA_REDIRECT_URI"), "/welcome/"],
    "USER_MAPPING_FN": "otto.utils.auth.map_entra_to_django_user",  # Optional, path to the function used to map the AAD to Django attributes
}
LOGIN_URL = "/azure_auth/login"
LOGIN_REDIRECT_URL = "/"  # Or any other endpoint

# Session timeout. 24 hours is allowed for WCAG and meets security requirement
SESSION_COOKIE_AGE = 60 * 60 * 24  # 24 hours, in seconds
SESSION_SAVE_EVERY_REQUEST = True  # Reset the timeout on every request

# OpenAI
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = os.environ.get("AZURE_OPENAI_VERSION")
# TODO: Replace with Cost model (this is used in Template Wizard)
OPENAI_COST_PER_TOKEN = 0.0020 / 1000
OPENAI_EMBEDDING_COST_PER_TOKEN = 0.0004 / 1000

DEFAULT_CHAT_MODEL = "gpt-4o-mini"
USD_TO_CAD = 1.36


# Azure Cognitive Services
AZURE_COGNITIVE_SERVICE_ENDPOINT = os.environ.get("AZURE_COGNITIVE_SERVICE_ENDPOINT")
AZURE_COGNITIVE_SERVICE_REGION = os.environ.get("AZURE_COGNITIVE_SERVICE_REGION")

AZURE_ACCOUNT_NAME = os.environ.get(
    "AZURE_STORAGE_ACCOUNT_NAME", ""
)  # Azure as default storage requires this name to be AZURE_ACCOUNT_NAME
AZURE_CONTAINER = os.environ.get(
    "AZURE_STORAGE_CONTAINER", ""
)  # Azure as default storage requires this name to be AZURE_STORAGE_CONTAINER

DEBUG = os.environ.get("DEBUG", "False") == "True"
DEBUG_PROPAGATE_EXCEPTIONS = True

ALLOWED_HOSTS = [SITE_URL.hostname, "localhost", "127.0.0.1"]

# AC-2: Entra Integration Helper App Configuration
AUTHENTICATION_BACKENDS = [
    "azure_auth.backends.AzureBackend",
    "rules.permissions.ObjectPermissionBackend",
]

if IS_RUNNING_TESTS:
    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
        "rules.permissions.ObjectPermissionBackend",
    ]

# Application definition
INSTALLED_APPS = [
    # Third-party apps
    "daphne",
    "django_structlog",
    "modeltranslation",
    "django_prometheus",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "corsheaders",
    "autocomplete",
    "rules.apps.AutodiscoverRulesConfig",
    "azure_auth",  # AC-2: Entra Integration Helper App
    # Otto apps
    "otto",
    "librarian",
    "chat",
    "laws",
    "case_prep",
    "template_wizard",
    # Third-party apps
    "channels",
    "django_cleanup.apps.CleanupConfig",
    "text_extractor",
    "django_celery_beat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # SC-10, SC-23: Django default session management
    "django.contrib.sessions.middleware.SessionMiddleware",
    # AC-2, AC-3, IA-2, IA-6, IA-8: Authentication, AC-14: Limited Access
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # AC-3 & AC-14: Limited Access to handle login flows: redirect to login page, use Azure login, accept terms to use
    # AC-3(7), IA-8: Custom middleware for enforcing role-based access control
    "otto.utils.auth.RedirectToLoginMiddleware",
    # AC-2, AC-14, IA-2, IA-6, IA-8, SC-23: Azure AD Integration to protect entire site by default
    "azure_auth.middleware.AzureMiddleware",
    "otto.utils.auth.AcceptTermsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "data_fetcher.middleware.GlobalRequestMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
    # AU-6: Aupports structured logging, facilitating the review and analysis of audit records for inappropriate or unusual activity
    "django_structlog.middlewares.RequestMiddleware",
]

if IS_RUNNING_TESTS:
    MIDDLEWARE.remove("azure_auth.middleware.AzureMiddleware")

CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = [
    "http://localhost:9000",
    "https://justipedia.gc.ca",
]


DEBUG_TOOLBAR = (
    os.environ.get("DEBUG_TOOLBAR", "False") == "True" and not IS_RUNNING_IN_CELERY
)

# If DEBUG_TOOLBAR is enabled, configure debug toolbar settings
if DEBUG_TOOLBAR:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

    # Set INTERNAL_IPS based on DEBUG_TOOLBAR_IP_LIST or default to "127.0.0.1"
    INTERNAL_IPS = os.environ.get("DEBUG_TOOLBAR_IP_LIST", "127.0.0.1").split(",")

    # If DEBUG_TOOLBAR_IP_LIST is set to 127.0.0.1 and DEBUG_TOOLBAR is True,
    # the debug toolbar will only be visible for requests originating from the server machine (localhost),
    # restricting access to external devices and ensuring it's only available in local development environments.
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_COLLAPSED": True,
        "UPDATE_ON_FETCH": True,
        "RENDER_PANELS": False,
    }


ROOT_URLCONF = "otto.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "otto", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "otto.context_processors.otto_version",
            ],
        },
    },
]

WSGI_APPLICATION = "otto.wsgi.application"

ASGI_APPLICATION = "otto.asgi.application"


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "TEST": {"NAME": "otto_test"},
    },
    "vector_db": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

# If the database is set in the environment variables, use that instead
if os.environ.get("DJANGODB_ENGINE") is not None:
    DATABASES["default"] = {
        "ENGINE": os.environ.get("DJANGODB_ENGINE"),
        "NAME": os.environ.get("DJANGODB_NAME"),
        "USER": os.environ.get("DJANGODB_USER"),
        # CosmosDB can't have the password quoted; it seems to handle this natively. TODO: Investigate to understand better
        "PASSWORD": os.environ.get("DJANGODB_PASSWORD", ""),
        "HOST": os.environ.get("DJANGODB_HOST"),
    }

    # Add the PORT and SSLMODE for CosmosDB, which only exist for DEV, UAT, and PROD
    if ENVIRONMENT in ["DEV", "UAT", "PROD"]:
        DATABASES["default"]["PORT"] = os.environ.get("DJANGODB_PORT")
        DATABASES["default"]["SSLMODE"] = "require"

if os.environ.get("VECTORDB_ENGINE") is not None:
    DATABASES["vector_db"] = {
        "ENGINE": os.environ.get("VECTORDB_ENGINE"),
        "NAME": os.environ.get("VECTORDB_NAME"),
        "USER": os.environ.get("VECTORDB_USER"),
        # Passwords for Postgres need to be quoted to handle special characters
        "PASSWORD": quote(os.environ.get("VECTORDB_PASSWORD", "")),
        "HOST": os.environ.get("VECTORDB_HOST"),
    }


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []


TIME_ZONE = "UTC"


REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-ca"

TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True
LANGUAGES = [
    ("en", "English"),
    ("fr", "French"),
]
LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"
# forever-cacheable files and compression support
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = []


X_FRAME_OPTIONS = "SAMEORIGIN"  # Required for iframe on same origin

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# SC-10: Session Timeout
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Security

if SITE_URL.scheme == "https" and SITE_URL.port == None:
    CSRF_TRUSTED_ORIGINS = [urlunparse(SITE_URL)]
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True  # SC-23: Secure session cookies
    CSRF_COOKIE_SECURE = True
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    print("Using HTTPS")
else:
    CSRF_TRUSTED_ORIGINS = [urlunparse(SITE_URL)]
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Default Storage needs to be a local directory for append to work
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Azure blob storage needed for Translation
# We have already set AZURE_ACCOUNT_KEY, AZURE_ACCOUNT_NAME, AZURE_CONTAINER
AZURE_STORAGE = AzureStorage(
    account_name=AZURE_ACCOUNT_NAME,
    account_key=AZURE_ACCOUNT_KEY,
    azure_container=AZURE_CONTAINER,
)

# Media storage
MEDIA_ROOT = os.path.join(BASE_DIR, os.environ.get("MEDIA_ROOT", "media"))
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)

AUTH_USER_MODEL = "otto.User"

# REDIS

REDIS_URL = "redis://{host}:{port}/0".format(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=os.environ.get("REDIS_PORT", "6379"),
)

# CELERY

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

if IS_RUNNING_IN_GITHUB:
    CACHES = {
        "default": {
            "BACKEND": "otto.utils.cache.LocMemCache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": f"otto_{ENVIRONMENT}",
        }
    }


DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
DATA_UPLOAD_MAX_NUMBER_FILES = 2000

# Logging

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
CELERY_LOG_LEVEL = os.environ.get("CELERY_LOG_LEVEL", "INFO")
DJANGO_STRUCTLOG_CELERY_ENABLED = True
DJANGO_STRUCTLOG_COMMAND_LOGGING_ENABLED = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "json_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "json": {
            "class": "logging.StreamHandler",
            "formatter": "json_formatter",
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["json"],
        "level": LOG_LEVEL,
        "stream": sys.stdout,
    },
}

if ENVIRONMENT == "LOCAL":
    LOGGING["root"]["handlers"] = ["console"]
elif IS_RUNNING_TESTS:
    LOGGING["root"]["handlers"] = ["null"]

# AU-6 & AU-7: Allows for the adjustment of log levels based on the environment and operational needs
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        logging_utils.merge_pathname_lineno_function_to_location,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
