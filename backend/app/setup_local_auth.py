"""Enable local development accounts while preserving the existing database URL."""

import secrets
from pathlib import Path


def main() -> None:
    path = Path(".env")
    if not path.is_file():
        raise SystemExit("Run from backend/. Copy .env.example to .env and set DATABASE_URL first.")
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    current = {
        name.strip(): value.strip()
        for line in lines
        if "=" in line and not line.lstrip().startswith("#")
        for name, value in [line.split("=", 1)]
    }
    if current.get("APP_ENV", "development").strip("'\"").casefold() == "production":
        raise SystemExit("Refusing to enable development registration in production.")
    key = current.get("SECURITY_KEY", "").strip().strip('"').strip("'")
    updates = {
        "APP_MODE": "authenticated",
        "APP_ENV": "development",
        "ALLOW_REGISTRATION": "true",
        "AUTH_COOKIE_SECURE": "false",
        "SECURITY_KEY": key if len(key) >= 32 else secrets.token_urlsafe(48),
    }
    output = []
    for line in lines:
        name = line.split("=", 1)[0].strip()
        output.append(f"{name}={updates.pop(name)}" if name in updates else line)
    output.extend(f"{name}={value}" for name, value in updates.items())
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(
        "Local authentication enabled. Restart the backend and register in the UI. "
        "No account was created."
    )


if __name__ == "__main__":
    main()
