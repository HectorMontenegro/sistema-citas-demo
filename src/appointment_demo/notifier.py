from __future__ import annotations

import logging

from appointment_demo.domain import AppointmentRequest, Confirmation, SelectedSlot


class LoggingNotifier:
    """Notificacion local: no envia correos ni expone datos personales."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def notify(
        self,
        request: AppointmentRequest,
        slot: SelectedSlot,
        confirmation: Confirmation,
    ) -> None:
        self._logger.info(
            "Notificacion simulada request_id=%s date=%s time=%s confirmation=%s",
            request.id,
            slot.appointment_date.isoformat(),
            slot.appointment_time.isoformat(timespec="minutes"),
            confirmation.code,
        )
