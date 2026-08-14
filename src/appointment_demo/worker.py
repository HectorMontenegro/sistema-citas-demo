from __future__ import annotations

import argparse
import logging
import time

from appointment_demo.config import Settings
from appointment_demo.notifier import LoggingNotifier
from appointment_demo.repository import MySQLRequestRepository
from appointment_demo.selenium_adapter import SeleniumDemoPortalFactory
from appointment_demo.service import RequestProcessor


def build_processor(settings: Settings) -> RequestProcessor:
    repository = MySQLRequestRepository(settings)
    portal_factory = SeleniumDemoPortalFactory(
        base_url=settings.demo_portal_base_url,
        access_code=settings.demo_access_code,
        headless=settings.selenium_headless,
    )
    return RequestProcessor(
        repository=repository,
        portal_factory=portal_factory,
        notifier=LoggingNotifier(),
        max_attempts=settings.worker_max_attempts,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker local de demostracion")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Procesa como maximo una solicitud y termina.",
    )
    args = parser.parse_args()

    settings = Settings.from_environment()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger(__name__)
    processor = build_processor(settings)

    while True:
        status = processor.process_one()
        if status is None:
            logger.info("No hay solicitudes pendientes.")
        else:
            logger.info("Ciclo finalizado con estado=%s", status.value)

        if args.once:
            return
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
