from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import date, timedelta

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template_string,
    request,
    url_for,
)

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Portal local de demostracion</title></head>
<body>
  <main>
    <h1>Portal local de demostracion</h1>
    <p>No introduzcas credenciales ni informacion real.</p>
    <form method="post">
      <label>Solicitud <input id="request_id" name="request_id" required></label>
      <label>Codigo local <input id="access_code" name="access_code" required></label>
      <label>
        <input id="accept_demo_terms" name="accept_demo_terms" type="checkbox" required>
        Confirmo que utilizo datos ficticios.
      </label>
      <button id="login_submit" type="submit">Continuar</button>
    </form>
  </main>
</body>
</html>
"""


APPOINTMENT_TEMPLATE = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Disponibilidad simulada</title></head>
<body>
  <main>
    <h1>Disponibilidad simulada</h1>
    <form id="appointment_form" method="post">
      <input id="selected_date" name="selected_date" type="hidden" required>
      <div>
        {% for slot_date in available_dates %}
          <button
            type="button"
            data-slot-date="{{ slot_date }}"
            onclick="document.getElementById('selected_date').value='{{ slot_date }}'"
          >{{ slot_date }}</button>
        {% endfor %}
      </div>
      <label>Hora
        <select id="slot_time" name="slot_time" required>
          <option value="">Seleccione</option>
          {% for slot_time in available_times %}
            <option value="{{ slot_time }}">{{ slot_time }}</option>
          {% endfor %}
        </select>
      </label>
      <button id="confirm_appointment" type="submit">Confirmar simulacion</button>
    </form>
  </main>
</body>
</html>
"""


CONFIRMATION_TEMPLATE = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Confirmacion simulada</title></head>
<body>
  <main>
    <h1>Confirmacion simulada</h1>
    <p>Codigo: <span id="confirmation_code">{{ confirmation_code }}</span></p>
    <p>Fecha: <span id="confirmed_date">{{ selected_date }}</span></p>
    <p>Hora: <span id="confirmed_time">{{ selected_time }}</span></p>
  </main>
</body>
</html>
"""


def _available_dates() -> list[str]:
    today = date.today()
    return [(today + timedelta(days=offset)).isoformat() for offset in range(7, 85, 7)]


def create_demo_blueprint(access_code: str) -> Blueprint:
    blueprint = Blueprint("demo_portal", __name__, url_prefix="/demo")

    @blueprint.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template_string(LOGIN_TEMPLATE)

        submitted_code = request.form.get("access_code", "")
        request_id = request.form.get("request_id", "")
        accepted = request.form.get("accept_demo_terms") == "on"

        if not accepted or not hmac.compare_digest(submitted_code, access_code):
            abort(403)
        try:
            uuid.UUID(request_id)
        except ValueError:
            abort(400)

        return redirect(url_for("demo_portal.appointments", request_id=request_id))

    @blueprint.route("/appointments/<uuid:request_id>", methods=["GET", "POST"])
    def appointments(request_id: uuid.UUID):
        available_dates = _available_dates()
        available_times = ["09:00", "11:30", "15:00"]

        if request.method == "GET":
            return render_template_string(
                APPOINTMENT_TEMPLATE,
                available_dates=available_dates,
                available_times=available_times,
            )

        selected_date = request.form.get("selected_date", "")
        selected_time = request.form.get("slot_time", "")
        if selected_date not in available_dates or selected_time not in available_times:
            abort(400)

        confirmation_code = (
            hashlib.sha256(f"{request_id}:{selected_date}:{selected_time}".encode())
            .hexdigest()[:16]
            .upper()
        )
        return render_template_string(
            CONFIRMATION_TEMPLATE,
            confirmation_code=confirmation_code,
            selected_date=selected_date,
            selected_time=selected_time,
        )

    return blueprint
