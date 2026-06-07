class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    database_url: str = field(default_factory=_resolve_database_url)
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
    return {
        "ssl": False
    }

    def database_host(self) -> str:
        return _database_host(self.database_url)

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is required. In Railway: Bot service → Variables → "
                "Add Reference → PostgreSQL → DATABASE_URL"
            )
        if _is_placeholder_database_url(self.database_url):
            raise ValueError(
                "DATABASE_URL is still a placeholder (host/user/password). "
                "Delete it and add PostgreSQL reference from Railway dashboard."
            )
