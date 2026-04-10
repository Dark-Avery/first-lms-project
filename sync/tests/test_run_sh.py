from __future__ import annotations

import os
import subprocess
import textwrap
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_SH = REPO_ROOT / "run.sh"


def write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def make_stub_commands(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    write_executable(
        bin_dir / "python",
        textwrap.dedent(
            """\
            #!/bin/sh
            echo "python $*" >> "$RUN_SH_LOG"
            if [ "$1" = "manage.py" ]; then
              exit 0
            fi
            trap 'exit 0' TERM INT
            while :; do sleep 1; done
            """
        ),
    )
    write_executable(
        bin_dir / "gunicorn",
        textwrap.dedent(
            """\
            #!/bin/sh
            echo "gunicorn $*" >> "$RUN_SH_LOG"
            trap 'exit 0' TERM INT
            while :; do sleep 1; done
            """
        ),
    )
    return bin_dir


def run_script(tmp_path: Path, *, broker_url: str | None) -> tuple[str, str]:
    log_path = tmp_path / "run.log"
    env = os.environ.copy()
    env["PATH"] = f"{make_stub_commands(tmp_path)}:{env['PATH']}"
    env["RUN_SH_LOG"] = str(log_path)
    if broker_url is None:
        env.pop("CELERY_BROKER_URL", None)
    else:
        env["CELERY_BROKER_URL"] = broker_url

    process = subprocess.Popen(  # noqa: S603
        ["bash", str(RUN_SH)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(1)
    process.terminate()
    stdout, stderr = process.communicate(timeout=5)
    log_contents = log_path.read_text()
    return stdout + stderr, log_contents


def test_run_sh_starts_web_without_broker_and_skips_celery(tmp_path: Path):
    output, log_contents = run_script(tmp_path, broker_url=None)

    assert "CELERY_BROKER_URL is not set; starting web without worker and beat." in output
    assert "python manage.py migrate" in log_contents
    assert "gunicorn config.wsgi:application" in log_contents
    assert "python -m celery -A config worker -l INFO" not in log_contents
    assert "python -m celery -A config beat -l INFO" not in log_contents


def test_run_sh_starts_worker_beat_and_gunicorn_when_broker_is_set(tmp_path: Path):
    _, log_contents = run_script(tmp_path, broker_url="sqla+postgresql://example")

    assert "python manage.py migrate" in log_contents
    assert "gunicorn config.wsgi:application" in log_contents
    assert "python -m celery -A config worker -l INFO" in log_contents
    assert "python -m celery -A config beat -l INFO" in log_contents
