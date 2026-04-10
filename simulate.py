import argparse
import os
import json
from datetime import datetime, timedelta
from core.utilities import json_file_read
from core.trader import TradeStats
from core.config import Config


def get_trade_files(start_ts, end_ts, market_slug: str = None):
    trade_stats_new = TradeStats(start_ts=start_ts, end_ts=end_ts)
    trade_stats_old = TradeStats(
        start_ts=start_ts,
        end_ts=end_ts,
        trade_files_directory=os.path.join(
            Config.TRADE_RECORDS_ARCHIVE,
            Config.TRADE_RECORDS_PROCESSED_DIR
        )
    )
    trade_files = trade_stats_new.get_trade_files() + trade_stats_old.get_trade_files()
    if market_slug is not None:
        trade_files = list(filter(
            lambda x: market_slug in x["trade"].market_slug,
            trade_files
        ))
    return trade_files


def get_performance(
    market_slug,
    timestamp: int,
    num_stats_hours: int
):
    end_date = datetime.fromtimestamp(timestamp)
    end_ts = end_date.timestamp()
    start_date = end_date - timedelta(hours=num_stats_hours)
    start_ts = start_date.timestamp()

    trade_files = get_trade_files(start_ts, end_ts, market_slug)

    if not trade_files:
        return None

    record_count = 0
    wins = 0
    for trade_item in trade_files:
        trade = trade_item["trade"]
        record_count += 1
        if trade.won:
            wins += 1
    performance = wins / record_count if record_count > 0 else ""
    return performance


def check_performance(trade, config):
    timestamp = trade.timestamp
    date = datetime.fromtimestamp(timestamp)
    market_slug = trade.market_slug[:-11]
    record_count = config["bot_config"][market_slug]["record_count"]
    threshold_count = config["bot_config"][market_slug]["threshold_count"]
    threshold_hours = config["bot_config"][market_slug]["threshold_hours"]
    threshold_low = config["bot_config"][market_slug]["threshold_low"]
    threshold_high = config["bot_config"][market_slug]["threshold_high"]
    paper_trade = config["bot_config"][market_slug]["paper_trade"]

    if record_count < threshold_count:
        return
    if (record_count % 5) != 0:
        return

    performance = get_performance(market_slug, timestamp, threshold_hours)
    # print(f"{date}: paper_trade {paper_trade}, performance: {performance}, threshold_low {threshold_low}, {threshold_high}")
    if paper_trade and performance <= threshold_low:
        config["bot_config"][market_slug]["paper_trade"] = False
        print(
            f"live_trade turned ON for {market_slug}: {performance:.2f} vs {threshold_low:.2f}")
    elif not paper_trade and performance >= threshold_high:
        config["bot_config"][market_slug]["paper_trade"] = True
        print(
            f"live_trade turned OFF for {market_slug}: {performance:.2f} vs {threshold_high:.2f}")

    return


def main():
    parser = argparse.ArgumentParser(description="Simulation Tool")
    parser.add_argument("--simulation_config", type=str, required=True,
                        help="Simulation config JSON file")
    args = parser.parse_args()

    assert os.path.exists(args.simulation_config)
    config = json_file_read(args.simulation_config)

    start_ts = datetime.strptime(config["start_date"], "%Y-%m-%d").timestamp()
    end_ts = datetime.strptime(config["end_date"], "%Y-%m-%d").timestamp()

    trade_files = get_trade_files(start_ts, end_ts)
    start_date = datetime.fromtimestamp(trade_files[0]["timestamp"])
    end_date = datetime.fromtimestamp(trade_files[-1]["timestamp"])

    if config["current_balance"] is None:
        config["current_balance"] = config["initial_balance"]

    num_wins = 0
    num_trades = 0
    for trade_file in trade_files:
        trade = trade_file["trade"]
        timestamp = trade.timestamp
        market_slug = trade.market_slug[:-11]
        if market_slug not in config["bot_config"]:
            continue

        if "record_count" not in config["bot_config"][market_slug]:
            config["bot_config"][market_slug]["record_count"] = 0

        config["bot_config"][market_slug]["record_count"] += 1
        check_performance(trade, config)
        paper_trade = config["bot_config"][market_slug]["paper_trade"]

        if not paper_trade:
            num_trades += 1
            trade_value = trade.amount * trade.entry_price
            if trade.won:
                num_wins += 1
                outcome_text = "WON"
                config["current_balance"] += trade_value
            else:
                outcome_text = "LOST"
                config["current_balance"] -= trade_value
            current_balance = config["current_balance"]
            print(
                f"Trade {timestamp}: {outcome_text}: "
                f"current_balance: {current_balance}"
            )

    current_balance = config["current_balance"]
    performance = f"{(num_wins/num_trades)*100:.2f}%" if num_trades > 0 else "N/A"
    print(
        f"Final Outcome: performance {performance}, current_balance: {current_balance}")


if __name__ == "__main__":
    main()
