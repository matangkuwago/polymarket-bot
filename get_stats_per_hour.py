import csv
from datetime import datetime
from tabulate import tabulate
from core.trader import TradeStats
from core.utilities import Emailer, are_bots_on_schedule


def main():
    trade_stats_data = {}
    trade_stats = TradeStats()
    trade_files = trade_stats.get_trade_files()

    if not trade_files:
        print(f"No data to process.")
        exit(0)

    if not are_bots_on_schedule():
        trade_stats.logger.info(
            "Bots are not running so no stats will be sent.")
        exit(0)

    trade_files = sorted(
        trade_files, key=lambda x: x["timestamp"], reverse=True)
    for trade_item in trade_files:
        timestamp = trade_item["timestamp"]
        trade = trade_item["trade"]
        market_slug = trade.market_slug[:-11]
        date_object = datetime.fromtimestamp(timestamp)
        hour = date_object.hour
        date_string = date_object.strftime("%Y-%m-%d")
        if date_string not in trade_stats_data:
            trade_stats_data[date_string] = {x: {} for x in range(0, hour+1)}
        for _hour in trade_stats_data[date_string].keys():
            if _hour >= hour:
                if market_slug not in trade_stats_data[date_string][_hour]:
                    trade_stats_data[date_string][_hour][market_slug] = {
                        "record_count": 0,
                        "wins": 0,
                    }
                trade_stats_data[date_string][_hour][market_slug]["record_count"] += 1
                if trade.won:
                    trade_stats_data[date_string][_hour][market_slug]["wins"] += 1

    headers = ["time", "btc", "eth", "xrp", "sol"]
    line_border = ["-"*21]*5
    csv_data = [headers,]
    table_data = []
    dates = list(trade_stats_data.keys())
    dates.sort()
    for _date in dates:
        for _hour in trade_stats_data[_date]:
            if not trade_stats_data[_date][_hour]:
                continue
            date_string = f"{_date} {_hour:02d}"
            markets = ["btc", "eth", "xrp", "sol"]
            _row_data = []
            for _market in markets:
                market_slug = f"{_market}-updown-5m"
                if market_slug in trade_stats_data[_date][_hour]:
                    count = trade_stats_data[_date][_hour][market_slug]["record_count"]
                    wins = trade_stats_data[_date][_hour][market_slug]["wins"]
                    percent_text = f"{float(wins / count) * 100:.2f}%"
                    _row_data.append(percent_text)
                else:
                    _row_data.append("")
            if _row_data:
                table_data.append([date_string] + _row_data)
                csv_data.append([date_string] + _row_data)
                table_data.append(line_border)
    table_text = tabulate(table_data, headers=headers, tablefmt="html")
    subject = f"polymarket_bot: per hour | {int(datetime.now().timestamp())}"
    mail_content = "".join(table_text)
    Emailer.send_email(subject, mail_content=mail_content,
                       mail_content_html=mail_content)

    file_csv = "stats_per_hour.csv"
    # Open the file and write the data
    with open(file_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
    print(f"Data successfully written to {file_csv}.")


if __name__ == "__main__":
    main()
