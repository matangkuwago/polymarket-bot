import json
from datetime import datetime, timedelta
from tabulate import tabulate
from core.utilities import Emailer
from core.trader import TradeStats
from core.config import Config
from core.wallet import WalletManager


def _format_table_title(title, format):
    if format == "html":
        return f"<br/><h4>{title}</h4>"

    return f"\n\n{title}:\n"


def tabulate_wallet_balance(format: str = "html"):
    wallet_manager = WalletManager()

    table_title = "Wallet Balance"
    headers = ["Wallet", "Portfolio", "Balance", "Total"]
    processed_wallets = set()
    data = []
    line_border = ["-"*11]*4
    total_data = ["Total", 0, 0, 0]
    for wallet_id in wallet_manager.get_wallet_ids():
        wallet = WalletManager().get_wallet(wallet_id)
        wallet_address = wallet.funder_address
        if wallet_address not in processed_wallets:
            processed_wallets.add(wallet_address)
            portfolio_value = wallet.portfolio_value()
            total_data[1] += portfolio_value
            balance_value = wallet.available_balance()
            total_data[2] += balance_value
            total_value = portfolio_value + balance_value
            total_data[3] += total_value

            data.append([wallet_id, f"{portfolio_value:.2f}",
                        f"{balance_value:.2f}", f"{total_value: .2f}"])
            data.append(line_border)

    data.append([f"{x:.2f}" if type(x) == float else x for x in total_data])
    data.append(line_border)

    return (
        f"{_format_table_title(table_title, format)}" +
        tabulate(data, headers=headers, tablefmt=format)
    )


def _tabulate_results(bot_id: str, table_title: str, results: dict, format: str = "html"):
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
        paper_trade = Config.get_bot_market_setting(
            bot_id, market, "paper_trade"
        )
        count = result['record_count']
        wins = result['wins']
        percent = float(wins / count) if count > 0 else -1
        percent_text = f"{percent*100:.2f}%" if percent >= 0 else "N/A"
        count_total += count
        wins_total += wins
        live_text = " [x]" if not paper_trade else ""
        data.append(line_border)
        data.append([market[:3] + live_text, count, wins, percent_text])

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
                         matched_total,
                         matched_wins_total,
                         f"{100*matched_wins_total/matched_total:.2f}%"])
        data.append(line_border)

    return (
        f"{_format_table_title(table_title, format)}" +
        tabulate(data, headers=headers, tablefmt=format)
    )


def load_stats_hours():
    try:
        with open(Config.REPORT_CONFIG_FILE, 'r') as f:
            data = json.load(f)
        if not data or "stats_hours" not in data:
            return []
        return data["stats_hours"]
    except FileNotFoundError as e:
        return {}
    except json.JSONDecodeError:
        return {}


def main():
    trade_stats = TradeStats()
    if not trade_stats.trade_files:
        trade_stats.logger.info("No trade records found.")
        exit(0)

    # add wallet balance
    email_lines = [tabulate_wallet_balance()]

    bot_id = Config.BOT_ID
    hours = load_stats_hours()
    for hour in hours:
        date_limit = datetime.now() - timedelta(hours=hour)
        timestamp = date_limit.timestamp()
        data = trade_stats.get_statistics(start_ts=timestamp)
        email_lines += [_tabulate_results(bot_id, f"{hour}H", data)]

    subject = f"{bot_id}: polymarket_bot: stats | {int(datetime.now().timestamp())}"
    mail_content = "".join(email_lines)

    Emailer.send_email(subject, mail_content=mail_content,
                       mail_content_html=mail_content)


if __name__ == "__main__":
    main()
