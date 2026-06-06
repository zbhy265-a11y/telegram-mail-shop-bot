import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from bot.database.models import (
    Category,
    Coupon,
    Order,
    Payment,
    Product,
    Stock,
    Ticket,
    User,
)
from bot.database.session import async_session

logger = logging.getLogger(__name__)


async def export_database() -> str:
    data: dict = {"exported_at": datetime.now(timezone.utc).isoformat(), "tables": {}}

    async with async_session() as session:
        for model, name in [
            (User, "users"),
            (Category, "categories"),
            (Product, "products"),
            (Stock, "stock"),
            (Order, "orders"),
            (Payment, "payments"),
            (Coupon, "coupons"),
            (Ticket, "tickets"),
        ]:
            result = await session.execute(select(model))
            rows = result.scalars().all()
            data["tables"][name] = [
                {
                    c.name: (
                        getattr(row, c.name).value
                        if hasattr(getattr(row, c.name), "value")
                        else (
                            getattr(row, c.name).isoformat()
                            if isinstance(getattr(row, c.name), datetime)
                            else getattr(row, c.name)
                        )
                    )
                    for c in row.__table__.columns
                }
                for row in rows
            ]

    return json.dumps(data, indent=2, default=str)
