
import os
import json
from dotenv import load_dotenv


load_dotenv()


class Config:

    # Wallet settings
    WALLET_SETTINGS_FILE: str = os.getenv(
        "WALLET_SETTINGS_FILE", "wallet_config.json")

    # Polymarket API settings
    GAMMA_API = os.getenv("GAMMA_API",
                          "https://gamma-api.polymarket.com")
    CLOB_API = os.getenv("CLOB_API",
                         "https://clob.polymarket.com")
    CHAIN_ID = int(os.getenv("CHAIN_ID", 137))  # Polygon mainnet
    USDC_TICK_SIZE = int(os.getenv("USDC_TICK_SIZE", 1_000_000))

    # Market settings
    MARKET_SETTINGS_OVERRIDE_URL = os.getenv(
        "MARKET_SETTINGS_OVERRIDE_URL", "")
    MARKET_SETTINGS_FILE = os.getenv(
        "MARKET_SETTINGS_FILE", "market_config.json")
    MARKET_SETTINGS_DEFAULT = {
        "paper_trade": True,
        "entry_price": 0.49,
        "order_size": 5,
        "start_hour": 5,
        "end_hour": 18,
    }
    PAPER_TRADE_CHECK_PERFORMANCE_HOURS: int = int(
        os.getenv("PAPER_TRADE_CHECK_PERFORMANCE_HOURS", 24))
    PAPER_TRADE_OFF_THRESHOLD: float = float(
        os.getenv("PAPER_TRADE_OFF_THRESHOLD", 0.5))
    PAPER_TRADE_ON_THRESHOLD: float = float(
        os.getenv("PAPER_TRADE_ON_THRESHOLD", 0.52))

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOGGER_NAME = "polymarket.bot"

    # Trade settings
    TRADE_RECORDS_DIR: str = "trades"
    TRADE_RECORDS_PROCESSED_DIR: str = "trades_processed"
    TRADE_RECORDS_ARCHIVE: str = "old_trades"
    TRADE_ORDER_EXPIRATION: int = int(
        os.getenv("TRADE_ORDER_EXPIRATION", 210))
    TRADE_MAX_RECORDS_UPDATE: int = int(
        os.getenv("TRADE_MAX_RECORDS_UPDATE", 50))

    # REST client settings
    REST_TIMEOUT: float = float(
        os.getenv("REST_TIMEOUT", 3))
    REST_RETRIES: int = int(os.getenv("REST_RETRIES", 2))

    # Prediction settings
    MINIMUM_NUM_PRICE_HISTORY: int = int(
        os.getenv("MINIMUM_NUM_PRICE_HISTORY", 23))
    NUM_PREDICTIONS = int(os.getenv("NUM_PREDICTIONS", 5))
    PREDICTION_API_ENDPOINT = os.getenv("PREDICTION_API_ENDPOINT", "")
    PREDICTION_API_RESULTS_ENDPOINT = os.getenv(
        "PREDICTION_API_RESULTS_ENDPOINT", "")
    PREDICTION_API_WAITING_STATUS_CODE: int = int(os.getenv(
        "PREDICTION_API_WAITING_STATUS_CODE", 418))
    PREDICTION_API_TOKEN = os.getenv("PREDICTION_API_TOKEN", "")
    PREDICTION_API_MAX_POLL: int = int(
        os.getenv("PREDICTION_API_MAX_POLL", 120))

    # Email settings
    EMAIL_RECEIVERS: str = os.getenv("EMAIL_RECEIVERS", "")
    EMAIL_SENDER_ADDRESS: str = os.getenv("EMAIL_SENDER_ADDRESS", "")
    EMAIL_SENDER_PASS: str = os.getenv("EMAIL_SENDER_PASS", "")
    EMAIL_SMTP_SERVER: str = os.getenv("EMAIL_SMTP_SERVER", "")
    EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", 0))
    EMAIL_UPDATE_RECORDS_NOTIFICATION: bool = os.getenv(
        "EMAIL_UPDATE_RECORDS_NOTIFICATION", "false").lower() == "true"
    EMAIL_LIMIT_ORDER_INFO: bool = os.getenv(
        "EMAIL_LIMIT_ORDER_INFO", "false").lower() == "true"

    @classmethod
    def get_paper_trade_settings(cls, settings_file: str = None):
        market_settings = Config._get_all_market_settings(settings_file)
        result = {}
        for market_slug, settings in market_settings.items():
            result[market_slug] = settings["paper_trade"]
        return result

    @classmethod
    def get_paper_trade_setting(cls, market_slug: str):
        settings = Config.get_market_settings(market_slug)
        return settings["paper_trade"]

    @classmethod
    def save_paper_trade_settings(cls, settings_json: dict, settings_file: str = None):
        for market in settings_json:
            market_settings = Config.get_market_settings(market)
            market_settings[market]["paper_trade"] = settings_json[market]
            Config.save_market_settings(market, market_settings)

    @classmethod
    def _get_all_market_settings(cls, settings_file: str = None):
        json_file = cls.MARKET_SETTINGS_FILE if settings_file is None else settings_file
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError as e:
            return {}
        except json.JSONDecodeError:
            return {}

    @classmethod
    def get_market_settings(cls, market: str, settings_file: str = None):
        json_file = cls.MARKET_SETTINGS_FILE if settings_file is None else settings_file
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            if market in data:
                return data[market]
            return dict(cls.MARKET_SETTINGS_DEFAULT)
        except FileNotFoundError as e:
            return dict(cls.MARKET_SETTINGS_DEFAULT)
        except json.JSONDecodeError:
            return dict(cls.MARKET_SETTINGS_DEFAULT)

    @classmethod
    def _save_all_market_settings(cls, settings: dict, settings_file: str = None):
        json_file = cls.MARKET_SETTINGS_FILE if settings_file is None else settings_file
        with open(json_file, 'w') as f:
            json.dump(settings, f, indent=4)

    @classmethod
    def save_market_settings(cls, market: str, settings: dict, settings_file: str = None):
        json_file = cls.MARKET_SETTINGS_FILE if settings_file is None else settings_file
        all_market_settings = cls._get_all_market_settings(json_file)
        market_settings = cls.MARKET_SETTINGS_DEFAULT | settings
        all_market_settings[market] = market_settings
        cls._save_all_market_settings(all_market_settings)
