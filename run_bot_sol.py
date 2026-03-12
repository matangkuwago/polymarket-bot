import asyncio
from core.bot import Polymarket5MinuteBot


sol_bot = Polymarket5MinuteBot("sol-updown-5m", "SOLUSDT")
asyncio.run(sol_bot.run())
