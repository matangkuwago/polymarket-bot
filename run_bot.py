import asyncio
import argparse
from core.bot import Polymarket5MinuteBot


parser = argparse.ArgumentParser(description="A simple Polymarket bot.")
parser.add_argument("--market_slug_prefix", type=str, required=True,
                    help="Polymarket 5-minute market slug prefix e.g. btc-updown-5m for BTC 5-minute market")
args = parser.parse_args()

bot = Polymarket5MinuteBot(
    polymarket_slug_prefix=args.market_slug_prefix,
    binance_ticker=args.binance_ticker
)
asyncio.run(bot.run())
