from datetime import date, time, timedelta

from appointment_demo.domain import (
    AppointmentRequest,
    Confirmation,
    RequestStatus,
    SelectedSlot,
)
from appointment_demo.service import RequestProcessor


class FakeRepository:
    def __init__(self, cancel_checks=None):
        today = date.today()
        self.request = AppointmentRequest(
            id="9f6ea5a7-6784-45cb-aed1-e0379a0d88fe",
            contact_email="demo@example.test",
            preferred_from=today,
            preferred_to=today + timedelta(days=30),
            status=RequestStatus.PROCESSING,
            attempts=1,
            cancel_requested=False,
        )
        self.cancel_checks = list(cancel_checks or [False, False])
        self.completed = False
        self.cancelled = False
        self.retried = False
        self.errored = False

    def claim_next(self):
        item, self.request = self.request, None
        return item

    def is_cancel_requested(self, request_id):
        return self.cancel_checks.pop(0)

    def mark_cancelled(self, request_id):
        self.cancelled = True

    def mark_completed(self, request_id, slot, confirmation_code):
        self.completed = True

    def retry_or_fail(self, request_id, attempts, max_attempts):
        self.retried = True

    def mark_error(self, request_id, attempts, max_attempts, public_error):
        self.errored = True

    def add_event(self, request_id, event_type, detail):
        pass


class FakeSession:
    def __init__(self, slot):
        self.slot = slot
        self.confirm_called = False
        self.closed = False

    def find_slot(self, request):
        return self.slot

    def confirm(self, slot):
        self.confirm_called = True
        return Confirmation(code="DEMO-123")

    def close(self):
        self.closed = True


class FakeFactory:
    def __init__(self, session):
        self.session = session

    def open(self, request):
        return self.session


class FakeNotifier:
    def __init__(self):
        self.called = False

    def notify(self, request, slot, confirmation):
        self.called = True


def test_completes_a_simulated_request():
    repository = FakeRepository()
    slot = SelectedSlot(date.today() + timedelta(days=7), time(9, 0))
    session = FakeSession(slot)
    notifier = FakeNotifier()
    processor = RequestProcessor(
        repository,
        FakeFactory(session),
        notifier,
        max_attempts=3,
    )

    status = processor.process_one()

    assert status is RequestStatus.COMPLETED
    assert repository.completed
    assert session.confirm_called
    assert session.closed
    assert notifier.called


def test_cancellation_is_checked_again_before_confirmation():
    repository = FakeRepository(cancel_checks=[False, True])
    slot = SelectedSlot(date.today() + timedelta(days=7), time(9, 0))
    session = FakeSession(slot)
    processor = RequestProcessor(
        repository,
        FakeFactory(session),
        FakeNotifier(),
        max_attempts=3,
    )

    status = processor.process_one()

    assert status is RequestStatus.CANCELLED
    assert repository.cancelled
    assert not session.confirm_called
    assert session.closed


def test_no_availability_schedules_a_limited_retry():
    repository = FakeRepository(cancel_checks=[False])
    session = FakeSession(None)
    processor = RequestProcessor(
        repository,
        FakeFactory(session),
        FakeNotifier(),
        max_attempts=3,
    )

    status = processor.process_one()

    assert status is RequestStatus.PENDING
    assert repository.retried
    assert not session.confirm_called
