import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.config import config
from bot.database.models import (
    Admin,
    AdminLevel,
    Category,
    Coupon,
    CouponUsage,
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Product,
    Referral,
    Setting,
    Stock,
    Ticket,
    TicketMessage,
    TicketStatus,
    TransactionLog,
    User,
    utcnow,
)


def generate_referral_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


def generate_order_id() -> str:
    return "ORD" + "".join(secrets.choice(string.digits) for _ in range(10))


class UserRepo:
    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        referrer_code: str | None = None,
    ) -> tuple[User, bool]:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.username = username
            user.first_name = first_name
            return user, False

        referrer = None
        if referrer_code:
            ref_result = await session.execute(
                select(User).where(User.referral_code == referrer_code.upper())
            )
            referrer = ref_result.scalar_one_or_none()

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            referral_code=generate_referral_code(),
            referred_by_id=referrer.id if referrer else None,
        )
        session.add(user)
        await session.flush()

        if referrer:
            session.add(Referral(referrer_id=referrer.id, referred_id=user.id))

        return user, True

    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def add_balance(
        session: AsyncSession, user: User, amount: float, description: str = ""
    ) -> None:
        user.balance += amount
        if amount > 0:
            user.total_deposits += amount
        session.add(
            TransactionLog(
                user_id=user.id, action="deposit", amount=amount, description=description
            )
        )

    @staticmethod
    async def deduct_balance(
        session: AsyncSession, user: User, amount: float, description: str = ""
    ) -> bool:
        if user.balance < amount:
            return False
        user.balance -= amount
        session.add(
            TransactionLog(
                user_id=user.id, action="purchase", amount=-amount, description=description
            )
        )
        return True

    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0

    @staticmethod
    async def get_referral_count(session: AsyncSession, user_id: int) -> int:
        result = await session.execute(
            select(func.count(Referral.id)).where(Referral.referrer_id == user_id)
        )
        return result.scalar() or 0


class CategoryRepo:
    @staticmethod
    async def get_all_active(session: AsyncSession) -> list[Category]:
        result = await session.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.sort_order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, category_id: int) -> Category | None:
        result = await session.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()


class ProductRepo:
    @staticmethod
    async def get_by_category(session: AsyncSession, category_id: int) -> list[Product]:
        result = await session.execute(
            select(Product)
            .where(Product.category_id == category_id, Product.is_active == True)
            .order_by(Product.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, product_id: int) -> Product | None:
        result = await session.execute(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_stock_count(session: AsyncSession, product_id: int) -> int:
        result = await session.execute(
            select(func.count(Stock.id)).where(
                Stock.product_id == product_id, Stock.is_sold == False
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_all(session: AsyncSession) -> list[Product]:
        result = await session.execute(
            select(Product).options(selectinload(Product.category)).order_by(Product.id)
        )
        return list(result.scalars().all())


class StockRepo:
    @staticmethod
    async def get_available(
        session: AsyncSession, product_id: int, quantity: int
    ) -> list[Stock]:
        result = await session.execute(
            select(Stock)
            .where(Stock.product_id == product_id, Stock.is_sold == False)
            .limit(quantity)
            .with_for_update()
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_bulk(session: AsyncSession, product_id: int, lines: list[str]) -> int:
        count = 0
        for line in lines:
            line = line.strip()
            if line and "|" in line:
                session.add(Stock(product_id=product_id, data=line))
                count += 1
        return count

    @staticmethod
    async def add_single(session: AsyncSession, product_id: int, data: str) -> Stock:
        item = Stock(product_id=product_id, data=data.strip())
        session.add(item)
        await session.flush()
        return item

    @staticmethod
    async def remove_by_id(session: AsyncSession, stock_id: int) -> bool:
        result = await session.execute(select(Stock).where(Stock.id == stock_id))
        item = result.scalar_one_or_none()
        if item and not item.is_sold:
            await session.delete(item)
            return True
        return False

    @staticmethod
    async def mark_sold(
        session: AsyncSession, items: list[Stock], order_id: int
    ) -> None:
        now = utcnow()
        for item in items:
            item.is_sold = True
            item.sold_at = now
            item.order_id = order_id


class OrderRepo:
    @staticmethod
    async def create(
        session: AsyncSession,
        user: User,
        product: Product,
        quantity: int,
        unit_price: float,
        total_price: float,
        delivery_data: str,
        discount: float = 0.0,
        coupon_code: str | None = None,
    ) -> Order:
        order = Order(
            order_id=generate_order_id(),
            user_id=user.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            discount=discount,
            coupon_code=coupon_code,
            delivery_data=delivery_data,
            status=OrderStatus.COMPLETED,
        )
        session.add(order)
        await session.flush()
        user.total_orders += 1
        user.total_purchases += total_price
        return order

    @staticmethod
    async def get_user_orders(
        session: AsyncSession, user_id: int, limit: int = 20, offset: int = 0
    ) -> list[Order]:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.product))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_order_id(session: AsyncSession, order_id: str) -> Order | None:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.product), selectinload(Order.user))
            .where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        result = await session.execute(select(func.count(Order.id)))
        return result.scalar() or 0

    @staticmethod
    async def total_revenue(session: AsyncSession) -> float:
        result = await session.execute(
            select(func.coalesce(func.sum(Order.total_price), 0.0))
        )
        return float(result.scalar() or 0)


class PaymentRepo:
    @staticmethod
    async def create(
        session: AsyncSession,
        user: User,
        amount: float,
        method: PaymentMethod,
        screenshot_file_id: str | None = None,
        transaction_ref: str | None = None,
    ) -> Payment:
        payment = Payment(
            user_id=user.id,
            amount=amount,
            method=method,
            screenshot_file_id=screenshot_file_id,
            transaction_ref=transaction_ref,
            status=PaymentStatus.PENDING,
        )
        session.add(payment)
        await session.flush()
        return payment

    @staticmethod
    async def get_pending(session: AsyncSession) -> list[Payment]:
        result = await session.execute(
            select(Payment)
            .options(selectinload(Payment.user))
            .where(Payment.status == PaymentStatus.PENDING)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, payment_id: int) -> Payment | None:
        result = await session.execute(
            select(Payment)
            .options(selectinload(Payment.user))
            .where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def approve(session: AsyncSession, payment: Payment) -> None:
        payment.status = PaymentStatus.APPROVED
        payment.processed_at = utcnow()
        await UserRepo.add_balance(
            session,
            payment.user,
            payment.amount,
            f"Payment #{payment.id} approved",
        )

    @staticmethod
    async def reject(session: AsyncSession, payment: Payment, note: str = "") -> None:
        payment.status = PaymentStatus.REJECTED
        payment.processed_at = utcnow()
        payment.admin_note = note


class CouponRepo:
    @staticmethod
    async def get_by_code(session: AsyncSession, code: str) -> Coupon | None:
        result = await session.execute(
            select(Coupon).where(Coupon.code == code.upper(), Coupon.is_active == True)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def validate_for_user(
        session: AsyncSession, coupon: Coupon, user_id: int
    ) -> str | None:
        if coupon.expiry_date and coupon.expiry_date < utcnow():
            return "Coupon has expired"
        if coupon.usage_limit > 0 and coupon.used_count >= coupon.usage_limit:
            return "Coupon usage limit reached"
        usage = await session.execute(
            select(CouponUsage).where(
                CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user_id
            )
        )
        if usage.scalar_one_or_none():
            return "You have already used this coupon"
        return None

    @staticmethod
    async def apply(session: AsyncSession, coupon: Coupon, user_id: int) -> None:
        coupon.used_count += 1
        session.add(CouponUsage(user_id=user_id, coupon_id=coupon.id))

    @staticmethod
    async def get_all(session: AsyncSession) -> list[Coupon]:
        result = await session.execute(select(Coupon).order_by(Coupon.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        code: str,
        discount_percent: float,
        expiry_date: datetime | None = None,
        usage_limit: int = 0,
    ) -> Coupon:
        coupon = Coupon(
            code=code.upper(),
            discount_percent=discount_percent,
            expiry_date=expiry_date,
            usage_limit=usage_limit,
        )
        session.add(coupon)
        await session.flush()
        return coupon


class TicketRepo:
    @staticmethod
    async def create(session: AsyncSession, user: User, subject: str) -> Ticket:
        ticket = Ticket(user_id=user.id, subject=subject)
        session.add(ticket)
        await session.flush()
        return ticket

    @staticmethod
    async def add_message(
        session: AsyncSession,
        ticket: Ticket,
        sender_id: int,
        message: str,
        is_admin: bool = False,
    ) -> TicketMessage:
        msg = TicketMessage(
            ticket_id=ticket.id,
            sender_id=sender_id,
            message=message,
            is_admin=is_admin,
        )
        session.add(msg)
        await session.flush()
        return msg

    @staticmethod
    async def get_user_tickets(session: AsyncSession, user_id: int) -> list[Ticket]:
        result = await session.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_open_tickets(session: AsyncSession) -> list[Ticket]:
        result = await session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user))
            .where(Ticket.status == TicketStatus.OPEN)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, ticket_id: int) -> Ticket | None:
        result = await session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user), selectinload(Ticket.messages))
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def close(session: AsyncSession, ticket: Ticket) -> None:
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = utcnow()


class AdminRepo:
    @staticmethod
    async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
        if telegram_id in config.admin_ids:
            return True
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_level(session: AsyncSession, telegram_id: int) -> AdminLevel | None:
        if telegram_id in config.admin_ids:
            return AdminLevel.SUPER
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        admin = result.scalar_one_or_none()
        return admin.level if admin else None

    @staticmethod
    async def add_admin(
        session: AsyncSession, telegram_id: int, level: AdminLevel = AdminLevel.ADMIN
    ) -> Admin:
        admin = Admin(telegram_id=telegram_id, level=level)
        session.add(admin)
        await session.flush()
        return admin


class StatsRepo:
    @staticmethod
    async def get_dashboard(session: AsyncSession) -> dict:
        users = await UserRepo.count_all(session)
        orders = await OrderRepo.count_all(session)
        revenue = await OrderRepo.total_revenue(session)
        pending = await session.execute(
            select(func.count(Payment.id)).where(Payment.status == PaymentStatus.PENDING)
        )
        open_tickets = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
        )
        return {
            "users": users,
            "orders": orders,
            "revenue": revenue,
            "pending_payments": pending.scalar() or 0,
            "open_tickets": open_tickets.scalar() or 0,
        }


class ReferralRepo:
    @staticmethod
    async def add_commission(
        session: AsyncSession, buyer: User, purchase_amount: float
    ) -> None:
        if not buyer.referred_by_id:
            return
        referrer = await UserRepo.get_by_id(session, buyer.referred_by_id)
        if not referrer:
            return
        commission = purchase_amount * (config.referral_commission / 100)
        referrer.referral_earnings += commission
        result = await session.execute(
            select(Referral).where(
                Referral.referrer_id == referrer.id, Referral.referred_id == buyer.id
            )
        )
        ref = result.scalar_one_or_none()
        if ref:
            ref.commission_earned += commission
        session.add(
            TransactionLog(
                user_id=referrer.id,
                action="referral",
                amount=commission,
                description=f"Referral commission from user {buyer.telegram_id}",
            )
        )

    @staticmethod
    async def withdraw_earnings(session: AsyncSession, user: User) -> float:
        amount = user.referral_earnings
        if amount <= 0:
            return 0.0
        user.referral_earnings = 0.0
        user.balance += amount
        session.add(
            TransactionLog(
                user_id=user.id,
                action="referral_withdraw",
                amount=amount,
                description="Referral earnings withdrawn to balance",
            )
        )
        return amount


async def seed_categories(session: AsyncSession) -> None:
    categories = [
        ("Hotmail Trust", "📧", 1),
        ("Outlook Trust", "📧", 2),
        ("Fresh Gmail", "📧", 3),
        ("Aged Gmail", "📧", 4),
        ("Edu Mail", "📧", 5),
        ("Yahoo Mail", "📧", 6),
        ("AOL Mail", "📧", 7),
        ("Custom Mail", "📧", 8),
    ]
    for name, emoji, order in categories:
        exists = await session.execute(select(Category).where(Category.name == name))
        if not exists.scalar_one_or_none():
            session.add(Category(name=name, emoji=emoji, sort_order=order))


async def seed_admins(session: AsyncSession) -> None:
    for admin_id in config.admin_ids:
        exists = await session.execute(
            select(Admin).where(Admin.telegram_id == admin_id)
        )
        if not exists.scalar_one_or_none():
            session.add(Admin(telegram_id=admin_id, level=AdminLevel.SUPER))
