from __future__ import annotations

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from src.core.config import get_settings
from src.bot.middlewares.i18n import I18nMiddleware
from src.bot.middlewares.user_registration import UserRegistrationMiddleware
from src.bot.routers.commands import router as commands_router
from src.bot.routers.uploads import router as uploads_router


_bot: Bot | None = None
_dp: Dispatcher | None = None


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(commands_router)
    dp.include_router(uploads_router)
    dp.message.middleware(I18nMiddleware())
    dp.message.middleware(UserRegistrationMiddleware())
    return dp


async def start_bot_polling() -> None:
    global _bot, _dp
    settings = get_settings()
    _bot = Bot(settings.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
    _dp = build_dispatcher()
    await _dp.start_polling(_bot)


async def stop_bot_polling() -> None:
    global _bot, _dp
    if _dp:
        await _dp.storage.close()
    if _bot:
        await _bot.session.close()

