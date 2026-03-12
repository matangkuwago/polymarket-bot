import asyncio
from core.bot import Polymarket5MinuteBot


btc_bot = Polymarket5MinuteBot("btc-updown-5m", "BTCUSDT")
asyncio.run(btc_bot.run())
