from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.api_client import BookingAPI
from app.keyboards import main_menu, slots_keyboard
from app.state import UserStateStore


def build_router(api: BookingAPI, state_store: UserStateStore) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def start_cmd(message: Message) -> None:
        await message.answer(
            "Выбери действие:\n"
            "1. Авторизация\n"
            "2. Показать слоты",
            reply_markup=main_menu(),
        )

    @router.message(F.text == "Авторизация")
    async def auth_button(message: Message) -> None:
        if api.is_authorized():
            try:
                await api.authenticate()
                await message.answer("Авторизация подтверждена. Сохраненные данные актуальны.", reply_markup=main_menu())
            except Exception as exc:
                state_store.set(message.from_user.id, mode="waiting_login")
                await message.answer(
                    f"Сохраненная авторизация не подошла: {exc}\nОтправь логин UNIME.",
                    reply_markup=main_menu(),
                )
            return

        state_store.set(message.from_user.id, mode="waiting_login")
        await message.answer("Отправь логин UNIME.")

    @router.message(F.text == "Показать слоты")
    async def ask_date(message: Message) -> None:
        if not api.is_authorized():
            state_store.set(message.from_user.id, mode="waiting_login")
            await message.answer("Сначала нужна авторизация. Отправь логин UNIME.")
            return

        state_store.set(message.from_user.id, mode="waiting_date")
        await message.answer("Введи дату в формате dd/mm. Например: 09/03")

    @router.message(F.text)
    async def text_router(message: Message) -> None:
        user_id = message.from_user.id
        state = state_store.get(user_id)
        mode = state.get("mode")
        text = (message.text or "").strip()

        if mode == "waiting_login":
            state_store.set(user_id, mode="waiting_password", login=text)
            await message.answer("Теперь отправь пароль UNIME.")
            return

        if mode == "waiting_password":
            login = state.get("login", "")
            password = text
            try:
                await api.authenticate(login=login, password=password)
            except Exception as exc:
                state_store.set(user_id, mode="waiting_login")
                await message.answer(f"Ошибка авторизации: {exc}\nОтправь логин заново.")
                return

            state_store.clear(user_id)
            await message.answer("Авторизация успешна. Данные сохранены.", reply_markup=main_menu())
            return

        if mode == "waiting_date":
            try:
                slots = await api.list_slots(text)
            except Exception as exc:
                await message.answer(f"Ошибка получения слотов: {exc}", reply_markup=main_menu())
                return

            if not slots:
                state_store.clear(user_id)
                await message.answer(
                    f"На {text} нет доступных слотов для записи.",
                    reply_markup=main_menu(),
                )
                return

            state_store.set_slots(user_id, text, slots)
            await message.answer(
                f"Доступные слоты на {text}:",
                reply_markup=slots_keyboard(slots),
            )
            return

        await message.answer("Используй кнопки меню.", reply_markup=main_menu())

    @router.callback_query(F.data.startswith("bookslot:"))
    async def slot_selected(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        state = state_store.get(user_id)
        slots = state.get("slots", [])

        if not slots:
            await callback.answer("Список слотов устарел. Запроси заново.", show_alert=True)
            return

        try:
            index = int(callback.data.split(":")[1])
            slot = slots[index]
        except (ValueError, IndexError):
            await callback.answer("Некорректный слот.", show_alert=True)
            return

        if slot.available_places <= 0:
            await callback.answer("На этот слот уже нет мест.", show_alert=True)
            return

        try:
            result = await api.book_slot(slot)
        except Exception as exc:
            await callback.message.answer(f"Ошибка записи: {exc}", reply_markup=main_menu())
            await callback.answer()
            return

        if 200 <= result["status_code"] < 300:
            await callback.message.answer(
                "Запись выполнена.\n"
                f"Дата: {slot.date_label}\n"
                f"Время: {slot.start_label}-{slot.end_label}\n"
                f"Мест было доступно: {slot.available_places}",
                reply_markup=main_menu(),
            )
        else:
            await callback.message.answer(
                "Запись не выполнена.\n"
                f"HTTP: {result['status_code']}\n"
                f"Ответ сервера: {result['data']}",
                reply_markup=main_menu(),
            )

        state_store.clear(user_id)
        await callback.answer()

    return router
