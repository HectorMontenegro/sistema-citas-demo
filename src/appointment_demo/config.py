from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

LOCAL_DEMO_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def ensure_local_demo_url(value: str) -> str:
    """Acepta exclusivamente el portal HTTP local incluido en el proyecto."""
    parsed = urlparse(value)

    if parsed.scheme != "http":
        raise ValueError("El portal de demostracion debe usar HTTP local.")
    if parsed.hostname not in LOCAL_DEMO_HOSTS:
        raise ValueError("Solo se permite un host de loopback.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("La URL de demostracion contiene componentes no permitidos.")
    if parsed.path.rstrip("/") != "/demo":
        raise ValueError("La URL debe terminar en /demo.")

    return value.rstrip("/")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or "CHANGE_ME" in value.upper():
        raise RuntimeError(f"Falta configurar {name} con un valor local seguro.")
    return value


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise RuntimeError(f"{name} debe ser mayor que cero.")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw not in {"true", "false"}:
        raise RuntimeError(f"{name} debe ser true o false.")
    return raw == "true"


@dataclass(frozen=True, slots=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    api_token: str
    demo_access_code: str
    demo_portal_base_url: str
    worker_poll_seconds: int
    worker_max_attempts: int
    selenium_headless: bool
    log_level: str

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()

        api_token = _required("API_TOKEN")
        if len(api_token) < 24:
            raise RuntimeError("API_TOKEN debe tener al menos 24 caracteres.")

        demo_access_code = _required("DEMO_ACCESS_CODE")
        if len(demo_access_code) < 12:
            raise RuntimeError("DEMO_ACCESS_CODE debe tener al menos 12 caracteres.")

        return cls(
            db_host=os.getenv("DB_HOST", "127.0.0.1").strip(),
            db_port=_positive_int("DB_PORT", 3307),
            db_name=_required("DB_NAME"),
            db_user=_required("DB_USER"),
            db_password=_required("DB_PASSWORD"),
            api_token=api_token,
            demo_access_code=demo_access_code,
            demo_portal_base_url=ensure_local_demo_url(
                os.getenv(
                    "DEMO_PORTAL_BASE_URL",
                    "http://127.0.0.1:5000/demo",
                ).strip()
            ),
            worker_poll_seconds=_positive_int("WORKER_POLL_SECONDS", 10),
            worker_max_attempts=_positive_int("WORKER_MAX_ATTEMPTS", 3),
            selenium_headless=_boolean("SELENIUM_HEADLESS", True),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
