import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5, ban_threshold: int = 20):
        self.rate_limit = rate_limit
        self.ban_threshold = ban_threshold
        self._last_action: dict[int, float] = defaultdict(float)
        self._spam_count: dict[int, int] = defaultdict(int)
        self._blocked: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        uid = user.id
        now = time.time()

        if uid in self._blocked:
            if now - self._blocked[uid] < 60:
                return None
            del self._blocked[uid]
            self._spam_count[uid] = 0

        last = self._last_action.get(uid, 0)
        if now - last < self.rate_limit:
            self._spam_count[uid] += 1
            if self._spam_count[uid] >= self.ban_threshold:
                self._blocked[uid] = now
            return None

        self._last_action[uid] = now
        self._spam_count[uid] = max(0, self._spam_count[uid] - 1)
        return await handler(event, data)
