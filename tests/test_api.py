from datetime import date, timedelta

from appointment_demo.api import create_app
from appointment_demo.config import Settings
from appointment_demo.domain import AppointmentRequest, RequestStatus


class FakeRepository:
    def __init__(self):
        self.item = None

    def create_request(self, contact_email, preferred_from, preferred_to):
        self.item = AppointmentRequest(
            id="52df9951-dc6f-4318-af91-4c0cc4a8fd00",
            contact_email=contact_email,
            preferred_from=preferred_from,
            preferred_to=preferred_to,
            status=RequestStatus.PENDING,
            attempts=0,
            cancel_requested=False,
        )
        return self.item

    def get_request(self, request_id):
        return self.item if self.item and self.item.id == request_id else None

    def request_cancellation(self, request_id):
        return bool(self.item and self.item.id == request_id)


def settings():
    return Settings(
        db_host="127.0.0.1",
        db_port=3307,
        db_name="demo",
        db_user="demo",
        db_password="local-test-only",
        api_token="a-local-test-token-with-24-chars",
        demo_access_code="local-demo-code",
        demo_portal_base_url="http://127.0.0.1:5000/demo",
        worker_poll_seconds=1,
        worker_max_attempts=3,
        selenium_headless=True,
        log_level="INFO",
    )


def valid_payload():
    start = date.today() + timedelta(days=1)
    return {
        "contact_email": "demo@example.test",
        "preferred_from": start.isoformat(),
        "preferred_to": (start + timedelta(days=30)).isoformat(),
    }


def test_api_requires_token():
    app = create_app(settings(), FakeRepository())
    client = app.test_client()
    response = client.post("/api/requests", json=valid_payload())
    assert response.status_code == 401


def test_api_rejects_third_party_credentials():
    app = create_app(settings(), FakeRepository())
    client = app.test_client()
    payload = valid_payload() | {"password": "must-not-be-accepted"}
    response = client.post(
        "/api/requests",
        json=payload,
        headers={"X-Demo-Token": settings().api_token},
    )
    assert response.status_code == 400
    assert "no acepta credenciales" in response.get_json()["error"]


def test_api_creates_a_synthetic_request_without_returning_email():
    repository = FakeRepository()
    app = create_app(settings(), repository)
    client = app.test_client()
    response = client.post(
        "/api/requests",
        json=valid_payload(),
        headers={"X-Demo-Token": settings().api_token},
    )
    body = response.get_json()
    assert response.status_code == 201
    assert body["status"] == "PENDING"
    assert "contact_email" not in body
