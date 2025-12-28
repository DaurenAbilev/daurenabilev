from __future__ import annotations

import argparse
import os
import sys

import requests
from dotenv import load_dotenv


def load_token() -> str:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("Error: BOT_TOKEN is missing. Set it in .env before running this script.", file=sys.stderr)
        sys.exit(1)
    return token


def fetch_chat_id(token: str) -> None:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        response = requests.get(url, timeout=15)
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

    updates = data.get("result") or []
    if not updates:
        print("No updates yet. Send /start to the bot from the target chat and run again.")
        sys.exit(0)

    latest = updates[-1]
    chat = (latest.get("message") or {}).get("chat") or {}
    chat_id = chat.get("id")
    title = chat.get("title") or chat.get("username") or chat.get("first_name") or "unknown"

    if chat_id is None:
        print("Could not find chat id in the latest update.", file=sys.stderr)
        sys.exit(1)

    print(f"CHAT_ID={chat_id}")
    print(f"Chat title/username: {title}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get Telegram chat id via getUpdates or print a provided one.",
    )
    parser.add_argument(
        "--manual",
        metavar="CHAT_ID",
        help="Skip API call and just echo the provided chat id.",
    )
    args = parser.parse_args()

    if args.manual:
        print(f"CHAT_ID={args.manual}")
        sys.exit(0)

    token = load_token()
    fetch_chat_id(token)


if __name__ == "__main__":
    main()
