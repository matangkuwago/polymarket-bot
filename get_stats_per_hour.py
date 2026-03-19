import json
from datetime import datetime
from tabulate import tabulate
from core.trader import TradeStats
from core.utilities import Emailer


def main():
    trade_stats_data = {}
    trade_stats = TradeStats()
    trade_files = trade_stats.get_trade_files()
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
        else:
            new_value = {x: {} for x in range(
                0, hour+1)}
            trade_stats_data[date_string] = new_value | trade_stats_data[date_string]
        for _hour in trade_stats_data[date_string].keys():
            if _hour >= hour:
                if market_slug not in trade_stats_data[date_string][_hour]:
                    trade_stats_data[date_string][_hour][market_slug] = {
                        "record_count": 0,
                        "num_won": 0,
                    }
                trade_stats_data[date_string][_hour][market_slug]["record_count"] += 1
                if trade.won:
                    trade_stats_data[date_string][_hour][market_slug]["num_won"] += 1

    headers = ["time", "btc", "eth", "xrp", "sol"]
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
                count = trade_stats_data[_date][_hour][market_slug]["record_count"]
                wins = trade_stats_data[_date][_hour][market_slug]["num_won"]
                if not count:
                    continue
                percent = f"{float(wins / count) * 100:.2f}%"
                _row_data.append(percent)
            if _row_data:
                table_data.append([date_string] + _row_data)
    table_text = tabulate(table_data, headers=headers, tablefmt="html")
    subject = f"polymarket_bot: stats per hour | {int(datetime.now().timestamp())}"
    mail_content = "".join(table_text)
    Emailer.send_email(subject, mail_content=mail_content,
                       mail_content_html=mail_content)


if __name__ == "__main__":
    main()
