from __future__ import annotations

import logging
from typing import Protocol

from appointment_demo.domain import (
    AppointmentRequest,
    Confirmation,
    RequestStatus,
    SelectedSlot,
)


class Repository(Protocol):
    def claim_next(self) -> AppointmentRequest | None: ...

    def is_cancel_requested(self, request_id: str) -> bool: ...

    def mark_cancelled(self, request_id: str) -> None: ...

    def mark_completed(
        self,
        request_id: str,
        slot: SelectedSlot,
        confirmation_code: str,
    ) -> None: ...

    def retry_or_fail(
        self,
        request_id: str,
        attempts: int,
        max_attempts: int,
    ) -> None: ...

    def mark_error(
        self,
        request_id: str,
        attempts: int,
        max_attempts: int,
        public_error: str,
    ) -> None: ...

    def add_event(self, request_id: str, event_type: str, detail: str) -> None: ...


class PortalSession(Protocol):
    def find_slot(self, request: AppointmentRequest) -> SelectedSlot | None: ...

    def confirm(self, slot: SelectedSlot) -> Confirmation: ...

    def close(self) -> None: ...


class PortalFactory(Protocol):
    def open(self, request: AppointmentRequest) -> PortalSession: ...


class Notifier(Protocol):
    def notify(
        self,
        request: AppointmentRequest,
        slot: SelectedSlot,
        confirmation: Confirmation,
    ) -> None: ...


class RequestProcessor:
    def __init__(
        self,
        repository: Repository,
        portal_factory: PortalFactory,
        notifier: Notifier,
        max_attempts: int,
    ) -> None:
        self._repository = repository
        self._portal_factory = portal_factory
        self._notifier = notifier
        self._max_attempts = max_attempts
        self._logger = logging.getLogger(__name__)

    def process_one(self) -> RequestStatus | None:
        request = self._repository.claim_next()
        if request is None:
            return None

        session: PortalSession | None = None
        try:
            if self._repository.is_cancel_requested(request.id):
                self._repository.mark_cancelled(request.id)
                return RequestStatus.CANCELLED

            session = self._portal_factory.open(request)
            slot = session.find_slot(request)
            if slot is None:
                self._repository.retry_or_fail(
                    request.id,
                    request.attempts,
                    self._max_attempts,
                )
                return (
                    RequestStatus.PENDING
                    if request.attempts < self._max_attempts
                    else RequestStatus.FAILED
                )

            # Comprobacion critica inmediatamente antes de confirmar.
            # Si la consulta de BD falla, la excepcion impide la confirmacion.
            if self._repository.is_cancel_requested(request.id):
                self._repository.mark_cancelled(request.id)
                return RequestStatus.CANCELLED

            confirmation = session.confirm(slot)
            self._repository.mark_completed(
                request.id,
                slot,
                confirmation.code,
            )

            try:
                self._notifier.notify(request, slot, confirmation)
            except Exception:
                self._logger.exception(
                    "Fallo la notificacion local request_id=%s",
                    request.id,
                )
                try:
                    self._repository.add_event(
                        request.id,
                        "NOTIFICATION_FAILED",
                        "La notificacion local no pudo completarse",
                    )
                except Exception:
                    self._logger.exception(
                        "No se pudo registrar el fallo de notificacion request_id=%s",
                        request.id,
                    )

            return RequestStatus.COMPLETED

        except Exception:
            self._logger.exception(
                "Fallo controlado durante el procesamiento request_id=%s",
                request.id,
            )
            try:
                self._repository.mark_error(
                    request.id,
                    request.attempts,
                    self._max_attempts,
                    "Fallo controlado durante la demostracion",
                )
            except Exception:
                self._logger.exception(
                    "No se pudo registrar el error request_id=%s",
                    request.id,
                )
            return (
                RequestStatus.PENDING
                if request.attempts < self._max_attempts
                else RequestStatus.FAILED
            )
        finally:
            if session is not None:
                session.close()
