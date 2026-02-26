from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from content import (
    SPECIAL_MESSAGES_BY_SLOT,
    determine_special_slot,
    generate_daily_message,
)

START_DATE = date(2025, 12, 29)
TOTAL_DAYS = 365
TIMEZONE = ZoneInfo("Asia/Qostanay")


def load_settings() -> tuple[str, str]:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    chat_id = os.getenv("CHAT_ID", "").strip()

    if not token:
        print("Error: BOT_TOKEN is missing. Set it in .env or GitHub Secrets.", file=sys.stderr)
        sys.exit(1)
    if not chat_id:
        print("Error: CHAT_ID is missing. Set it in .env or GitHub Secrets.", file=sys.stderr)
        sys.exit(1)

    return token, chat_id


def compute_day_index(local_date: date) -> int:
    return (local_date - START_DATE).days + 1


def pick_message(now: datetime) -> str:
    local_date = now.date()

    if local_date < START_DATE:
        print(
            f"Marathon has not started yet (today={local_date}, start={START_DATE}). Skipping send.",
        )
        sys.exit(0)

    last_day = START_DATE + timedelta(days=TOTAL_DAYS - 1)
    if local_date > last_day:
        print(
            f"Marathon finished on {last_day}. Disable the workflow to stop scheduled runs.",
        )
        sys.exit(0)

    if local_date == START_DATE:
        slot = determine_special_slot(now.time())
        return SPECIAL_MESSAGES_BY_SLOT[slot]

    day_index = compute_day_index(local_date)
    return generate_daily_message(day_index)


def send_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        print(f"Network or HTTP error: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        print("Telegram response is not valid JSON.", file=sys.stderr)
        sys.exit(1)

    if not data.get("ok"):
        description = data.get("description", "unknown error")
        print(f"Telegram API error: {description}", file=sys.stderr)
        sys.exit(1)

    print("sent ok")

def get_test_now(tz: ZoneInfo) -> datetime | None:
    """
    Optional test override via env:
      TEST_DATE=YYYY-MM-DD
      TEST_HOUR=0..23
    If only TEST_DATE is set, hour defaults to 10.
    If only TEST_HOUR is set, date defaults to today's local date.
    """
    test_date_raw = os.getenv("TEST_DATE", "").strip()
    test_hour_raw = os.getenv("TEST_HOUR", "").strip()

    if not test_date_raw and not test_hour_raw:
        return None

    # Base date
    if test_date_raw:
        try:
            d = date.fromisoformat(test_date_raw)
        except ValueError:
            print("Error: TEST_DATE must be in YYYY-MM-DD format.", file=sys.stderr)
            sys.exit(1)
    else:
        d = datetime.now(tz).date()

    # Base hour
    if test_hour_raw:
        try:
            h = int(test_hour_raw)
        except ValueError:
            print("Error: TEST_HOUR must be an integer 0..23.", file=sys.stderr)
            sys.exit(1)
        if not (0 <= h <= 23):
            print("Error: TEST_HOUR must be in range 0..23.", file=sys.stderr)
            sys.exit(1)
    else:
        h = 10

    return datetime(d.year, d.month, d.day, h, 0, 0, tzinfo=tz)



def main() -> None:
    token, chat_id = load_settings()
    test_now = get_test_now(TIMEZONE)
    now = test_now or datetime.now(TIMEZONE)
    message = pick_message(now)
    send_message(token, chat_id, message)


if __name__ == "__main__":
    main()