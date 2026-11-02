"""Called only inside test_postgres.py's verified disposable PostgreSQL cluster."""

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def capture(environment: dict[str, str], temporary_root: Path) -> int:
    backend = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8810))
    env = {
        **environment,
        "APP_MODE": "authenticated",
        "APP_ENV": "development",
        "ALLOW_REGISTRATION": "true",
        "SECURITY_KEY": secrets.token_urlsafe(48),
        "AI_PROVIDER": "fake",
        "OPENAI_API_KEY": "",
        "AUTH_COOKIE_SECURE": "false",
        "CORS_ORIGINS": json.dumps(["http://127.0.0.1:3200"]),
        "ALLOWED_HOSTS": json.dumps(["127.0.0.1"]),
        "PORTFOLIO_API_URL": "http://127.0.0.1:8810",
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend,
        env=env,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    with (temporary_root / "api.log").open("w", encoding="utf-8") as log:
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8810",
                "--no-access-log",
            ],
            cwd=backend,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if api.poll() is not None:
                    raise RuntimeError("Disposable API exited. Inspect its synthetic test log.")
                try:
                    with urlopen(env["PORTFOLIO_API_URL"] + "/health", timeout=1) as response:
                        if json.load(response)["mode"] == "authenticated":
                            break
                except (URLError, TimeoutError):
                    time.sleep(0.2)
            else:
                raise RuntimeError("Disposable API did not become ready.")
            command = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/c",
                "npm.cmd",
                "run",
                "portfolio:capture",
            ]
            result = subprocess.run(
                command,
                cwd=backend.parent / "frontend",
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print(result.stdout, flush=True)
            return result.returncode
        finally:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait()
