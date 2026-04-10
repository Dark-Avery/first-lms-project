from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote, urlparse


def build_default_database_settings(
    *,
    env: Mapping[str, str] | None = None,
    base_dir: Path,
) -> dict[str, str]:
    source = env or os.environ

    if _has_db_env(source):
        return {
            "ENGINE": source.get("DB_ENGINE", "django.db.backends.sqlite3"),
            "NAME": source.get("DB_NAME", str(base_dir / "db.sqlite3")),
            "USER": source.get("DB_USER", ""),
            "PASSWORD": source.get("DB_PASSWORD", ""),
            "HOST": source.get("DB_HOST", ""),
            "PORT": source.get("DB_PORT", ""),
        }

    if source.get("POSTGRES_CONNECTION_STRING"):
        return _build_from_postgres_connection_string(
            source["POSTGRES_CONNECTION_STRING"],
        )

    if _has_postgres_env(source):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": source.get("POSTGRES_DATABASE_NAME", source.get("POSTGRES_DB", "")),
            "USER": source.get("POSTGRES_USERNAME", source.get("POSTGRES_USER", "")),
            "PASSWORD": source.get("POSTGRES_PASSWORD", ""),
            "HOST": source.get("POSTGRES_HOST", ""),
            "PORT": source.get("POSTGRES_PORT", ""),
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(base_dir / "db.sqlite3"),
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }


def build_default_celery_broker_url(env: Mapping[str, str] | None = None) -> str:
    source = env or os.environ

    if source.get("CELERY_BROKER_URL"):
        return source["CELERY_BROKER_URL"]

    if source.get("POSTGRES_CONNECTION_STRING"):
        return _build_broker_url_from_connection_string(
            source["POSTGRES_CONNECTION_STRING"],
        )

    if _has_postgres_env(source):
        database_name = source.get("POSTGRES_DATABASE_NAME", source.get("POSTGRES_DB", ""))
        username = source.get("POSTGRES_USERNAME", source.get("POSTGRES_USER", ""))
        password = source.get("POSTGRES_PASSWORD", "")
        host = source.get("POSTGRES_HOST", "")
        port = source.get("POSTGRES_PORT", "")
        return (
            "sqla+postgresql+psycopg2://"
            f"{username}:{password}@{host}:{port}/{database_name}"
        )

    return ""


def _has_db_env(env: Mapping[str, str]) -> bool:
    return any(
        env.get(key)
        for key in (
            "DB_ENGINE",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "DB_HOST",
            "DB_PORT",
        )
    )


def _has_postgres_env(env: Mapping[str, str]) -> bool:
    return any(
        env.get(key)
        for key in (
            "POSTGRES_DATABASE_NAME",
            "POSTGRES_DB",
            "POSTGRES_USERNAME",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
        )
    )


def _build_from_postgres_connection_string(connection_string: str) -> dict[str, str]:
    parsed = urlparse(connection_string)

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


def _build_broker_url_from_connection_string(connection_string: str) -> str:
    parsed = urlparse(connection_string)
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    hostname = parsed.hostname or ""
    port = str(parsed.port or "")
    database_name = parsed.path.lstrip("/")

    return (
        "sqla+postgresql+psycopg2://"
        f"{username}:{password}@{hostname}:{port}/{database_name}"
    )
