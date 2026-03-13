import os
import json
from glob import glob
from core.trader import Trade, LiveTrader
from core.config import Config


processed_dir = Config.TRADE_RECORDS_PROCESSED_DIR
trade_files = glob(os.path.join(processed_dir, '*.trade'))
trade_files.sort()


trader = LiveTrader()
results = {}
for file in trade_files:
    market_slug = os.path.basename(file).replace(".trade", "")
    coin = market_slug[:3]
    market_slug_prefix = market_slug[:-11]
    timestamp = int(market_slug[-10:])
    trade = Trade.load(market_slug, trade_files_directory=processed_dir)

    if coin not in results:
        results[coin] = {
            "record_count": 0,
            "num_won": 0,
        }

    results[coin]["record_count"] += 1
    if trade.won:
        results[coin]["num_won"] += 1

for coin in results:
    results[coin]["percent"] = float(
        results[coin]["num_won"]/results[coin]["record_count"])

pretty_json_string = json.dumps(results, indent=4)
print(pretty_json_string)
