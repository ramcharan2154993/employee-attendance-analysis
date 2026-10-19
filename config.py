"""Configuration settings for database connections and environment variables."""

import os
import warnings
from dotenv import load_dotenv

load_dotenv()

DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_USER: str | None = os.getenv("DB_USER")
DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")
DB_NAME: str | None = os.getenv("DB_NAME")
DB_TEST_NAME: str | None = os.getenv("DB_TEST_NAME")
APP_NAME: str = "AttendIQ"
APP_TAGLINE: str = "Attendance intelligence for modern teams"
APP_ENV: str = os.getenv("APP_ENV", "development").lower().strip()


def _resolve_secret_key() -> str | None:
    """Resolve SECRET_KEY with deprecated fallback to FLASK_SECRET_KEY only in dev."""
    key = os.getenv("SECRET_KEY")
    if not key:
        old_key = os.getenv("FLASK_SECRET_KEY")
        if old_key:
            env = os.getenv("APP_ENV", "development").lower().strip()
            if env == "development":
                warnings.warn(
                    "FLASK_SECRET_KEY is deprecated and will be removed in a future release. Use SECRET_KEY instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                key = old_key
    return key


SECRET_KEY: str | None = _resolve_secret_key()
# Deprecated backward compatibility alias
FLASK_SECRET_KEY: str | None = SECRET_KEY
