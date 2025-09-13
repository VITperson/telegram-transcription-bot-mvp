from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Awaitable, Any, Dict
from src.services.i18n.loader import I18n


class I18nMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.i18n = I18n()

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        if isinstance(event, Message):
            lang = event.from_user.language_code or "en"  # naive default
            data["_"] = self.i18n.get_translator(lang)
        return await handler(event, data)

