from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models import Category, Order, PaymentMethod, Product, Ticket


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Shop", callback_data="shop"),
                InlineKeyboardButton(text="💰 Add Balance", callback_data="deposit"),
            ],
            [
                InlineKeyboardButton(text="📦 Orders", callback_data="orders"),
                InlineKeyboardButton(text="👤 Profile", callback_data="profile"),
            ],
            [
                InlineKeyboardButton(text="🎁 Referral", callback_data="referral"),
                InlineKeyboardButton(text="🎫 Support", callback_data="support"),
            ],
            [
                InlineKeyboardButton(text="📊 Statistics", callback_data="statistics"),
                InlineKeyboardButton(text="🎟 Coupon", callback_data="coupon"),
            ],
        ]
    )


def back_button(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data=callback)]
        ]
    )


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        rows.append([
            InlineKeyboardButton(
                text=f"{cat.emoji} {cat.name}",
                callback_data=f"cat_{cat.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_keyboard(products: list[Product], category_id: int) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        rows.append([
            InlineKeyboardButton(
                text=f"{p.name} — ${p.price:.2f}",
                callback_data=f"prod_{p.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="shop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_keyboard(product_id: int, category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Buy Single", callback_data=f"buy_1_{product_id}"
                ),
                InlineKeyboardButton(
                    text="📦 Buy Bulk", callback_data=f"buy_bulk_{product_id}"
                ),
            ],
            [InlineKeyboardButton(text="◀️ Back", callback_data=f"cat_{category_id}")],
        ]
    )


def payment_methods_keyboard() -> InlineKeyboardMarkup:
    methods = [
        ("💳 Binance Pay", PaymentMethod.BINANCE.value),
        ("💵 USDT TRC20", PaymentMethod.USDT_TRC20.value),
        ("💵 USDT BEP20", PaymentMethod.USDT_BEP20.value),
        ("🇧🇩 bKash", PaymentMethod.BKASH.value),
        ("🇧🇩 Nagad", PaymentMethod.NAGAD.value),
        ("🇧🇩 Rocket", PaymentMethod.ROCKET.value),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"pay_{method}")]
        for label, method in methods
    ]
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deposit_confirm_keyboard(method: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ I've Paid — Send Screenshot",
                    callback_data=f"deposit_confirm_{method}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Back", callback_data="deposit")],
        ]
    )


def orders_keyboard(orders: list[Order], page: int = 0, has_more: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for o in orders:
        rows.append([
            InlineKeyboardButton(
                text=f"#{o.order_id} — {o.product.name if o.product else 'Product'}",
                callback_data=f"order_{o.order_id}",
            )
        ])
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️ Prev", callback_data=f"orders_page_{page - 1}")
        )
    if has_more:
        nav.append(
            InlineKeyboardButton(text="Next ➡️", callback_data=f"orders_page_{page + 1}")
        )
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Open Ticket", callback_data="ticket_new")],
            [InlineKeyboardButton(text="📋 My Tickets", callback_data="ticket_list")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")],
        ]
    )


def tickets_keyboard(tickets: list[Ticket]) -> InlineKeyboardMarkup:
    rows = []
    for t in tickets:
        status = "🟢" if t.status.value == "open" else "🔴"
        rows.append([
            InlineKeyboardButton(
                text=f"{status} #{t.id} — {t.subject[:30]}",
                callback_data=f"ticket_{t.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="support")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ticket_detail_keyboard(ticket_id: int, is_open: bool) -> InlineKeyboardMarkup:
    rows = []
    if is_open:
        rows.append([
            InlineKeyboardButton(text="💬 Reply", callback_data=f"ticket_reply_{ticket_id}")
        ])
        rows.append([
            InlineKeyboardButton(text="🔒 Close Ticket", callback_data=f"ticket_close_{ticket_id}")
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="ticket_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referral_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Withdraw Earnings", callback_data="ref_withdraw")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")],
        ]
    )
