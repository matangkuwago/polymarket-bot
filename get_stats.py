from datetime import datetime, timedelta
from tabulate import tabulate
from core.trader import TradeStats
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
    count_total = 0
    win_total = 0
    num_unmatched_total = 0
    num_unmatched_wins_total = 0
    for coin, result in results_sorted:
        count = result['record_count']
        count_total += count
        wins = result['num_won']
        win_total += wins
        num_unmatched_total += int(result['num_unmatched'])
        num_unmatched_wins_total += int(result['num_unmatched_wins'])
        percent = f"{result['percent']*100:.2f}%"
        percents.append(result['percent']*100)
        data.append([coin, count, wins, percent])
    percent_average = f"{(sum(percents) / len(percents)):.2f}%" if percents else "N/A"
    data.append(["-"*11, "-"*11, "-"*11, "-"*11])
    data.append(["", count_total, win_total, percent_average])

    if num_unmatched_total > 0:
        unmatched_percent_average = f"{(num_unmatched_wins_total / num_unmatched_total)*100:.2f}%"
        data.append(["-"*11, "-"*11, "-"*11, "-"*11])
        data.append(["x", num_unmatched_total,
                    num_unmatched_wins_total, unmatched_percent_average])

    return f"{format_table_title(table_title, format)}" + tabulate(data, headers=headers, tablefmt=format)


def main():

    trade_stats = TradeStats()
    if not trade_stats.trade_files:
        exit(0)

    email_lines = []
    email_lines += [tabulate_results("All",
                                     trade_stats.get_statistics())]

    date_limit = datetime.now() - timedelta(hours=1)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("1H",
                                     trade_stats.get_statistics(timestamp))]

    date_limit = datetime.now() - timedelta(hours=4)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("4H",
                                     trade_stats.get_statistics(timestamp))]

    date_limit = datetime.now() - timedelta(hours=8)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("8H",
                                     trade_stats.get_statistics(timestamp))]

    date_limit = datetime.now() - timedelta(hours=24)
    timestamp = date_limit.timestamp()
    email_lines += [tabulate_results("24H",
                                     trade_stats.get_statistics(timestamp))]

    email_subject = f"polymarket_bot: stats | {int(datetime.now().timestamp())}"
    email_body = "".join(email_lines)

    Emailer.send_email(email_subject, email_body, email_body)


if __name__ == "__main__":
    main()
