
import os
import json
from dotenv import load_dotenv


load_dotenv()


class Config:

    BOT_ID: str = os.getenv("BOT_ID", "001")

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

    # Statistics settings
    STATS_DIR: str = "stats_per_hour"

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

    # Market settings
    BOT_SETTINGS_FILE = os.getenv(
        "BOT_SETTINGS_FILE", "bot_config.json")

    @classmethod
    def get_bot_market_setting(cls, bot_id: str, market: str, setting: str, settings_file: str = None):
        data = cls.get_bot_market_settings(bot_id, market, settings_file)
        return data[setting]

    @classmethod
    def save_bot_market_setting(cls, bot_id: str, market: str, setting: str, value, settings_file: str = None):
        data = cls.get_bot_market_settings(bot_id, market, settings_file)
        data[setting] = value
        cls.save_bot_market_settings(bot_id, market, data)

    @classmethod
    def _get_all_market_settings(cls, settings_file: str = None):
        json_file = cls.BOT_SETTINGS_FILE if settings_file is None else settings_file
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError as e:
            return {}
        except json.JSONDecodeError:
            return {}

    @classmethod
    def get_bot_market_settings(cls, bot_id: str, market: str, settings_file: str = None):
        json_file = cls.BOT_SETTINGS_FILE if settings_file is None else settings_file
        with open(json_file, 'r') as f:
            data = json.load(f)
        if bot_id in data and market in data[bot_id]:
            return data[bot_id][market]

        raise RuntimeError(
            f"Settings for {bot_id}: {market} not found in {json_file}!")

    @classmethod
    def _save_all_market_settings(cls, settings: dict, settings_file: str = None):
        json_file = cls.BOT_SETTINGS_FILE if settings_file is None else settings_file
        with open(json_file, 'w') as f:
            json.dump(settings, f, indent=4)

    @classmethod
    def save_bot_market_settings(cls, bot_id: str, market: str, settings: dict, settings_file: str = None):
        json_file = cls.BOT_SETTINGS_FILE if settings_file is None else settings_file
        all_market_settings = cls._get_all_market_settings(json_file)
        if bot_id not in all_market_settings or market not in all_market_settings[bot_id]:
            raise RuntimeError(
                f"Settings for {bot_id}: {market} not found in {json_file}!")
        all_market_settings[bot_id][market] = settings
        cls._save_all_market_settings(all_market_settings)

    # Reporting settings
    REPORT_CONFIG_FILE: str = os.getenv(
        "REPORT_CONFIG_FILE", "report_config.json")
