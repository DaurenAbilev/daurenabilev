from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import Credentials, Slot


class AuthStorage:
    def __init__(self, path: Path, default_login: str = "", default_password: str = "") -> None:
        self.path = path
        self.default_login = default_login
        self.default_password = default_password

    def load(self) -> Credentials | None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            credentials = Credentials.from_dict(data)
            if credentials.login and credentials.password:
                return credentials

        if self.default_login and self.default_password:
            return Credentials(login=self.default_login, password=self.default_password)
        return None

    def save(self, credentials: Credentials) -> None:
        self.path.write_text(
            json.dumps(credentials.to_dict(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )


class UserStateStore:
    def __init__(self) -> None:
        self._state: dict[int, dict[str, Any]] = {}

    def get(self, user_id: int) -> dict[str, Any]:
        return self._state.get(user_id, {})

    def set(self, user_id: int, **values: Any) -> None:
        self._state[user_id] = values

    def patch(self, user_id: int, **values: Any) -> None:
        state = self.get(user_id).copy()
        state.update(values)
        self._state[user_id] = state

    def clear(self, user_id: int) -> None:
        self._state[user_id] = {}

    def set_slots(self, user_id: int, date_str: str, slots: list[Slot]) -> None:
        self._state[user_id] = {
            "mode": "slots_loaded",
            "date": date_str,
            "slots": slots,
        }
