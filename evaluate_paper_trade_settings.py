from datetime import datetime, timedelta
from core.trader import TradeStats
from core.config import Config


def main():
    date_limit = datetime.now() - timedelta(hours=Config.PAPER_TRADE_MIN_EVALUATION_HOURS)
    timestamp_earliest = date_limit.timestamp()
    trade_stats = TradeStats()
    trade_stats.evaluate_paper_trade_settings_change(timestamp_earliest)


if __name__ == "__main__":
    main()
