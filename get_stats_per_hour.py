import csv
from datetime import datetime
from core.trader import TradeStats


def main():
    trade_stats_data = {}
    trade_stats = TradeStats()
    trade_files = trade_stats.get_trade_files()

    if not trade_files:
        print(f"No data to process.")
        exit(0)

    trade_files = sorted(
        trade_files, key=lambda x: x["timestamp"])

    record_count = 0
    wins = 0
    matched = 0
    matched_wins = 0
    for trade_item in trade_files:
        timestamp = trade_item["timestamp"]
        trade = trade_item["trade"]
        hour = datetime.fromtimestamp(timestamp).hour
        if hour not in trade_stats_data:
            trade_stats_data[hour] = {
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
        trade_stats_data[hour]["record_count"] = record_count
        trade_stats_data[hour]["wins"] = wins
        trade_stats_data[hour]["matched"] = matched
        trade_stats_data[hour]["matched_wins"] = matched_wins

    headers = ["time", "performance (all)", "performance (matched)",
               "record_count", "wins", "matched", "matched_wins"]
    csv_data = [headers,]

    for hour in sorted(trade_stats_data.keys()):
        record_count = trade_stats_data[hour]["record_count"]
        wins = trade_stats_data[hour]["wins"]
        matched = trade_stats_data[hour]["matched"]
        matched_wins = trade_stats_data[hour]["matched_wins"]
        hour_string = f" {hour:02d}"
        performance_all = f"{float(wins/record_count)*100:.2f}%" if record_count > 0 else "N/A"
        performance_matched = f"{float(matched_wins/matched)*100:.2f}%" if matched > 0 else "N/A"
        _row_data = [hour_string, performance_all, performance_matched,
                     record_count, wins, matched, matched_wins]
        csv_data.append(_row_data)

    file_csv = "stats_per_hour.csv"
    with open(file_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
    print(f"Data successfully written to {file_csv}.")


if __name__ == "__main__":
    main()
