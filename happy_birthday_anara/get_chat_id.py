from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv


def load_token() -> str:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("Error: BOT_TOKEN is missing. Set it in .env before running this script.", file=sys.stderr)
        sys.exit(1)
    return token


def tg_get_updates(
    token: str,
    offset: Optional[int] = None,
    timeout: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params: Dict[str, Any] = {"timeout": timeout, "limit": limit}
    if offset is not None:
        params["offset"] = offset

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
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

    return data


def extract_chat_objects_from_update(update: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """
    Достаём chat-объекты из разных типов апдейтов.
    Telegram может прислать chat в разных местах:
      - message.chat
      - edited_message.chat
      - channel_post.chat
      - edited_channel_post.chat
      - my_chat_member.chat (важно для добавления/удаления бота)
      - chat_member.chat
      - callback_query.message.chat
      - message_reaction.chat (если доступно)
    """
    candidates: List[Optional[Dict[str, Any]]] = []

    def safe_get(path: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
        cur: Any = update
        for key in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
        return cur if isinstance(cur, dict) else None

    # основные
    candidates.append(safe_get(("message", "chat")))
    candidates.append(safe_get(("edited_message", "chat")))
    candidates.append(safe_get(("channel_post", "chat")))
    candidates.append(safe_get(("edited_channel_post", "chat")))

    # события членства (очень полезно для групп/каналов)
    candidates.append(safe_get(("my_chat_member", "chat")))
    candidates.append(safe_get(("chat_member", "chat")))

    # callback query
    candidates.append(safe_get(("callback_query", "message", "chat")))

    # message_reaction / message_reaction_count (не у всех ботов включено)
    candidates.append(safe_get(("message_reaction", "chat")))
    candidates.append(safe_get(("message_reaction_count", "chat")))

    for c in candidates:
        if c:
            yield c


def chat_display_name(chat: Dict[str, Any]) -> str:
    # title - для групп/каналов, username - для публичных, first_name - для приватных
    return (
        (chat.get("title") or "").strip()
        or (chat.get("username") or "").strip()
        or (chat.get("first_name") or "").strip()
        or "unknown"
    )


def list_unique_chats_from_updates(token: str, print_raw: bool = False) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    data = tg_get_updates(token=token, offset=None, timeout=0, limit=100)

    updates = data.get("result") or []
    if not updates:
        return [], None

    seen_ids: Set[int] = set()
    chats: List[Dict[str, Any]] = []

    max_update_id: Optional[int] = None

    for upd in updates:
        if isinstance(upd, dict):
            upd_id = upd.get("update_id")
            if isinstance(upd_id, int):
                max_update_id = upd_id if max_update_id is None else max(max_update_id, upd_id)

            for chat in extract_chat_objects_from_update(upd):
                chat_id = chat.get("id")
                if isinstance(chat_id, int) and chat_id not in seen_ids:
                    seen_ids.add(chat_id)
                    chats.append(chat)

    # стабильная сортировка: сначала по типу, затем по id
    chats.sort(key=lambda c: (str(c.get("type", "")), int(c.get("id", 0))))

    if print_raw:
        print("RAW UPDATES COUNT:", len(updates))

    return chats, max_update_id


def print_chats(chats: List[Dict[str, Any]]) -> None:
    if not chats:
        print("No chats found in updates yet.")
        print("Tip: write /start to the bot in private chat and send any message in groups/channels,")
        print("so Telegram generates updates for those chats.")
        return

    print(f"Found {len(chats)} unique chat(s) in updates:\n")
    for chat in chats:
        cid = chat.get("id")
        ctype = chat.get("type", "unknown")
        name = chat_display_name(chat)
        username = chat.get("username")
        extra = f"@{username}" if username else ""
        print(f"- CHAT_ID={cid} | type={ctype} | name={name} {extra}".rstrip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List unique Telegram chats visible via getUpdates (not truly all chats bot is in).",
    )
    parser.add_argument(
        "--manual",
        metavar="CHAT_ID",
        help="Skip API call and just echo the provided chat id.",
    )
    parser.add_argument(
        "--mark-read",
        action="store_true",
        help="After listing chats, mark updates as read (sets offset to last_update_id+1).",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print extra debug info.",
    )
    args = parser.parse_args()

    if args.manual:
        print(f"CHAT_ID={args.manual}")
        sys.exit(0)

    token = load_token()
    chats, max_update_id = list_unique_chats_from_updates(token=token, print_raw=args.raw)
    print_chats(chats)

    if args.mark_read and max_update_id is not None:
        # чтобы “съесть” апдейты, делаем getUpdates с offset = max_update_id + 1
        _ = tg_get_updates(token=token, offset=max_update_id + 1, timeout=0, limit=1)
        print(f"\nMarked updates as read. Next offset: {max_update_id + 1}")


if __name__ == "__main__":
    main()
