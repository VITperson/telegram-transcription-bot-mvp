from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Awaitable, Any, Dict
from sqlalchemy import select
from src.db.session import get_session
from src.db.models import User


class UserRegistrationMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        if isinstance(event, Message) and event.from_user:
            async for session in get_session():
                res = await session.execute(select(User).where(User.id == event.from_user.id))
                user = res.scalar_one_or_none()
                if not user:
                    user = User(
                        id=event.from_user.id,
                        username=event.from_user.username,
                        first_name=event.from_user.first_name,
                        last_name=event.from_user.last_name,
                        locale=event.from_user.language_code or "en",
                    )
                    session.add(user)
                    await session.commit()
        return await handler(event, data)

