r"""Windows: run tests in a disposable PG cluster, never the configured project DB.

Usage: python scripts/test_postgres.py --pg-bin "D:\Program Files\PostgreSQL\18\bin"
Requires the matching pgvector extension installed beside those PostgreSQL binaries.
"""

import argparse
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55432)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This helper targets Windows. Use a disposable test DB on other platforms.")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))  # Fail before creating anything if occupied.
    root = Path(tempfile.mkdtemp(prefix="akh-disposable-pg-")).resolve()
    data = root / "data"
    password = secrets.token_urlsafe(32)
    password_file = root / "password"
    password_file.write_text(password, encoding="utf-8")
    started = False

    def run(binary: str, *arguments: str) -> None:
        log = root / f"{binary}.out"
        # A daemon may inherit stdout on Windows. A file avoids waiting for EOF
        # on a pipe that the still-running PostgreSQL process holds open.
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run(
                [str(args.pg_bin / (binary + ".exe")), *arguments],
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        print(log.read_text(encoding="utf-8", errors="replace"), flush=True)
        result.check_returncode()

    try:
        run(
            "initdb",
            "-D",
            str(data),
            "-U",
            "akh_tests",
            "--pwfile",
            str(password_file),
            "--auth=scram-sha-256",
            "--encoding=UTF8",
            "--locale=C",
        )
        password_file.unlink()
        run(
            "pg_ctl",
            "-D",
            str(data),
            "-l",
            str(root / "postgres.log"),
            "-o",
            f"-h 127.0.0.1 -p {args.port}",
            "-w",
            "start",
        )
        started = True
        from sqlalchemy import create_engine, text

        url = f"postgresql+psycopg://akh_tests:{password}@127.0.0.1:{args.port}/postgres"
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
        with engine.begin() as db:
            actual = Path(db.scalar(text("SHOW data_directory"))).resolve()
            assert actual == data.resolve(), "Refusing to test an unrelated cluster"
            db.execute(text("CREATE EXTENSION vector WITH SCHEMA public"))
        engine.dispose()
        env = {
            **os.environ,
            "DATABASE_URL": url,
            "TEST_DATABASE_URL": url,
            "APP_MODE": "local-demo",
            "APP_ENV": "development",
        }
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            env=env,
            cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(result.stdout, flush=True)
        return result.returncode
    finally:
        if started and (data / "postmaster.pid").exists():
            run("pg_ctl", "-D", str(data), "-m", "fast", "-w", "stop")
        # Only delete the exact temporary root this process created.
        temp_root = Path(tempfile.gettempdir()).resolve()
        if root.parent == temp_root and root.name.startswith("akh-disposable-pg-"):
            shutil.rmtree(root)


if __name__ == "__main__":
    raise SystemExit(main())
