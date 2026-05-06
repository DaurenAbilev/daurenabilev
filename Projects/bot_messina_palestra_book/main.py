from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from app.api_client import BookingAPI
from app.config import settings
from app.handlers import build_router
from app.state import AuthStorage, UserStateStore


async def main() -> None:
    settings.validate()

    auth_storage = AuthStorage(
        path=settings.auth_file,
        default_login=settings.default_login,
        default_password=settings.default_password,
    )
    api = BookingAPI(settings=settings, auth_storage=auth_storage)
    state_store = UserStateStore()

    bot = Bot(settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(api=api, state_store=state_store))

    try:
        await dispatcher.start_polling(bot)
    finally:
        await api.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
