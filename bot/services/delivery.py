import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Product, User
from bot.database.repository import (
    CouponRepo,
    OrderRepo,
    ProductRepo,
    ReferralRepo,
    StockRepo,
    UserRepo,
)

logger = logging.getLogger(__name__)


class DeliveryService:
    @staticmethod
    async def purchase(
        session: AsyncSession,
        user: User,
        product: Product,
        quantity: int,
        coupon_code: str | None = None,
    ) -> tuple[bool, str, str | None]:
        stock_count = await ProductRepo.get_stock_count(session, product.id)
        if stock_count < quantity:
            return False, f"❌ Insufficient stock. Available: {stock_count}", None

        unit_price = product.price
        total = unit_price * quantity
        discount = 0.0
        applied_coupon = None

        if coupon_code:
            coupon = await CouponRepo.get_by_code(session, coupon_code)
            if coupon:
                error = await CouponRepo.validate_for_user(session, coupon, user.id)
                if not error:
                    discount = total * (coupon.discount_percent / 100)
                    total -= discount
                    applied_coupon = coupon.code
                    await CouponRepo.apply(session, coupon, user.id)

        if user.balance < total:
            return (
                False,
                f"❌ Insufficient balance.\n\nRequired: ${total:.2f}\nYour balance: ${user.balance:.2f}",
                None,
            )

        stock_items = await StockRepo.get_available(session, product.id, quantity)
        if len(stock_items) < quantity:
            return False, "❌ Stock unavailable. Please try again.", None

        if not await UserRepo.deduct_balance(
            session, user, total, f"Purchase: {product.name} x{quantity}"
        ):
            return False, "❌ Payment failed. Insufficient balance.", None

        delivery_data = "\n".join(item.data for item in stock_items)

        order = await OrderRepo.create(
            session,
            user=user,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total,
            delivery_data=delivery_data,
            discount=discount,
            coupon_code=applied_coupon,
        )

        await StockRepo.mark_sold(session, stock_items, order.id)
        await ReferralRepo.add_commission(session, user, total)

        logger.info(
            "Order %s completed: user=%s product=%s qty=%d",
            order.order_id,
            user.telegram_id,
            product.name,
            quantity,
        )

        return True, delivery_data, order.order_id
