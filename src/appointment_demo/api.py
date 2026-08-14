from __future__ import annotations

import hmac
import logging
import re
import uuid
from collections.abc import Callable
from datetime import date, timedelta
from functools import wraps
from typing import Any

from flask import Flask, jsonify, request

from appointment_demo.config import Settings
from appointment_demo.domain import AppointmentRequest
from appointment_demo.mock_portal import create_demo_blueprint
from appointment_demo.repository import MySQLRequestRepository

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_FIELDS = {"contact_email", "preferred_from", "preferred_to"}
FORBIDDEN_FIELDS = {
    "password",
    "credentials",
    "username",
    "portal_url",
    "cookie",
    "session",
}


def _serialize(item: AppointmentRequest) -> dict[str, Any]:
    return {
        "id": item.id,
        "status": item.status.value,
        "attempts": item.attempts,
        "cancel_requested": item.cancel_requested,
        "preferred_from": item.preferred_from.isoformat(),
        "preferred_to": item.preferred_to.isoformat(),
    }


def _parse_request_payload(payload: dict[str, Any]) -> tuple[str, date, date]:
    keys = set(payload)
    if keys & FORBIDDEN_FIELDS:
        raise ValueError("La API de demostracion no acepta credenciales de terceros.")
    if keys != ALLOWED_FIELDS:
        raise ValueError("Los campos enviados no coinciden con el contrato de la API.")

    email = str(payload["contact_email"]).strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("El correo de demostracion no tiene un formato valido.")

    try:
        preferred_from = date.fromisoformat(str(payload["preferred_from"]))
        preferred_to = date.fromisoformat(str(payload["preferred_to"]))
    except ValueError as exc:
        raise ValueError("Las fechas deben usar el formato YYYY-MM-DD.") from exc

    today = date.today()
    if preferred_from < today:
        raise ValueError("La fecha inicial no puede estar en el pasado.")
    if preferred_to < preferred_from:
        raise ValueError("La fecha final no puede ser anterior a la inicial.")
    if preferred_to - preferred_from > timedelta(days=90):
        raise ValueError("El rango de demostracion no puede exceder 90 dias.")
    if preferred_to > today + timedelta(days=180):
        raise ValueError("La fecha final no puede superar 180 dias desde hoy.")

    return email, preferred_from, preferred_to


def _valid_uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value.lower()
    except ValueError:
        return False


def create_app(
    settings: Settings | None = None,
    repository: MySQLRequestRepository | None = None,
) -> Flask:
    settings = settings or Settings.from_environment()
    repository = repository or MySQLRequestRepository(settings)

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024
    app.register_blueprint(create_demo_blueprint(settings.demo_access_code))

    def require_token(function: Callable):
        @wraps(function)
        def wrapped(*args, **kwargs):
            provided = request.headers.get("X-Demo-Token", "")
            if not hmac.compare_digest(provided, settings.api_token):
                return jsonify({"error": "No autorizado"}), 401
            return function(*args, **kwargs)

        return wrapped

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "appointment-demo"})

    @app.post("/api/requests")
    @require_token
    def create_request():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Se requiere un objeto JSON"}), 400

        try:
            email, preferred_from, preferred_to = _parse_request_payload(payload)
            item = repository.create_request(email, preferred_from, preferred_to)
            return jsonify(_serialize(item)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            logger.exception("No fue posible crear una solicitud de demostracion")
            return jsonify({"error": "No fue posible procesar la solicitud"}), 500

    @app.get("/api/requests/<request_id>")
    @require_token
    def get_request(request_id: str):
        if not _valid_uuid(request_id):
            return jsonify({"error": "Identificador invalido"}), 400
        try:
            item = repository.get_request(request_id)
            if item is None:
                return jsonify({"error": "Solicitud no encontrada"}), 404
            return jsonify(_serialize(item))
        except Exception:
            logger.exception("No fue posible consultar request_id=%s", request_id)
            return jsonify({"error": "No fue posible consultar la solicitud"}), 500

    @app.delete("/api/requests/<request_id>")
    @require_token
    def cancel_request(request_id: str):
        if not _valid_uuid(request_id):
            return jsonify({"error": "Identificador invalido"}), 400
        try:
            if not repository.request_cancellation(request_id):
                return jsonify({"error": "La solicitud no admite cancelacion"}), 409
            return jsonify({"status": "cancellation_requested"}), 202
        except Exception:
            logger.exception("No fue posible cancelar request_id=%s", request_id)
            return jsonify({"error": "No fue posible cancelar la solicitud"}), 500

    return app


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
