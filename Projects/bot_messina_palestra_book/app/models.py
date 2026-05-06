from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Slot:
    id_lesson: int
    id_servizio: int
    id_durata: int
    type_: int
    date_lesson: str
    start_time: str
    end_time: str
    available_places: int
    service_description: str
    category_description: str
    price: float
    raw: dict[str, Any]

    @property
    def date_label(self) -> str:
        return self.date_lesson.split("T")[0]

    @property
    def start_label(self) -> str:
        return self.start_time.split("T")[1][:5]

    @property
    def end_label(self) -> str:
        return self.end_time.split("T")[1][:5]

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> "Slot":
        return cls(
            id_lesson=item["IDLesson"],
            id_servizio=item["IDServizio"],
            id_durata=item.get("IDDurata", 0),
            type_=item.get("Type", 0),
            date_lesson=item["DateLesson"],
            start_time=item["StartTime"],
            end_time=item["EndTime"],
            available_places=item.get("AvailablePlaces", 0),
            service_description=item.get("ServiceDescription", ""),
            category_description=item.get("CategoryDescription", ""),
            price=item.get("Price", 0),
            raw=item,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Credentials:
    login: str
    password: str
    auth_token: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Credentials":
        return cls(
            login=data.get("login", ""),
            password=data.get("password", ""),
            auth_token=data.get("auth_token"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
        return payload
