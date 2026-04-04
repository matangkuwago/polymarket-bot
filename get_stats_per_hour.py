import csv
from datetime import datetime
from core.trader import TradeStats


def main(ticker: str):
    trade_stats_data = {}
    trade_stats = TradeStats()
    trade_files = trade_stats.get_trade_files()
    trade_files = list(filter(
        lambda x: ticker in x["trade"].market_slug,
        trade_files
    ))

    if not trade_files:
        print(f"No data to process.")
        exit(0)

    trade_files = sorted(
        trade_files, key=lambda x: x["timestamp"])

    previous_trade_date_text = ""
    for trade_item in trade_files:
        timestamp = trade_item["timestamp"]
        trade = trade_item["trade"]
        trade_date = datetime.fromtimestamp(timestamp)
        trade_date_text = trade_date.strftime("%Y-%m-%d")
        if previous_trade_date_text != trade_date_text:
            record_count = 0
            wins = 0
            matched = 0
            matched_wins = 0
        hour = trade_date.hour
        if trade_date_text not in trade_stats_data:
            trade_stats_data[trade_date_text] = {}
            for _hour in range(0, 24):
                trade_stats_data[trade_date_text][_hour] = {
                    "record_count": 0,
                    "wins": 0,
                    "matched": 0,
                    "matched_wins": 0,
                }
        record_count += 1
        if trade.won:
            wins += 1
        if trade.order_status == "MATCHED":
            matched += 1
            if trade.won:
                matched_wins += 1
        trade_stats_data[trade_date_text][hour]["record_count"] = record_count
        trade_stats_data[trade_date_text][hour]["wins"] = wins
        trade_stats_data[trade_date_text][hour]["matched"] = matched
        trade_stats_data[trade_date_text][hour]["matched_wins"] = matched_wins
        previous_trade_date_text = trade_date_text

    dates = list(sorted(trade_stats_data.keys()))
    headers = ["time"] + dates
    csv_data = [headers]

    for hour in range(0, 24):
        hour_string = f" {hour:02d}"
        performance_data = []
        for date in dates:
            record_count = trade_stats_data[date][hour]["record_count"]
            wins = trade_stats_data[date][hour]["wins"]
            performance = f"{(wins / record_count)*100:.2f}%" if record_count > 0 else ""
            performance_data.append(performance)
        _row_data = [hour_string] + performance_data
        csv_data.append(_row_data)

    file_csv = f"stats_per_hour-{ticker}.csv"
    with open(file_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
    print(f"Data successfully written to {file_csv}.")


if __name__ == "__main__":
    for ticker in ("btc", "eth", "xrp", "sol"):
        main(ticker)
