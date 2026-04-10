from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_settings_import(
    *,
    db_engine: str,
    secret_key: str | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("SECRET_KEY", None)
    env["DB_ENGINE"] = db_engine
    env["PYTHONPATH"] = str(REPO_ROOT)

    if secret_key is not None:
        env["SECRET_KEY"] = secret_key

    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from config.settings import SECRET_KEY; print(SECRET_KEY)",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def test_settings_allow_dev_secret_for_local_sqlite_runtime():
    result = run_settings_import(
        db_engine="django.db.backends.sqlite3",
        secret_key=None,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "dev-secret-key"


def test_settings_require_secret_key_for_non_sqlite_runtime():
    result = run_settings_import(
        db_engine="django.db.backends.postgresql",
        secret_key=None,
    )

    assert result.returncode != 0
    assert "SECRET_KEY must be set when using a non-sqlite database." in result.stderr
