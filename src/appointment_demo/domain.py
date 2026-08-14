from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class AppointmentRequest:
    id: str
    contact_email: str
    preferred_from: date
    preferred_to: date
    status: RequestStatus
    attempts: int
    cancel_requested: bool


@dataclass(frozen=True, slots=True)
class SelectedSlot:
    appointment_date: date
    appointment_time: time


@dataclass(frozen=True, slots=True)
class Confirmation:
    code: str
