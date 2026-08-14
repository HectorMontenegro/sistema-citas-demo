from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import mysql.connector

from appointment_demo.config import Settings
from appointment_demo.domain import AppointmentRequest, RequestStatus, SelectedSlot


class MySQLRequestRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _connect(self):
        return mysql.connector.connect(
            host=self._settings.db_host,
            port=self._settings.db_port,
            user=self._settings.db_user,
            password=self._settings.db_password,
            database=self._settings.db_name,
            autocommit=False,
        )

    @staticmethod
    def _to_request(row: dict[str, Any]) -> AppointmentRequest:
        return AppointmentRequest(
            id=row["id"],
            contact_email=row["contact_email"],
            preferred_from=row["preferred_from"],
            preferred_to=row["preferred_to"],
            status=RequestStatus(row["status"]),
            attempts=row["attempts"],
            cancel_requested=bool(row["cancel_requested"]),
        )

    def create_request(
        self,
        contact_email: str,
        preferred_from: date,
        preferred_to: date,
    ) -> AppointmentRequest:
        request_id = str(uuid.uuid4())
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO appointment_requests (
                    id, contact_email, preferred_from, preferred_to
                ) VALUES (%s, %s, %s, %s)
                """,
                (request_id, contact_email, preferred_from, preferred_to),
            )
            cursor.execute(
                """
                INSERT INTO request_events (request_id, event_type, detail)
                VALUES (%s, 'REQUEST_CREATED', 'Solicitud de demostracion creada')
                """,
                (request_id,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        return AppointmentRequest(
            id=request_id,
            contact_email=contact_email,
            preferred_from=preferred_from,
            preferred_to=preferred_to,
            status=RequestStatus.PENDING,
            attempts=0,
            cancel_requested=False,
        )

    def get_request(self, request_id: str) -> AppointmentRequest | None:
        connection = self._connect()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, contact_email, preferred_from, preferred_to,
                       status, attempts, cancel_requested
                FROM appointment_requests
                WHERE id = %s
                LIMIT 1
                """,
                (request_id,),
            )
            row = cursor.fetchone()
            return self._to_request(row) if row else None
        finally:
            cursor.close()
            connection.close()

    def claim_next(self) -> AppointmentRequest | None:
        """Toma una solicitud de forma exclusiva para evitar duplicados."""
        connection = self._connect()
        cursor = connection.cursor(dictionary=True)
        try:
            connection.start_transaction()
            cursor.execute(
                """
                SELECT id, contact_email, preferred_from, preferred_to,
                       status, attempts, cancel_requested
                FROM appointment_requests
                WHERE status = 'PENDING' AND cancel_requested = FALSE
                ORDER BY created_at, id
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
            row = cursor.fetchone()
            if not row:
                connection.commit()
                return None

            cursor.execute(
                """
                UPDATE appointment_requests
                SET status = 'PROCESSING', attempts = attempts + 1
                WHERE id = %s AND status = 'PENDING'
                """,
                (row["id"],),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None

            cursor.execute(
                """
                INSERT INTO request_events (request_id, event_type, detail)
                VALUES (%s, 'PROCESSING_STARTED', 'Solicitud tomada por el worker')
                """,
                (row["id"],),
            )
            connection.commit()

            row["status"] = RequestStatus.PROCESSING.value
            row["attempts"] += 1
            return self._to_request(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def request_cancellation(self, request_id: str) -> bool:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            connection.start_transaction()
            cursor.execute(
                """
                UPDATE appointment_requests
                SET cancel_requested = TRUE,
                    status = CASE
                        WHEN status = 'PENDING' THEN 'CANCELLED'
                        ELSE status
                    END
                WHERE id = %s
                  AND status IN ('PENDING', 'PROCESSING')
                """,
                (request_id,),
            )
            changed = cursor.rowcount == 1
            if changed:
                cursor.execute(
                    """
                    INSERT INTO request_events (request_id, event_type, detail)
                    VALUES (%s, 'CANCELLATION_REQUESTED', 'Cancelacion solicitada')
                    """,
                    (request_id,),
                )
            connection.commit()
            return changed
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def is_cancel_requested(self, request_id: str) -> bool:
        """Falla de forma segura: un error de BD se propaga al worker."""
        request = self.get_request(request_id)
        if request is None:
            return True
        return request.cancel_requested or request.status is RequestStatus.CANCELLED

    def mark_cancelled(self, request_id: str) -> None:
        self._change_status(
            request_id,
            RequestStatus.CANCELLED,
            "REQUEST_CANCELLED",
            "Solicitud cancelada antes de confirmar",
        )

    def mark_completed(
        self,
        request_id: str,
        slot: SelectedSlot,
        confirmation_code: str,
    ) -> None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            connection.start_transaction()
            cursor.execute(
                """
                UPDATE appointment_requests
                SET status = 'COMPLETED', selected_date = %s,
                    selected_time = %s, confirmation_code = %s,
                    last_error = NULL
                WHERE id = %s AND status = 'PROCESSING'
                """,
                (
                    slot.appointment_date,
                    slot.appointment_time,
                    confirmation_code,
                    request_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Transicion de estado invalida al completar.")
            cursor.execute(
                """
                INSERT INTO request_events (request_id, event_type, detail)
                VALUES (%s, 'REQUEST_COMPLETED', 'Confirmacion local completada')
                """,
                (request_id,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def retry_or_fail(self, request_id: str, attempts: int, max_attempts: int) -> None:
        status = (
            RequestStatus.PENDING if attempts < max_attempts else RequestStatus.FAILED
        )
        event = (
            "RETRY_SCHEDULED" if status is RequestStatus.PENDING else "REQUEST_FAILED"
        )
        self._change_status(
            request_id,
            status,
            event,
            "No se encontro disponibilidad en el entorno simulado",
        )

    def mark_error(
        self,
        request_id: str,
        attempts: int,
        max_attempts: int,
        public_error: str,
    ) -> None:
        status = (
            RequestStatus.PENDING if attempts < max_attempts else RequestStatus.FAILED
        )
        self._change_status(request_id, status, "PROCESSING_ERROR", public_error[:255])

    def add_event(self, request_id: str, event_type: str, detail: str) -> None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO request_events (request_id, event_type, detail)
                VALUES (%s, %s, %s)
                """,
                (request_id, event_type[:40], detail[:255]),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _change_status(
        self,
        request_id: str,
        status: RequestStatus,
        event_type: str,
        detail: str,
    ) -> None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            connection.start_transaction()
            cursor.execute(
                """
                UPDATE appointment_requests
                SET status = %s, last_error = %s
                WHERE id = %s
                  AND status IN ('PENDING', 'PROCESSING')
                """,
                (
                    status.value,
                    detail if status is RequestStatus.FAILED else None,
                    request_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Transicion de estado invalida.")
            cursor.execute(
                """
                INSERT INTO request_events (request_id, event_type, detail)
                VALUES (%s, %s, %s)
                """,
                (request_id, event_type, detail),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
