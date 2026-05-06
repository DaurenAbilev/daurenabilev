from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.models import Slot


def main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Авторизация")
    keyboard.button(text="Показать слоты")
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)


def slots_keyboard(slots: list[Slot]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for index, slot in enumerate(slots):
        text = f"{slot.start_label}-{slot.end_label} | мест: {slot.available_places}"
        keyboard.button(text=text, callback_data=f"bookslot:{index}")
    keyboard.adjust(1)
    return keyboard.as_markup()
