#!/usr/bin/env python3
"""
Автозапись на корт (виджет Altegio, Теннисный Центр Даулет).

Стратегия: по каждому корту спрашиваем свободные слоты; если нужный есть —
сразу бронируем. Первый успех — выход. Никто не подошёл — пауза и новый круг.

Запуск:
  python daulet_tennis_reservation.py --date 2026-08-12 --time 19:00 --dry-run
  python daulet_tennis_reservation.py --date 2026-08-12 --time 19:00 --start-at 2026-08-12T10:00
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

# ─────────────────────────── 1. CONFIG ───────────────────────────

BASE = "https://tennisdaulet.altegio.me/api/v1"
TZ = ZoneInfo("Asia/Almaty")           # центр в Астане, UTC+5

LOCATION_ID = 521176                    # id компании — он же в URL book_record
SERVICE_ID = 7849893                    # "Аренда открытого корта (1 час)"
BOOKFORM_ID = 551098
TOKEN = "gtcwf654agufy25gsadh"           # публичный токен виджета, одинаков для всех

# Порядок = приоритет: первым идёт корт, который хочется больше.
# Проверяются все — корт без свободных слотов просто вернёт пустой data.

COURTS: list[dict] = [
    {"id": 1521565, "name": "Корт №3"},
    {"id": 1521564, "name": "Корт №2"}, 
    {"id": 1521562, "name": "Корт ? (уточни)"},
    {"id": 1521566, "name": "Корт ? (уточни)"},
    {"id": 1521567, "name": "Корт ? (уточни)"},
]

CLIENT_INFO = {
    "fullname": "Даурен",
    "surname": None,
    "patronymic": None,
    "phone": "77478365145",
    "email": "daurenabilev2022@gmail.com",
}

RECORDS_LOG = Path("records.jsonl")     # сюда пишем всё созданное — иначе не отменить

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ru-RU",
    "authorization": f"Bearer {TOKEN}",
    "content-type": "application/json",
    "origin": "https://tennisdaulet.altegio.me",
    "referer": f"https://tennisdaulet.altegio.me/company/{LOCATION_ID}/create-record/record",
    "x-altegio-application-name": "client.booking",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}
# Намеренно НЕ отправляем: x-app-signature, x-app-client-context, cf_clearance.
# Тесты показали, что сервер их не проверяет. Если посыплются 401/403 —
# верни их сюда, скопировав свежие значения из DevTools.

log = logging.getLogger("booker")


# ─────────────────────────── 2. API ───────────────────────────

def make_client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=10.0)


def search_timeslots(client: httpx.Client, staff_id: int,
                     date: str | None = None) -> set[str]:
    """
    Свободные слоты по ОДНОМУ корту.

    Ключевой момент: форма ответа зависит от запроса.
      - staff_id указан  -> booking_search_result_timeslots (времена)
      - staff_id не указан -> booking_search_result_staff (список кортов)
    Нам нужен первый вариант, поэтому шлём строго один корт за раз.

    Возвращает множество строк вида "2026-08-12T19:00:00" (без смещения,
    чтобы напрямую сравнивать с тем, что уходит в book()).
    """
    payload = {
        "context": {"location_id": LOCATION_ID},
        "filter": {
            "date": date,
            "records": [{
                "staff_id": staff_id,
                "attendance_service_items": [{"type": "service", "id": SERVICE_ID}],
            }],
        },
    }
    r = client.post(f"{BASE}/booking/search/timeslots", json=payload)
    r.raise_for_status()

    slots = set()
    for item in r.json().get("data", []):
        attrs = item.get("attributes", {})
        if not attrs.get("is_bookable"):
            continue
        dt = attrs.get("datetime", "")
        if dt:
            slots.add(dt[:19])          # "2026-08-05T06:00:00+05:00" -> "2026-08-05T06:00:00"
    return slots


def book(client: httpx.Client, staff_id: int, dt: str, comment: str = "") -> dict:
    """Создаёт запись. dt — локальное время центра, 'YYYY-MM-DDTHH:MM:SS'."""
    body = {
        **CLIENT_INFO,
        "comment": comment,
        "custom_fields": {},
        "is_newsletter_allowed": None,
        "is_personal_data_processing_allowed": None,
        "appointments": [{
            "services": [SERVICE_ID],
            "staff_id": staff_id,
            "datetime": dt,
            "chargeStatus": "",
            "custom_fields": {},
            "id": 0,                     # локальный индекс, не серверный id
            "available_staff_ids": [staff_id],
        }],
        "bookform_id": BOOKFORM_ID,
        "isMobile": False,
        "notify_by_sms": 3,
        "referrer": "https://taplink.cc/daulet.tennis.centre",
        "is_charge_required_priority": True,
        "is_support_charge": False,
        "pay_by_abonement": False,
        "appointments_charges": [{"id": 0, "services": [], "prepaid": []}],
        "redirect_url": (
            f"https://tennisdaulet.altegio.me/company/{LOCATION_ID}"
            "/success-order/{recordId}/{recordHash}"
        ),
    }
    r = client.post(f"{BASE}/book_record/{LOCATION_ID}", json=body)
    r.raise_for_status()
    return r.json()[0]


def remember(result: dict) -> None:
    """Пишем record_id и record_hash — без них запись потом не отменить."""
    entry = {
        "record_id": result["record_id"],
        "record_hash": result["record_hash"],
        "datetime": result["record"]["datetime"],
        "staff": result["record"]["staff"]["name"],
        "saved_at": datetime.now(TZ).isoformat(),
    }
    with RECORDS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info("Сохранил в %s: %s", RECORDS_LOG, entry)


# ─────────────────────────── 3. СЦЕНАРИЙ ───────────────────────────

def wait_until(moment: datetime) -> None:
    """Спит до момента X. Последние секунды досыпает мелкими шагами."""
    while True:
        left = (moment - datetime.now(TZ)).total_seconds()
        if left <= 0:
            return
        if left > 60:
            log.info("До старта %.0f с", left)
        time.sleep(min(left, 30) if left > 2 else 0.05)


def hunt(client: httpx.Client, target: str, courts: list[dict],
         poll_interval: float, deadline_sec: float, dry_run: bool) -> bool:
    """
    Круг за кругом обходит корты: спрашивает свободные слоты и,
    как только целевой находится, сразу его занимает.
    """
    started = time.monotonic()
    lap = 0

    while time.monotonic() - started < deadline_sec:
        lap += 1
        for court in courts:
            label = f"{court['name']} ({court['id']})"

            try:
                slots = search_timeslots(client, court["id"], target[:10])
            except httpx.HTTPError as e:
                log.warning("%s: не удалось получить слоты — %s", label, e)
                continue

            if lap == 1:
                log.info("%s: свободно %s — %s", label, len(slots),
                         ", ".join(sorted(t[11:16] for t in slots)) or "ничего")

            if target not in slots:
                log.debug("%s: %s недоступен", label, target)
                continue

            log.info("%s: слот %s свободен", label, target)
            if dry_run:
                log.info("DRY-RUN: бронь не отправлена")
                return True

            try:
                result = book(client, court["id"], target)
            except httpx.HTTPStatusError as e:
                # Тело ответа логируем целиком: так узнаем, как выглядит отказ,
                # если слот увели в те ~200 мс между проверкой и бронью.
                log.warning("%s: отказ %s — %s",
                            label, e.response.status_code, e.response.text[:500])
                continue
            except httpx.HTTPError as e:
                log.warning("%s: сетевая ошибка при броне — %s", label, e)
                continue

            log.info("УСПЕХ: %s, запись %s", label, result["record_id"])
            remember(result)
            return True

        log.info("Круг %s: слот %s недоступен, ждём %.1f с", lap, target, poll_interval)
        time.sleep(poll_interval)

    log.error("Дедлайн истёк, слот %s взять не удалось", target)
    return False

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="YYYY-MM-DD — дата игры")
    p.add_argument("--time", required=True, help="HH:MM — время игры")
    p.add_argument("--courts", help="staff_id через запятую, в порядке приоритета")
    p.add_argument("--start-at", help="YYYY-MM-DDTHH:MM — когда начать охоту")
    p.add_argument("--poll", type=float, default=2.0, help="пауза между кругами, с")
    p.add_argument("--deadline", type=float, default=300, help="сколько секунд охотиться")
    p.add_argument("--dry-run", action="store_true", help="искать, но не бронировать")
    p.add_argument("-v", "--verbose", action="store_true", help="показывать занятые слоты")
    args = p.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    target = f"{args.date}T{args.time}:00"

    if args.courts:
        by_id = {c["id"]: c for c in COURTS}
        courts = [by_id.get(i, {"id": i, "name": "?"})
                  for i in (int(x) for x in args.courts.split(","))]
    else:
        courts = COURTS

    log.info("Цель: %s. Корты: %s", target, ", ".join(c["name"] for c in courts))

    if args.start_at:
        wait_until(datetime.fromisoformat(args.start_at).replace(tzinfo=TZ))

    with make_client() as client:
        ok = hunt(client, target, courts, args.poll, args.deadline, args.dry_run)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())