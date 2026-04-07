import os
import argparse
import csv
from datetime import datetime, timedelta
from core.trader import TradeStats
from core.config import Config


parser = argparse.ArgumentParser(
    description="Tool for generating statistics per hour.")
parser.add_argument("--start_date", type=str, required=True,
                    help="start date to use to filter the data, format is yyyy-mm-dd e.g. 2026-04-01")
args = parser.parse_args()


def get_dates(timestamps):
    start_ts = min(timestamps)
    end_ts = max(timestamps)

    start_date = datetime.fromtimestamp(start_ts).date()
    end_date = datetime.fromtimestamp(end_ts).date()

    dates = [start_date + timedelta(days=x)
             for x in range((end_date - start_date).days + 1)]

    return [date.strftime("%Y-%m-%d") for date in dates]


def get_performance(
    trade_files: list,
    date: str,
    hour: int,
    num_stats_hours: int = Config.PAPER_TRADE_CHECK_PERFORMANCE_HOURS
):
    end_date = datetime.strptime(date, "%Y-%m-%d") + timedelta(hours=hour+1)
    end_ts = end_date.timestamp()
    start_date = end_date - timedelta(hours=num_stats_hours)
    start_ts = start_date.timestamp()

    filtered_trade_files = list(filter(
        lambda x: start_ts <= x["timestamp"] and x["timestamp"] <= end_ts,
        trade_files
    ))
    if not filtered_trade_files:
        return ""

    record_count = 0
    wins = 0
    for trade_item in filtered_trade_files:
        trade = trade_item["trade"]
        record_count += 1
        if trade.won:
            wins += 1
    performance = f"{(wins / record_count)*100:.2f}%" if record_count > 0 else ""
    return performance


def main(ticker: str):

    trade_stats = TradeStats()
    trade_stats_old = TradeStats(
        trade_files_directory=os.path.join(
            Config.TRADE_RECORDS_ARCHIVE,
            Config.TRADE_RECORDS_PROCESSED_DIR
        )
    )
    trade_files = trade_stats.get_trade_files() + trade_stats_old.get_trade_files()
    if not trade_files:
        print(f"No data to process.")
        exit(0)

    filter_timestamp = datetime.strptime(
        args.start_date, "%Y-%m-%d") .timestamp()

    trade_files = list(filter(
        lambda x: (x["timestamp"] >= filter_timestamp and
                   ticker in x["trade"].market_slug),
        trade_files
    ))

    timestamps = [x["timestamp"] for x in trade_files]
    dates = get_dates(timestamps)

    headers = ["time"] + dates
    csv_data = [headers]

    for hour in range(0, 24):
        hour_string = f" {hour:02d}"
        performance_data = []
        for date in dates:
            performance = get_performance(trade_files, date, hour)
            performance_data.append(performance)
        _row_data = [hour_string] + performance_data
        csv_data.append(_row_data)

    bot_id = Config.BOT_ID
    file_csv = f"stats_per_hour-{ticker}-{bot_id}.csv"
    os.makedirs(Config.STATS_DIR, exist_ok=True)
    file_csv = os.path.join(Config.STATS_DIR, file_csv)
    with open(file_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
    print(f"Data successfully written to {file_csv}.")


if __name__ == "__main__":
    for ticker in ("btc", "eth", "xrp", "sol"):
        main(ticker)
