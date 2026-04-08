import os
from glob import glob
from core.config import Config
from core.polymarket import PolymarketClient
from core.trader import Trade, LiveTrader
from core.wallet import WalletManager
from core.utilities import Emailer


def mark_trade_as_processed(trade):
    os.makedirs(Config.TRADE_RECORDS_PROCESSED_DIR, exist_ok=True)
    source_file = f"{Config.TRADE_RECORDS_DIR}/{trade.market_slug}.trade"
    target_file = f"{Config.TRADE_RECORDS_PROCESSED_DIR}/{trade.market_slug}.trade"
    os.rename(source_file, target_file)
    print(
        f"Trade record has been moved "
        f"from {source_file} to {target_file}."
    )


def main():
    unprocessed_dir = Config.TRADE_RECORDS_DIR
    trade_files = glob(os.path.join(unprocessed_dir, '*.trade'))
    trade_files.sort()

    num_records_processed = 0
    bot_id = Config.BOT_ID
    wallet = WalletManager().get_wallet(bot_id)
    trader = LiveTrader(wallet)
    for file in trade_files:
        market_slug = os.path.basename(file).replace(".trade", "")
        market_slug_prefix = market_slug[:-11]
        timestamp = int(market_slug[-10:])

        client = PolymarketClient(
            market_slug_prefix=market_slug_prefix)
        market = client.get_market(timestamp)

        if not market.resolved:
            continue

        trade = Trade.load(market.slug)
        if not trade:
            continue

        trade.outcome = market.outcome
        trade.won = True if trade.direction == market.outcome else False
        won_text = "WON" if trade.won else "LOST"

        order = trader.get_order(trade.order_id)
        if order:
            order_email_text = (
                f"\n"
                f"Order Record:\n"
                f"order.status: {order['status']}\n"
                f"order.price: {order['price']}\n"
                f"order.original_size: {order['original_size']}\n"
                f"order.size_matched: {order['size_matched']}\n"
                f"order.side: {order['side']}\n"
            )
            trade.order_status = order['status']
            if trade.order_status == "MATCHED":
                pass
        else:
            order_email_text = (
                f"\n"
                f"Order Record:\n"
                f"Unable to get order record from Polymarket API.\n"
            )

        trade.save()

        bot_id = Config.BOT_ID
        subject = f"{bot_id}: polymarket_bot: result: {won_text} | {trade.market_slug}"
        mail_content = (
            f"Trade Record:\n"
            f"trade.timestamp: {trade.timestamp}\n"
            f"trade.order_id: {trade.order_id}\n"
            f"trade.direction: {trade.direction}\n"
            f"trade.entry_price: {trade.entry_price}\n"
            f"trade.amount: {trade.amount}\n"
            f"trade.outcome: {trade.outcome}\n"
            f"trade.won: {trade.won}\n"
            f"{order_email_text}"
        )

        if Config.EMAIL_UPDATE_RECORDS_NOTIFICATION and order and order['status'] != "CANCELED":
            Emailer.send_email(subject=subject, mail_content=mail_content)

        print(subject)

        mark_trade_as_processed(trade)
        num_records_processed += 1
        if num_records_processed >= Config.TRADE_MAX_RECORDS_UPDATE:
            break


if __name__ == "__main__":
    main()
