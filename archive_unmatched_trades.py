import os
import logging
from glob import glob
from core.config import Config
from core.polymarket import PolymarketClient
from core.trader import Trade, LiveTrader
from core.utilities import Emailer


def archive_unmatched_trade(trade):
    source_file = os.path.join(
        f"{Config.TRADE_RECORDS_PROCESSED_DIR}",
        f"{trade.market_slug}.trade"
    )
    target_file = os.path.join(
        f"{Config.TRADE_RECORDS_ARCHIVE}",
        f"{Config.TRADE_RECORDS_PROCESSED_DIR}",
        f"{trade.market_slug}.trade"
    )
    os.rename(source_file, target_file)
    print(
        f"Trade record for {trade.market_slug} has been moved "
        f"from {source_file} to {target_file}."
    )


def main():
    processed_dir = Config.TRADE_RECORDS_PROCESSED_DIR
    trade_files = glob(os.path.join(processed_dir, '*.trade'))
    trade_files.sort()

    for file in trade_files:
        market_slug = os.path.basename(file).replace(".trade", "")
        trade = Trade.load(market_slug, trade_files_directory=processed_dir)
        if not trade:
            continue

        if trade.order_status != "MATCHED":
            archive_unmatched_trade(trade)


if __name__ == "__main__":
    main()
