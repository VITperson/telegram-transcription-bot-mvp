from __future__ import annotations

import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from src.tasks.tasks import enqueue_transcription_job


router = Router()

# Accept standard, youtu.be, and shorts URLs (single videos only)
YOUTUBE_RE = re.compile(r"https?://(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[A-Za-z0-9_\-]+")


def language_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for code, label in [("auto", "Auto"), ("en", "English"), ("ru", "Русский")]:
        kb.button(text=label, callback_data=f"lang:{code}")
    kb.adjust(3)
    return kb


def mode_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for code, label in [("full", "Full"), ("summary", "Summary"), ("keypoints", "Key points")]:
        kb.button(text=label, callback_data=f"mode:{code}")
    kb.adjust(3)
    return kb


@router.message(F.text.regexp(YOUTUBE_RE))
async def on_youtube_link(m: Message, state: FSMContext):
    text = m.text or ""
    # Simple playlist detection
    if "list=" in text:
        await m.answer("Playlists are not supported yet. Please send a single video link.")
        return
    await state.update_data(pending_source={"type": "youtube", "link": text})
    await m.answer("Choose language:", reply_markup=language_keyboard().as_markup())


@router.message(F.voice | F.audio | F.video)
async def on_media(m: Message, state: FSMContext):
    src_type = "voice" if m.voice else ("audio" if m.audio else "video")
    await state.update_data(pending_source={"type": src_type, "file_id": (m.voice or m.audio or m.video).file_id})
    await m.answer("Choose language:", reply_markup=language_keyboard().as_markup())


@router.callback_query(F.data.startswith("lang:"))
async def on_language(cq: CallbackQuery, state: FSMContext):
    lang = cq.data.split(":", 1)[1]
    await state.update_data(chosen_language=lang)
    await cq.answer()
    await cq.message.edit_text("Choose mode:", reply_markup=mode_keyboard().as_markup())


@router.callback_query(F.data.startswith("mode:"))
async def on_mode(cq: CallbackQuery, state: FSMContext):
    mode = cq.data.split(":", 1)[1]
    ctx = await state.get_data()
    src = ctx.get("pending_source")
    if not src:
        await cq.answer("No source found. Please resend.", show_alert=True)
        return
    language = ctx.get("chosen_language", "auto")
    await cq.answer()
    await cq.message.edit_text("Queued. We will notify when ready.")
    await enqueue_transcription_job(
        user_id=cq.from_user.id,
        source=src,
        language=language,
        mode=mode,
    )
