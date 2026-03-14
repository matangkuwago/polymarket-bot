import os
import json
from datetime import datetime, timedelta
from glob import glob
from tabulate import tabulate
from core.trader import Trade, LiveTrader
from core.config import Config
from core.utilities import Emailer


def format_table_title(title, format):
    if format == "html":
        return f"<br/><h4>{title}</h4>"

    return f"\n\n{table_title}:\n"


def tabulate_results(table_title: str, results: dict, format: str = "html"):
    data = []
    headers = ["Asset", "Count", "Wins", "%"]
    results_sorted = sorted(
        results.items(), key=lambda x: x[1]["percent"], reverse=True)
    percents = []
    for coin, result in results_sorted:
        count = result['record_count']
        wins = result['num_won']
        percent = f"{result['percent']*100:.2f}%"
        percents.append(result['percent']*100)
        data.append([coin, count, wins, percent])
    percent_average = f"{(sum(percents) / len(percents)):.2f}%" if percents else "N/A"
    data.append(["avg", "", "", percent_average])
    return f"{format_table_title(table_title, format)}" + tabulate(data, headers=headers, tablefmt=format)


def get_results(trade_files, timestamp_earliest: int = None):
    results = {}
    trader = LiveTrader()
    for file in trade_files:
        market_slug = os.path.basename(file).replace(".trade", "")
        coin = market_slug[:3]
        market_slug_prefix = market_slug[:-11]
        timestamp = int(market_slug[-10:])
        if timestamp_earliest and timestamp < timestamp_earliest:
            continue
        trade = Trade.load(
            market_slug, trade_files_directory=Config.TRADE_RECORDS_PROCESSED_DIR)

        if coin not in results:
            results[coin] = {
                "record_count": 0,
                "num_won": 0,
            }

        results[coin]["record_count"] += 1
        if trade.won:
            results[coin]["num_won"] += 1

    for coin in results:
        results[coin]["percent"] = float(
            results[coin]["num_won"]/results[coin]["record_count"])

    return results


def main():
    processed_dir = Config.TRADE_RECORDS_PROCESSED_DIR
    trade_files = glob(os.path.join(processed_dir, '*.trade'))
    trade_files.sort()

    if not trade_files:
        exit(0)

    email_lines = []
    email_lines += [tabulate_results("All", get_results(trade_files))]

    date_limit = datetime.now() - timedelta(hours=1)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("1H",
                                     get_results(trade_files, timestamp))]

    date_limit = datetime.now() - timedelta(hours=4)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("4H",
                                     get_results(trade_files, timestamp))]

    date_limit = datetime.now() - timedelta(hours=8)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("8H",
                                     get_results(trade_files, timestamp))]

    date_limit = datetime.now() - timedelta(hours=24)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("24H",
                                     get_results(trade_files, timestamp))]

    email_subject = f"polymarket_bot: stats | {int(datetime.now().timestamp())}"
    email_body = "".join(email_lines)

    Emailer.send_email(email_subject, email_body, email_body)


if __name__ == "__main__":
    main()
