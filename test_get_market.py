import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from core.polymarket import PolymarketClient


current_market = datetime.now().replace(
    minute=(datetime.now().minute - (datetime.now().minute % 5)), 
    second=0, 
    microsecond=0)

# get last 30 market information
client = PolymarketClient()
market_interval = 5 # 5 minutes
results = []
for i in range(30):
    timestamp = int(current_market.timestamp())
    market = client.get_market(timestamp)
    et_aware_dt = current_market.astimezone(ZoneInfo('America/New_York'))
    price_to_beat = f"{market.price_to_beat:.2f}" if market.price_to_beat is not None else ""
    resolved = market.resolved
    outcome = market.outcome
    row = [et_aware_dt, price_to_beat, timestamp, resolved, outcome]
    results.insert(0, row)
    current_market = current_market - timedelta(minutes=market_interval)

for item in results:
    print(f"{item[0]}, {item[1]}, {item[2]}, {item[3]}, {item[4]}")
