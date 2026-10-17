"""Configuration settings for database connections and environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_USER: str | None = os.getenv("DB_USER")
DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")
DB_NAME: str | None = os.getenv("DB_NAME")
DB_TEST_NAME: str | None = os.getenv("DB_TEST_NAME")
FLASK_SECRET_KEY: str | None = os.getenv("FLASK_SECRET_KEY")
