from datetime import datetime, timedelta
from tabulate import tabulate
from core.utilities import Emailer
from core.trader import TradeStats


def _format_table_title(title, format):
    if format == "html":
        return f"<br/><h4>{title}</h4>"

    return f"\n\n{title}:\n"


def _tabulate_results(table_title: str, results: dict, format: str = "html"):
    data = []
    headers = ["Market", "Count", "Wins", "%"]
    results_sorted = sorted(
        results.items(), key=lambda x: float(x[1]["wins"]/x[1]["record_count"]), reverse=True)

    count_total = 0
    wins_total = 0
    matched_total = 0
    matched_wins_total = 0
    line_border = ["-"*11]*4
    for market, result in results_sorted:
        count = result['record_count']
        wins = result['wins']
        percent = float(wins / count) if count > 0 else -1
        percent_text = f"{percent*100:.2f}%" if percent >= 0 else "N/A"
        count_total += count
        wins_total += wins
        data.append(line_border)
        data.append([market[:3], count, wins, percent_text])

        if count > 0 and result['matched'] > 0:
            matched = result['matched']
            matched_wins = result['matched_wins']
            matched_total += matched
            matched_wins_total += matched_wins
            matched_wins_percent = float(matched_wins / matched)
            data.append(["matched", matched, matched_wins,
                        f"{matched_wins_percent*100:.2f}%"])

    if count_total > 0:
        data.append(line_border)
        data.append(["total", count_total, wins_total,
                    f"{100*wins_total/count_total:.2f}%"])
        if matched_total > 0:
            data.append(["matched",
                         matched_wins_total,
                         matched_total,
                         f"{100*matched_wins_total/matched_total:.2f}%"])
        data.append(line_border)

    return (
        f"{_format_table_title(table_title, format)}" +
        tabulate(data, headers=headers, tablefmt=format)
    )


def main():

    trade_stats = TradeStats()
    if not trade_stats.trade_files:
        trade_stats.logger.info("No trade records found.")
        exit(0)

    email_lines = []
    email_lines += [_tabulate_results("All", trade_stats.get_statistics())]

    hours = [1, 4, 8, 24]
    for hour in hours:
        date_limit = datetime.now() - timedelta(hours=hour)
        timestamp = date_limit.timestamp()
        data = trade_stats.get_statistics(start_ts=timestamp)
        email_lines += [_tabulate_results(f"{hour}H", data)]

    subject = f"polymarket_bot: stats | {int(datetime.now().timestamp())}"
    mail_content = "".join(email_lines)

    Emailer.send_email(subject, mail_content=mail_content,
                       mail_content_html=mail_content)


if __name__ == "__main__":
    main()
