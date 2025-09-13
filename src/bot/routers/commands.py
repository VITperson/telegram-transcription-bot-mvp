from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_session
from src.db.models import User, PromoCode
from src.core.config import get_settings


router = Router()


@router.message(Command("start"))
async def cmd_start(m: Message):
    await m.answer("Welcome! Send a voice/audio/video or a YouTube link to transcribe. Use /help for details.")


@router.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(
        "Send: voice, audio (mp3/wav/m4a), video (mp4), or a single YouTube link.\n"
        "Flow: choose language -> choose mode (Full/Summary/Key points) -> wait for result.\n"
        "Use /balance to see minutes. Use /promo to redeem codes."
    )


@router.message(Command("language"))
async def cmd_language(m: Message):
    await m.answer("Please send media and you will be asked for language before processing.")


@router.message(Command("balance"))
async def cmd_balance(m: Message):
    # minimal balance display; registration middleware ensures user exists
    await m.answer("Your minute balance will be used per job (rounded up). Free tier caps apply.")


@router.message(Command("history"))
async def cmd_history(m: Message):
    await m.answer("History coming soon: you'll see past jobs with pagination.")


@router.message(Command("promo"))
async def cmd_promo(m: Message):
    await m.answer("Send a promo code as a message: PROMO: YOURCODE")


@router.message(F.text.startswith("PROMO:"))
async def handle_promo(m: Message):
    code = (m.text or "").split(":", 1)[1].strip()
    if not code:
        await m.answer("Please provide a promo code after PROMO: ...")
        return
    # In a real flow, validate via DB
    await m.answer(f"Promo code received: {code}. We will validate and add minutes if valid.")

