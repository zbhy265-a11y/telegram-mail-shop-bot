from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models import Payment, Product, Ticket


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats"),
                InlineKeyboardButton(text="👥 Users", callback_data="adm_users"),
            ],
            [
                InlineKeyboardButton(text="📦 Products", callback_data="adm_products"),
                InlineKeyboardButton(text="📋 Stock", callback_data="adm_stock"),
            ],
            [
                InlineKeyboardButton(text="💳 Payments", callback_data="adm_payments"),
                InlineKeyboardButton(text="🎟 Coupons", callback_data="adm_coupons"),
            ],
            [
                InlineKeyboardButton(text="🎫 Tickets", callback_data="adm_tickets"),
                InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"),
            ],
            [
                InlineKeyboardButton(text="💰 Balance", callback_data="adm_balance"),
                InlineKeyboardButton(text="🚫 Ban/Unban", callback_data="adm_ban"),
            ],
            [
                InlineKeyboardButton(text="📥 Export DB", callback_data="adm_export"),
                InlineKeyboardButton(text="◀️ Close", callback_data="adm_close"),
            ],
        ]
    )


def admin_back(callback: str = "admin_panel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Admin", callback_data=callback)]
        ]
    )


def admin_products_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Add Product", callback_data="adm_add_product")],
    ]
    for p in products:
        rows.append([
            InlineKeyboardButton(
                text=f"{p.name} (${p.price:.2f})",
                callback_data=f"adm_prod_{p.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_product_actions(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Edit", callback_data=f"adm_edit_prod_{product_id}"),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"adm_del_prod_{product_id}"),
            ],
            [
                InlineKeyboardButton(text="📥 Add Stock", callback_data=f"adm_addstock_{product_id}"),
                InlineKeyboardButton(text="📊 Stock Count", callback_data=f"adm_stockcount_{product_id}"),
            ],
            [InlineKeyboardButton(text="◀️ Back", callback_data="adm_products")],
        ]
    )


def admin_payments_keyboard(payments: list[Payment]) -> InlineKeyboardMarkup:
    rows = []
    for p in payments[:15]:
        user_label = p.user.username or str(p.user.telegram_id)
        rows.append([
            InlineKeyboardButton(
                text=f"#{p.id} ${p.amount:.2f} — {user_label}",
                callback_data=f"adm_pay_{p.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_actions(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"adm_pay_ok_{payment_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"adm_pay_no_{payment_id}"),
            ],
            [InlineKeyboardButton(text="◀️ Back", callback_data="adm_payments")],
        ]
    )


def admin_tickets_keyboard(tickets: list[Ticket]) -> InlineKeyboardMarkup:
    rows = []
    for t in tickets[:15]:
        user_label = t.user.username or str(t.user.telegram_id)
        rows.append([
            InlineKeyboardButton(
                text=f"#{t.id} {t.subject[:20]} — {user_label}",
                callback_data=f"adm_ticket_{t.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_ticket_actions(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Reply", callback_data=f"adm_treply_{ticket_id}"),
                InlineKeyboardButton(text="🔒 Close", callback_data=f"adm_tclose_{ticket_id}"),
            ],
            [InlineKeyboardButton(text="◀️ Back", callback_data="adm_tickets")],
        ]
    )


def admin_balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add Balance", callback_data="adm_add_bal")],
            [InlineKeyboardButton(text="➖ Remove Balance", callback_data="adm_rem_bal")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")],
        ]
    )


def admin_ban_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Ban User", callback_data="adm_ban_user")],
            [InlineKeyboardButton(text="✅ Unban User", callback_data="adm_unban_user")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")],
        ]
    )


def admin_coupons_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Create Coupon", callback_data="adm_new_coupon")],
            [InlineKeyboardButton(text="📋 List Coupons", callback_data="adm_list_coupons")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")],
        ]
    )
