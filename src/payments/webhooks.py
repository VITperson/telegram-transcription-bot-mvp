from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Header, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from src.db.session import get_session
from src.db.models import Payment
from .providers.dummy import DummyProvider


router = APIRouter()


@router.post("/dummy/callback")
async def dummy_callback(request: Request, x_dummy_signature: str = Header(default="")):
    body = await request.body()
    provider = DummyProvider()
    try:
        payload = provider.parse_webhook({"X-Dummy-Signature": x_dummy_signature}, body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid-signature")

    user_id = payload.get("user_id")
    external_id = payload.get("id")
    amount_cents = int(payload.get("amount_cents", 0))
    async for session in get_session():
        await session.execute(
            insert(Payment).values(
                user_id=user_id,
                provider=provider.name,
                external_id=external_id,
                amount_cents=amount_cents,
                currency=payload.get("currency", "USD"),
                status="received",
                raw_payload=payload,
                created_at=dt.datetime.utcnow(),
            )
        )
        await session.commit()
    return {"ok": True}

