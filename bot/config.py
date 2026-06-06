import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def _normalize_database_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _database_ssl_required(url: str) -> bool:
    if os.getenv("DATABASE_SSL", "").lower() in ("1", "true", "yes"):
        return True
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return True
    return "localhost" not in url and "127.0.0.1" not in url


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    database_url: str = field(
        default_factory=lambda: _normalize_database_url(os.getenv("DATABASE_URL", ""))
    )
    admin_ids: list[int] = field(default_factory=_parse_admin_ids)
    binance_pay_id: str = os.getenv("BINANCE_PAY_ID", "")
    usdt_trc20: str = os.getenv("USDT_TRC20_ADDRESS", "")
    usdt_bep20: str = os.getenv("USDT_BEP20_ADDRESS", "")
    bkash_number: str = os.getenv("BKASH_NUMBER", "")
    nagad_number: str = os.getenv("NAGAD_NUMBER", "")
    rocket_number: str = os.getenv("ROCKET_NUMBER", "")
    referral_commission: float = float(os.getenv("REFERRAL_COMMISSION_PERCENT", "10"))
    support_username: str = os.getenv("SUPPORT_USERNAME", "")
    min_deposit: float = float(os.getenv("MIN_DEPOSIT", "1.0"))
    currency: str = os.getenv("CURRENCY_SYMBOL", "$")

    def db_connect_args(self) -> dict:
        if _database_ssl_required(self.database_url):
            return {"ssl": True}
        return {}

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")


config = Config()
