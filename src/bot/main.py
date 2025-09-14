from __future__ import annotations

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from src.core.config import get_settings
from src.bot.middlewares.i18n import I18nMiddleware
from src.bot.middlewares.user_registration import UserRegistrationMiddleware
from src.bot.routers.commands import router as commands_router
from src.bot.routers.uploads import router as uploads_router


_bot: Bot | None = None
_dp: Dispatcher | None = None
_polling_started: bool = False
_log = logging.getLogger("bot")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(commands_router)
    dp.include_router(uploads_router)
    dp.message.middleware(I18nMiddleware())
    dp.message.middleware(UserRegistrationMiddleware())
    return dp


async def start_bot_polling() -> None:
    global _bot, _dp, _polling_started
    settings = get_settings()
    _bot = Bot(settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _dp = build_dispatcher()
    _log.info("bot.polling.start")
    try:
        try:
            await _bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            _log.exception("bot.delete_webhook.error")
        _polling_started = True
        await _dp.start_polling(_bot)
    finally:
        _polling_started = False
        _log.info("bot.polling.stop")


async def stop_bot_polling() -> None:
    global _bot, _dp
    if _dp:
        await _dp.storage.close()
    if _bot:
        await _bot.session.close()


def is_polling() -> bool:
    return _polling_started
