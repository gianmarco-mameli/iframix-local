#!/usr/bin/env python3

import os
import shlex
import subprocess
import sys
from pathlib import Path


APP_DIR = Path("/home/app")


def log(message: str) -> None:
    print(f"[entrypoint] {message}", flush=True)


def env_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default) == "1"


def run_command(args: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=str(cwd) if cwd else None, check=True)


def ensure_certificate() -> None:
    cert_file = os.environ.get("CERT_FILE", "/home/app/server.crt")
    key_file = os.environ.get("KEY_FILE", "/home/app/server.key")

    if os.path.isfile(cert_file) and os.path.isfile(key_file):
        log(f"Using existing SSL certificate at {cert_file}")
        return

    log("Generating self-signed SSL certificate...")
    run_command([
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-keyout",
        key_file,
        "-out",
        cert_file,
        "-days",
        "365",
        "-nodes",
        "-subj",
        "/CN=ifp.ga.codethriving.com",
        "-addext",
        (
            "subjectAltName=DNS:ifp.ga.codethriving.com,"
            "DNS:api.qiniu.com,DNS:upload-z2.qiniup.com,"
            "DNS:up-z2.qiniup.com,DNS:iframixcn.codethriving.com"
        ),
    ])
    log(f"Certificate written to {cert_file}")


def fetch_assets() -> None:
    if not env_flag("AUTO_FETCH_ASSETS", "1"):
        log("AUTO_FETCH_ASSETS=0 - skipping asset download step.")
        return

    asset_fetch_version = os.environ.get("ASSET_FETCH_VERSION", "")
    dns_server = os.environ.get("DNS_SERVER", "").strip() or "8.8.8.8"

    log(f"Fetching webapp and weather assets (DNS server: {dns_server})...")
    run_command(
        [
            sys.executable,
            "scripts/fetch-webapp-assets.py",
            asset_fetch_version,
            "--dns-server",
            dns_server,
        ],
        cwd=APP_DIR,
    )
    run_command(
        [
            sys.executable,
            "scripts/fetch-pad1-webapp-assets.py",
            asset_fetch_version,
            "--dns-server",
            dns_server,
        ],
        cwd=APP_DIR,
    )
    run_command(
        [
            sys.executable,
            "scripts/fetch-download-assets.py",
            "--dns-server",
            dns_server,
        ],
        cwd=APP_DIR,
    )
    run_command(
        [
            sys.executable,
            "scripts/fetch-weather-icons.py",
            "--dns-server",
            dns_server,
        ],
        cwd=APP_DIR,
    )
    run_command(
        [sys.executable, "scripts/apply-local-index-html-patch.py"],
        cwd=APP_DIR,
    )
    log("Asset fetch complete.")


def start_router() -> subprocess.Popen[bytes]:
    log("Starting iCharGuard router (background)...")

    env = os.environ.copy()
    env.setdefault("BROKER_HOST", "mosquitto")
    env.setdefault("BROKER_PORT", "1883")
    env.setdefault("BROKER_WS_PORT", "9001")

    process = subprocess.Popen(
        [sys.executable, "/home/app/icharguard-router.py", "--headless"],
        env=env,
    )
    log(f"Router PID: {process.pid}")
    return process


def run_api() -> None:
    log("Starting iCharGuard API server...")

    sys.path.insert(0, "/home/app")

    import src.api.config as cfg

    cfg.MQTT_BROKER_HOST = os.environ.get("BROKER_HOST", "mosquitto")
    cfg.MQTT_BROKER_PORT = int(os.environ.get("BROKER_PORT", "1883"))
    cfg.MOSQUITTO_WS_HOST = os.environ.get("BROKER_HOST", "mosquitto")
    cfg.MOSQUITTO_WS_PORT = int(os.environ.get("BROKER_WS_PORT", "9001"))

    extra = os.environ.get("API_EXTRA_ARGS", "").strip()
    extra_parts = shlex.split(extra) if extra else []
    if "--no-ssl" in extra_parts:
        raise SystemExit(
            "--no-ssl is not supported in this container configuration"
        )
    sys.argv = ["/home/app/icharguard-api.py", *extra_parts]

    from src.api.handler import main

    main()


def main() -> int:
    ensure_certificate()
    fetch_assets()
    start_router()
    run_api()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
