import argparse
import os
import shutil
from glob import glob
from datetime import datetime, timedelta
from pathlib import Path
from core.config import Config
from core.utilities import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Tool for archiving old processed trades.")
    parser.add_argument("--old_days", type=int, required=True,
                        help="Trade records older than old_days will be moved the archive folder.")
    args = parser.parse_args()

    logger = setup_logging(
        log_file="archiving.log",
        logger_name="archive_processed_trades"
    )

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
            logger.debug(f"reference_date: {reference_date} | {reference_timestamp}")
            logger.debug(f"trade_date: {trade_date} | {trade_timestamp}")
            logger.info(f"Transfer: {source_file} => {destination_path}")
            shutil.move(source_file, destination_path)


if __name__ == "__main__":
    main()
