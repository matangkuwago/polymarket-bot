import argparse
import os
import shutil
from glob import glob
from datetime import datetime, timedelta
from pathlib import Path
from core.config import Config


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
    parser = argparse.ArgumentParser(
        description="Tool for archiving old processed trades.")
    parser.add_argument("--old_days", type=int, required=True,
                        help="Trade records older than old_days will be moved the archive folder.")
    args = parser.parse_args()

    reference_date = datetime.now() - timedelta(days=args.old_days)
    reference_timestamp = reference_date.timestamp()

    processed_dir = Config.TRADE_RECORDS_PROCESSED_DIR
    trade_files = glob(os.path.join(processed_dir, '*.trade'))
    trade_files.sort()

    for file in trade_files:
        trade_timestamp = os.path.basename(file).replace(
            ".trade", "")
        trade_timestamp = trade_timestamp.split("-")
        trade_timestamp = trade_timestamp[-1]
        trade_timestamp = int(trade_timestamp)
        trade_date = datetime.fromtimestamp(trade_timestamp)

        if trade_timestamp < reference_timestamp:
            source_file = file
            destination_path = os.path.join(
                Config.TRADE_RECORDS_ARCHIVE, Config.TRADE_RECORDS_PROCESSED_DIR, os.path.basename(file))
            print(f"reference_date: {reference_date}")
            print(f"reference_timestamp: {reference_timestamp}")
            print(f"trade_date: {trade_date}")
            print(f"trade_timestamp: {trade_timestamp}")
            print(f"Transfer: {source_file} => {destination_path}")
            shutil.move(source_file, destination_path)


if __name__ == "__main__":
    main()
