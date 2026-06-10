# ruff: noqa: E402, F403
# E402: module-level imports follow section-by-section pattern
# F403: `from superset.config import *` is the documented Superset config override pattern
# =============================================================================
# Analytics Copilot — Superset Custom Configuration
# =============================================================================
# This file overrides defaults from /app/superset/config.py
# Compatible with: Apache Superset 6.0.0
# =============================================================================

import os
from typing import Any
from cachelib.redis import RedisCache

from superset.config import *

import logging

LOG_LEVEL = "INFO"

# =============================================================================
# 1. WILDCARD EMBED CSRF PATCH
# =============================================================================
# Guest token requests come from cross-origin iframes — CSRF same-origin check
# cannot work. Patch same_origin to support wildcard domains and log every
# decision so embed failures are easy to diagnose.

from urllib.parse import urlparse
from flask_wtf import csrf
from superset.extensions import db
from superset.security import SupersetSecurityManager

log = logging.getLogger("analytics_copilot.superset")

_real_same_origin = csrf.same_origin


def _hostname_matches(
    hostname: str | None,
    allowed_hostname: str | None,
    allowed_origin: str,
) -> bool:
    if not hostname or not allowed_hostname:
        return False

    if allowed_origin.startswith(("http://*.", "https://*.")):
        suffix = allowed_hostname.removeprefix("*.")
        return hostname == suffix or hostname.endswith(f".{suffix}")

    return hostname == allowed_hostname


def _origin_matches(referrer: str, allowed_origin: str) -> bool:
    referrer_url = urlparse(referrer)
    allowed_url = urlparse(allowed_origin.replace(":*", ""))

    if referrer_url.scheme != allowed_url.scheme:
        log.warning(
            "Embed origin rejected: scheme mismatch referrer=%s allowed=%s",
            referrer,
            allowed_origin,
        )
        return False

    if not _hostname_matches(
        referrer_url.hostname,
        allowed_url.hostname,
        allowed_origin,
    ):
        log.warning(
            "Embed origin rejected: host mismatch referrer=%s allowed=%s",
            referrer,
            allowed_origin,
        )
        return False

    if ":*" in allowed_origin:
        log.warning(
            "Embed origin accepted: wildcard port referrer=%s allowed=%s",
            referrer,
            allowed_origin,
        )
        return True

    matches = referrer_url.port == allowed_url.port
    log.warning(
        "Embed origin %s: port check referrer=%s allowed=%s",
        "accepted" if matches else "rejected",
        referrer,
        allowed_origin,
    )
    return matches


def analytics_copilot_same_origin(referrer: str | None, domain: str | None) -> bool:
    log.warning("Embed origin check started: referrer=%s domain=%s", referrer, domain)

    if not referrer or not domain:
        log.warning("Embed origin rejected: missing referrer or domain")
        return False

    try:
        if _real_same_origin(referrer, domain):
            log.warning("Embed origin accepted: native same-origin match")
            return True
    except ValueError:
        log.warning("Embed origin native check failed", exc_info=True)

    matches = _origin_matches(referrer, domain)
    if matches:
        log.warning("Embed origin accepted: configured wildcard match")
    return matches


csrf.same_origin = analytics_copilot_same_origin


# =============================================================================
# 2. EMBEDDED GUEST ROLE
# =============================================================================

PUBLIC_PERMISSION_VIEW_MENUS = (
    ("can_language_pack", "Superset"),
    ("can_read", "CssTemplate"),
)

EMBEDDED_GUEST_PERMISSION_VIEW_MENUS = (
    ("can_csv", "Superset"),
    ("can_dashboard", "Superset"),
    ("can_explore_json", "Superset"),
    ("can_fetch_datasource_metadata", "Superset"),
    ("can_grant_guest_token", "SecurityRestApi"),
    ("can_invalidate", "CacheRestApi"),
    ("can_log", "Superset"),
    ("can_read", "Chart"),
    ("can_read", "CssTemplate"),
    ("can_read", "Dashboard"),
    ("can_read", "DashboardFilterStateRestApi"),
    ("can_read", "Database"),
    ("can_read", "Dataset"),
    ("can_read", "Query"),
    ("can_read", "SavedQuery"),
    ("can_slice", "Superset"),
    ("can_time_range", "Api"),
    ("can_export", "Chart"),
    ("can_export", "Dashboard"),
)


class CustomSecurityManager(SupersetSecurityManager):
    def _grant_permissions(self, role_name, permission_view_menus):
        role = self.find_role(role_name) or self.add_role(role_name)
        if not role:
            log.warning("Superset role sync skipped: role unavailable role=%s", role_name)
            return

        for permission_name, view_menu_name in permission_view_menus:
            permission_view_menu = self.find_permission_view_menu(
                permission_name,
                view_menu_name,
            )
            if permission_view_menu and permission_view_menu not in role.permissions:
                role.permissions.append(permission_view_menu)
                log.warning(
                    "Superset role permission granted: role=%s permission=%s view=%s",
                    role_name,
                    permission_name,
                    view_menu_name,
                )

    def sync_role_definitions(self):
        super().sync_role_definitions()

        try:
            self._grant_permissions("Public", PUBLIC_PERMISSION_VIEW_MENUS)
            self._grant_permissions(
                "Embedded_Guest",
                EMBEDDED_GUEST_PERMISSION_VIEW_MENUS,
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            log.warning("Failed to sync embedded Superset roles", exc_info=True)


CUSTOM_SECURITY_MANAGER = CustomSecurityManager

if "SUPERSET_HOME" in os.environ:
    DATA_DIR = os.environ["SUPERSET_HOME"]
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".superset")

# =============================================================================
# 3. BRANDING
# =============================================================================
APP_NAME = "Analytics Copilot"
LOGO_TOOLTIP = "Analytics Copilot — dbt-powered BI"

# =============================================================================
# 4. COLOR SCHEMES
# =============================================================================
EXTRA_CATEGORICAL_COLOR_SCHEMES: list[dict[str, Any]] = [
    {
        "id": "analytics_copilot_default",
        "label": "Analytics Copilot",
        "description": "Primary palette for the Analytics Copilot dashboards",
        "isDefault": True,
        "colors": [
            "#2563EB",  # Blue 600
            "#16A34A",  # Green 600
            "#D97706",  # Amber 600
            "#DC2626",  # Red 600
            "#7C3AED",  # Violet 600
            "#0891B2",  # Cyan 600
            "#EA580C",  # Orange 600
            "#BE185D",  # Pink 700
            "#4F46E5",  # Indigo 600
            "#65A30D",  # Lime 600
        ],
    },
    {
        "id": "analytics_status",
        "label": "Analytics Status",
        "description": "Status / alert palette (success → warning → error)",
        "colors": [
            "#16A34A",  # Success
            "#2563EB",  # Info
            "#D97706",  # Warning
            "#DC2626",  # Error
        ],
    },
]

EXTRA_SEQUENTIAL_COLOR_SCHEMES: list[dict[str, Any]] = [
    {
        "id": "analytics_blue_seq",
        "label": "Analytics Blue (Sequential)",
        "isDiverging": False,
        "colors": [
            "#DBEAFE",
            "#BFDBFE",
            "#93C5FD",
            "#60A5FA",
            "#3B82F6",
            "#2563EB",
            "#1D4ED8",
            "#1E40AF",
            "#1E3A8A",
            "#172554",
        ],
    },
    {
        "id": "analytics_perf_div",
        "label": "Analytics Performance (Diverging)",
        "isDiverging": True,
        "colors": [
            "#DC2626",
            "#EF4444",
            "#F87171",
            "#FCA5A5",
            "#F5F5F5",
            "#86EFAC",
            "#4ADE80",
            "#22C55E",
            "#16A34A",
            "#15803D",
        ],
    },
]

# =============================================================================
# 5. THEME
# =============================================================================
THEME_DEFAULT = {
    "token": {
        "colorPrimary": "#2563EB",
        "colorSuccess": "#16A34A",
        "colorWarning": "#D97706",
        "colorError": "#DC2626",
        "colorInfo": "#0891B2",
        "colorBgBase": "#FFFFFF",
        "colorBgContainer": "#F8FAFC",
        "colorBgElevated": "#FFFFFF",
        "colorBgLayout": "#F1F5F9",
        "colorText": "#0F172A",
        "colorTextSecondary": "#475569",
        "colorTextTertiary": "#94A3B8",
        "colorBorder": "#E2E8F0",
        "colorBorderSecondary": "#CBD5E1",
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "fontSize": 14,
        "borderRadius": 8,
        "borderRadiusLg": 12,
        "borderRadiusSm": 4,
        "margin": 16,
        "padding": 16,
    }
}

ENABLE_UI_THEME_ADMINISTRATION = True

THEME_FONT_URL_ALLOWED_DOMAINS = ["fonts.googleapis.com", "fonts.gstatic.com"]
CUSTOM_FONT_URLS: list[str] = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
]

# =============================================================================
# 6. LANGUAGES
# =============================================================================
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "tr": {"flag": "tr", "name": "Turkish"},
}
BABEL_DEFAULT_LOCALE = "en"

# =============================================================================
# 7. LIMITS
# =============================================================================
NATIVE_FILTER_DEFAULT_ROW_LIMIT = 10000
FILTER_SELECT_ROW_LIMIT = 10000
FILTER_SEARCH_LIMIT = 10000

# =============================================================================
# 8. DATABASE (Superset metadata)
# =============================================================================
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql://superset:superset@superset-db:5432/superset",
)

SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 5,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
    "max_overflow": 10,
    "connect_args": {
        "connect_timeout": 10,
        "application_name": "superset",
    },
}

PREVENT_UNSAFE_DB_CONNECTIONS = False

# =============================================================================
# 9. CACHE & REDIS
# =============================================================================
REDIS_HOST = os.environ.get("REDIS_HOST", "superset-redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_metadata",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": 0,
}

FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_filter",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": 2,
}

EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_explore",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": 3,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_data",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": 4,
}

RESULTS_BACKEND = RedisCache(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=1,
    default_timeout=86400,
    key_prefix="superset_results",
)

# =============================================================================
# 10. ASYNC TASKS (Celery)
# =============================================================================
class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
    worker_prefetch_multiplier = 1
    task_acks_late = True


CELERY_CONFIG = CeleryConfig

# =============================================================================
# 11. SECURITY & AUTH
# =============================================================================
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "local-dev-secret-key-change-in-prod")

ENABLE_GUEST_TOKEN = True
GUEST_TOKEN_JWT_SECRET = os.environ.get(
    "GUEST_TOKEN_JWT_SECRET", "guest-token-secret-change-in-prod"
)
GUEST_ROLE_NAME = "Embedded_Guest"
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_JWT_EXP_SECONDS = 300
GUEST_TOKEN_JWT_AUDIENCE = "analytics-copilot"

WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
WTF_CSRF_EXEMPT_LIST = [
    "SecurityRestApi.guest_token",
    "ChartDataRestApi.data",
    "Superset.explore_json",
    "Superset.log",
]
ENABLE_EXPLORE_JSON_CSRF_PROTECTION = False

SESSION_TYPE = "redis"
SESSION_REDIS = RedisCache(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=5,
    key_prefix="superset_session:",
)
PERMANENT_SESSION_LIFETIME = 86400

# =============================================================================
# 12. CORS & EMBEDDING
# =============================================================================

# Wildcard origins for CSP frame-ancestors + EMBED_ALLOWED_DOMAINS.
# analytics_copilot_same_origin handles the wildcard matching logic.
# Example: EMBED_ALLOWED_ORIGINS=http://localhost:*,https://*.example.com
_raw_embed_origins = os.environ.get("EMBED_ALLOWED_ORIGINS", "http://localhost:*,https://localhost:*")
_EMBED_ORIGINS: list[str] = [o for o in _raw_embed_origins.split(",") if o]

# Exact origins for CORS pre-flight — Flask-CORS does not support wildcards.
# Falls back to _EMBED_ORIGINS if not set.
_raw_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
_CORS_ORIGINS: list[str] = [o for o in _raw_cors_origins.split(",") if o] or _EMBED_ORIGINS

ENABLE_CORS = True
CORS_OPTIONS = {
    "origins": _CORS_ORIGINS,
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-CSRFToken"],
    "supports_credentials": True,
    "max_age": 3600,
}

EMBED_ALLOWED_DOMAINS = _EMBED_ORIGINS

ENABLE_PROXY_FIX = True
PROXY_FIX_CONFIG = {"x_for": 1, "x_proto": 1, "x_host": 1, "x_port": 1, "x_prefix": 1}

TALISMAN_ENABLED = True
TALISMAN_CONFIG = {
    "content_security_policy": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'", "'strict-dynamic'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "data:", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "blob:", "https:"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'self'"] + _EMBED_ORIGINS,
    },
    "content_security_policy_nonce_in": ["script-src"],
    "force_https": False,
}

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# =============================================================================
# 13. FEATURE FLAGS
# =============================================================================
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS_SET": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_RBAC": True,
    "EMBEDDED_SUPERSET": True,
    "ENABLE_EXPLORE_JSON_CSRF_PROTECTION": False,
    "SCARF_ANALYTICS": False,
    "DRILL_BY": True,
}

HTML_SANITIZATION = True
ALLOW_HTML_IN_MARKDOWN = True
