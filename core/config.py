# DEPRECATED: Use polymarket_algo.* packages instead. This file exists for backward compatibility.
import os
from datetime import timedelta, timezone

from dotenv import load_dotenv

load_dotenv()


# Timezone configuration
TIMEZONE_NAME = os.getenv("TIMEZONE", "Asia/Jakarta")

# Create timezone object (Asia/Jakarta = UTC+7)
_TZ_OFFSETS = {
    "Asia/Jakarta": timedelta(hours=7),
    "Asia/Singapore": timedelta(hours=8),
    "Asia/Tokyo": timedelta(hours=9),
    "UTC": timedelta(hours=0),
    "America/New_York": timedelta(hours=-5),
    "America/Los_Angeles": timedelta(hours=-8),
}

LOCAL_TZ = timezone(_TZ_OFFSETS.get(TIMEZONE_NAME, timedelta(hours=7)))


class Config:

    # Polymarket API settings
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    # 0=EOA/MetaMask, 1=Magic/proxy
    SIGNATURE_TYPE: int = int(os.getenv("SIGNATURE_TYPE", "0"))
    FUNDER_ADDRESS: str = os.getenv(
        "FUNDER_ADDRESS", "")  # Required for proxy wallets
    GAMMA_API = "https://gamma-api.polymarket.com"
    CLOB_API = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon mainnet
    USDC_TICK_SIZE = 1_000_000

    # Binance API settings
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")

    # Timing
    ENTRY_SECONDS_BEFORE: int = int(os.getenv("ENTRY_SECONDS_BEFORE", "30"))

    # Mode
    PAPER_TRADE: bool = os.getenv("PAPER_TRADE", "true").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    LOGGER_NAME = "polymarket.bot"

    # Trade settings
    TRADE_RECORDS_DIR: str = "trades"
    TRADE_ENTRY_PRICE: float = float(os.getenv("TRADE_ENTRY_PRICE", 0.4))
    TRADE_ORDER_SIZE: float = float(os.getenv("TRADE_ORDER_SIZE", 5.0))

    # WebSocket settings
    WS_CLOB_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    WS_USER_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
    WS_RTDS_URL = "wss://ws-live-data.polymarket.com"
    USE_WEBSOCKET: bool = os.getenv("USE_WEBSOCKET", "true").lower() == "true"

    # REST client settings
    REST_TIMEOUT: float = float(
        os.getenv("REST_TIMEOUT", "3"))  # Faster timeout
    REST_RETRIES: int = int(os.getenv("REST_RETRIES", "2"))

    # Prediction settings
    MINIMUM_NUM_PRICE_HISTORY: int = 23  # past prices needed to make a prediction
    NUM_PREDICTIONS = 5  # we predict 5 outcomes
    PREDICTION_API_ENDPOINT = os.getenv("PREDICTION_API_ENDPOINT", "")
    PREDICTION_API_RESULTS_ENDPOINT = os.getenv(
        "PREDICTION_API_RESULTS_ENDPOINT", "")
    PREDICTION_API_WAITING_STATUS_CODE: int = os.getenv(
        "PREDICTION_API_WAITING_STATUS_CODE", 418)
    PREDICTION_API_TOKEN = os.getenv("PREDICTION_API_TOKEN", "")
    PREDICTION_API_MAX_POLL: int = os.getenv("PREDICTION_API_MAX_POLL", 120)

    # Email settings
    EMAIL_RECEIVERS: str = os.getenv("EMAIL_RECEIVERS", "")
    EMAIL_SENDER_ADDRESS: str = os.getenv("EMAIL_SENDER_ADDRESS", "")
    EMAIL_SENDER_PASS: str = os.getenv("EMAIL_SENDER_PASS", "")
    EMAIL_SMTP_SERVER: str = os.getenv("EMAIL_SMTP_SERVER", "")
    EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", 0))
