import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from core.polymarket import PolymarketClient


current_market = datetime.now().replace(
    minute=(datetime.now().minute - (datetime.now().minute % 5)), 
    second=0, 
    microsecond=0)

# get last 5 market information
client = PolymarketClient()
market_interval = 5 # 5 minutes
for i in range(5):
    timestamp = int(current_market.timestamp())
    market = client.get_market(timestamp)
    et_aware_dt = current_market.astimezone(ZoneInfo('America/New_York'))
    print("-----------------")
    print(f"timestamp: {timestamp}")
    print(f"et_aware_dt: {et_aware_dt}")
    print(f"market: {market}")
    print(market)

    current_market = current_market - timedelta(minutes=market_interval)
