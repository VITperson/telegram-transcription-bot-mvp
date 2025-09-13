# Telegram Transcription Bot (MVP)

Production-ready MVP for a Telegram transcription bot with FastAPI, aiogram 3, Celery, Redis, MySQL, and Django Admin. Transcribes voice/audio/video and single YouTube links via faster-whisper (CTranslate2). Includes summary/key points modes, i18n, minimal monetization via promo codes and dummy payment provider, and export to TXT/Markdown.

## Quick Start

1) Copy environment and fill keys

```
cp .env.example .env
```

2) Build and start services

```
docker compose up -d --build
```

3) Run DB migrations

```
docker compose exec bot_api alembic upgrade head
```

4) Create Django superuser

```
docker compose exec admin python manage.py createsuperuser
```

5) Test the bot

- Send a Telegram voice note, audio (mp3/wav/m4a), video (mp4), or a single YouTube video link to the bot.

## Services

- bot_api: FastAPI (webhooks, payments) + aiogram bot polling
- worker: Celery worker for download/normalize/transcribe/summarize/exports
- admin: Django Admin for users, jobs, plans, promo codes, payments, exports
- redis: broker and rate-limit store
- mysql: primary DB (switchable to Postgres via ENV)

## Tech

- Bot: aiogram 3.x
- API: FastAPI
- Queue: Celery + Redis
- Media: ffmpeg, yt-dlp
- STT: faster-whisper (CTranslate2)
- Summarization: provider abstraction (default OpenAI)
- DB: MySQL via SQLAlchemy 2.0 + Alembic (ENV switch for Postgres)
- Admin: Django 5.x
- Logging: structlog JSON
- Tests: pytest

## Notes

- Stores text, timestamps, metadata only. Temp media deleted.
- Free tier caps; promo codes add minutes; no real payments (dummy provider + HMAC).
- i18n with en/ru JSON. Basic per-user rate limiting.

