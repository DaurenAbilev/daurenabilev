from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp

from app.config import Settings
from app.models import Credentials, Slot
from app.state import AuthStorage


class BookingAPI:
    def __init__(self, settings: Settings, auth_storage: AuthStorage) -> None:
        self.settings = settings
        self.auth_storage = auth_storage
        self.credentials = auth_storage.load()
        self.auth_token = self.credentials.auth_token if self.credentials else None
        self.session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    def is_authorized(self) -> bool:
        return bool(self.credentials and self.credentials.login and self.credentials.password)

    def headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "AppToken": self.settings.app_token,
            "IYESUrl": self.settings.iyes_url,
        }
        if self.auth_token:
            headers["AuthToken"] = self.auth_token
        return headers

    def cookies(self) -> dict[str, str]:
        cookies = {
            "app-token": self.settings.app_token,
            "iyesurl": self.settings.iyes_url,
            "company": str(self.settings.company_id),
        }
        if self.auth_token:
            cookies["auth-token"] = self.auth_token
        return cookies

    def save_credentials(self, login: str, password: str, auth_token: str | None = None) -> None:
        self.credentials = Credentials(login=login, password=password, auth_token=auth_token)
        self.auth_token = auth_token
        self.auth_storage.save(self.credentials)

    @staticmethod
    def parse_user_date(user_input: str) -> datetime:
        try:
            day, month = map(int, user_input.strip().split("/"))
        except ValueError as exc:
            raise ValueError("Дата должна быть в формате dd/mm") from exc

        now = datetime.now()
        target = datetime(now.year, month, day)
        if target.date() < now.date():
            target = datetime(now.year + 1, month, day)
        return target

    async def authenticate(
        self,
        login: str | None = None,
        password: str | None = None,
        persist: bool = True,
    ) -> str:
        if login and password:
            self.save_credentials(login=login, password=password, auth_token=self.auth_token)

        if not self.credentials or not self.credentials.login or not self.credentials.password:
            raise RuntimeError("Нет сохраненных логина и пароля. Сначала нажми 'Авторизация'.")

        session = await self.get_session()
        url = (
            f"{self.settings.base_url}/api/v1/security/webauthenticate"
            f"?login={self.credentials.login}"
            f"&password={self.credentials.password}"
            f"&companyid={self.settings.company_id}"
            f"&confirmlink={self.settings.base_url}/account-verification/"
        )

        async with session.get(url, headers=self.headers(), cookies=self.cookies()) as response:
            text = await response.text()
            if response.status != 200:
                raise RuntimeError(f"Auth failed: {response.status} | {text}")

            try:
                data = await response.json(content_type=None)
            except Exception:
                data = {}

        token = None
        for key in ("AuthToken", "authToken", "auth-token", "token", "Token"):
            if data.get(key):
                token = data[key]
                break

        if not token:
            for cookie in session.cookie_jar:
                if cookie.key.lower() == "auth-token":
                    token = cookie.value
                    break

        if not token:
            raise RuntimeError(f"Не удалось получить AuthToken. Ответ: {text}")

        self.auth_token = token
        if persist and self.credentials:
            self.save_credentials(self.credentials.login, self.credentials.password, token)
        return token

    async def ensure_auth(self) -> None:
        if not self.auth_token:
            await self.authenticate()

    async def list_slots(self, date_str: str) -> list[Slot]:
        await self.ensure_auth()
        session = await self.get_session()

        target_date = self.parse_user_date(date_str)
        start_date = target_date.strftime("%Y-%m-%dT00:00:00")
        end_date = target_date.strftime("%Y-%m-%dT00:00:00")
        time_start = target_date.strftime("%Y-%m-%dT06:00:00")
        time_end = target_date.strftime("%Y-%m-%dT23:00:00")

        payload = {
            "CompanyID": self.settings.company_id,
            "Types": [],
            "StartDate": start_date,
            "EndDate": end_date,
            "TimeStart": time_start,
            "TimeEnd": time_end,
        }
        headers = self.headers()
        headers["Content-Type"] = "application/json"

        url = f"{self.settings.base_url}/api/v1/webbooking/listwithmine"
        async with session.post(url, json=payload, headers=headers, cookies=self.cookies()) as response:
            text = await response.text()

            if response.status == 401:
                self.auth_token = None
                await self.authenticate()
                return await self.list_slots(date_str)

            if response.status != 200:
                raise RuntimeError(f"listwithmine failed: {response.status} | {text}")

            data = await response.json(content_type=None)

        items = data.get("Items", [])
        slots = [
            Slot.from_api(item)
            for item in items
            if item.get("ServiceDescription") == self.settings.target_service
            and item.get("AvailablePlaces", 0) > 0
        ]
        return sorted(slots, key=lambda slot: slot.start_time)

    async def book_slot(self, slot: Slot) -> dict[str, Any]:
        await self.ensure_auth()
        session = await self.get_session()

        date_part = slot.date_lesson.split("T")[0]
        start_dt = f"{date_part}T{slot.start_time.split('T')[1]}"
        end_dt = f"{date_part}T{slot.end_time.split('T')[1]}"

        payload = {
            "Note": "",
            "BookNr": 1,
            "BookingID": slot.id_servizio,
            "StartTime": start_dt,
            "EndTime": end_dt,
            "IDLesson": slot.id_lesson,
            "Type": slot.type_,
            "IDDurata": slot.id_durata,
        }
        headers = self.headers()
        headers["Content-Type"] = "application/json"

        url = f"{self.settings.base_url}/api/v1/webbooking/book"
        async with session.post(url, json=payload, headers=headers, cookies=self.cookies()) as response:
            text = await response.text()

            if response.status == 401:
                self.auth_token = None
                await self.authenticate()
                return await self.book_slot(slot)

            try:
                data = await response.json(content_type=None)
            except Exception:
                data = {"raw_text": text}

        return {"status_code": response.status, "data": data, "payload": payload}

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
