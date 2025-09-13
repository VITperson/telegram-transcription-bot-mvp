from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.payments.webhooks import router as payments_router
from src.bot.main import start_bot_polling, stop_bot_polling


settings = get_settings()
configure_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_task = asyncio.create_task(start_bot_polling())
    try:
        yield
    finally:
        await stop_bot_polling()
        bot_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bot_task


app = FastAPI(title="Transcription Bot API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(payments_router, prefix="/payments", tags=["payments"])

