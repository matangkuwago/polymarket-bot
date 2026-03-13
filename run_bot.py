import asyncio
import argparse
from core.bot import Polymarket5MinuteBot


parser = argparse.ArgumentParser(description="A simple Polymarket bot.")
parser.add_argument("--market_slug_prefix", type=str, required=True,
                    help="Polymarket 5-minute market slug prefix e.g. btc-updown-5m for BTC 5-minute market")
parser.add_argument("--binance_ticker", type=str, required=True,
                    help="The Binance ticker where the price will be compared e.g. BTCUSD")
parser.add_argument("--paper_trade", type=bool, required=True,
                    help="Paper trade option")

args = parser.parse_args()
btc_bot = Polymarket5MinuteBot(
    polymarket_slug_prefix=args.market_slug_prefix,
    binance_ticker=args.binance_ticker,
    paper_trade=args.paper_trade)
asyncio.run(btc_bot.run())
