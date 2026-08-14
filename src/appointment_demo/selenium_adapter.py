from __future__ import annotations

import logging
from datetime import date, time
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from appointment_demo.config import LOCAL_DEMO_HOSTS, ensure_local_demo_url
from appointment_demo.domain import AppointmentRequest, Confirmation, SelectedSlot


class SeleniumDemoPortalFactory:
    def __init__(
        self,
        base_url: str,
        access_code: str,
        headless: bool = True,
    ) -> None:
        self._base_url = ensure_local_demo_url(base_url)
        self._access_code = access_code
        self._headless = headless

    def open(self, request: AppointmentRequest) -> SeleniumDemoPortalSession:
        return SeleniumDemoPortalSession(
            base_url=self._base_url,
            access_code=self._access_code,
            request=request,
            headless=self._headless,
        )


class SeleniumDemoPortalSession:
    def __init__(
        self,
        base_url: str,
        access_code: str,
        request: AppointmentRequest,
        headless: bool,
    ) -> None:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--disable-dev-shm-usage")

        self._base_url = ensure_local_demo_url(base_url)
        self._driver = webdriver.Chrome(options=options)
        self._wait = WebDriverWait(self._driver, 10)
        try:
            self._driver.get(f"{self._base_url}/login")
            self._assert_local_navigation()

            request_field = self._wait.until(
                EC.presence_of_element_located((By.ID, "request_id"))
            )
            request_field.send_keys(request.id)

            code_field = self._driver.find_element(By.ID, "access_code")
            code_field.send_keys(access_code)
            self._driver.find_element(By.ID, "accept_demo_terms").click()
            self._driver.find_element(By.ID, "login_submit").click()

            self._wait.until(
                EC.presence_of_element_located((By.ID, "appointment_form"))
            )
            self._assert_local_navigation()
        except Exception:
            self.close()
            raise

    def _assert_local_navigation(self) -> None:
        parsed = urlparse(self._driver.current_url)
        if parsed.scheme != "http" or parsed.hostname not in LOCAL_DEMO_HOSTS:
            self.close()
            raise RuntimeError("Selenium intento abandonar el entorno local.")

    def find_slot(self, request: AppointmentRequest) -> SelectedSlot | None:
        buttons = self._driver.find_elements(By.CSS_SELECTOR, "[data-slot-date]")
        selected_date: date | None = None

        for button in buttons:
            candidate = date.fromisoformat(button.get_attribute("data-slot-date"))
            if request.preferred_from <= candidate <= request.preferred_to:
                button.click()
                selected_date = candidate
                break

        if selected_date is None:
            return None

        time_select = Select(self._driver.find_element(By.ID, "slot_time"))
        valid_options = [
            option
            for option in time_select.options
            if option.get_attribute("value").strip()
        ]
        if not valid_options:
            return None

        selected_time = time.fromisoformat(valid_options[0].get_attribute("value"))
        time_select.select_by_value(selected_time.strftime("%H:%M"))
        return SelectedSlot(selected_date, selected_time)

    def confirm(self, slot: SelectedSlot) -> Confirmation:
        self._assert_local_navigation()
        self._driver.find_element(By.ID, "confirm_appointment").click()
        code_element = self._wait.until(
            EC.presence_of_element_located((By.ID, "confirmation_code"))
        )
        self._assert_local_navigation()

        confirmed_date = date.fromisoformat(
            self._driver.find_element(By.ID, "confirmed_date").text.strip()
        )
        confirmed_time = time.fromisoformat(
            self._driver.find_element(By.ID, "confirmed_time").text.strip()
        )
        if (
            confirmed_date != slot.appointment_date
            or confirmed_time != slot.appointment_time
        ):
            raise RuntimeError(
                "El portal simulado devolvio un resultado inconsistente."
            )

        code = code_element.text.strip()
        if not code:
            raise RuntimeError("El portal simulado no genero confirmacion.")
        return Confirmation(code=code)

    def close(self) -> None:
        try:
            self._driver.quit()
        except Exception:
            logging.getLogger(__name__).debug(
                "El navegador ya estaba cerrado.",
                exc_info=True,
            )
