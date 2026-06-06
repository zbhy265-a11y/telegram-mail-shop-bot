from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    waiting_amount = State()
    waiting_screenshot = State()
    waiting_ref = State()


class SupportStates(StatesGroup):
    waiting_subject = State()
    waiting_message = State()
    waiting_reply = State()


class CouponStates(StatesGroup):
    waiting_code = State()


class BulkBuyStates(StatesGroup):
    waiting_quantity = State()


class AdminStates(StatesGroup):
    add_balance_user = State()
    add_balance_amount = State()
    remove_balance_user = State()
    remove_balance_amount = State()
    ban_user = State()
    unban_user = State()
    broadcast_message = State()
    add_stock_product = State()
    add_stock_data = State()
    remove_stock_product = State()
    add_product_name = State()
    add_product_category = State()
    add_product_price = State()
    add_product_description = State()
    edit_product_select = State()
    edit_product_field = State()
    delete_product_select = State()
    create_coupon_code = State()
    create_coupon_discount = State()
    create_coupon_expiry = State()
    create_coupon_limit = State()
    ticket_reply = State()
    reject_payment_note = State()
