from core.trader import LiveTrader
from core.polymarket import PolymarketClient

timestamp = 1772806800
client = PolymarketClient()
market = client.get_market(timestamp)
if not market.resolved:

    trader = LiveTrader()
    usdc_balance = trader.get_usdc_balance()
    print(f"Current balance is {usdc_balance}")

    trader.place_limit_order(
        market=market,
        direction="up",
        entry_price=0.4,
        amount=5.0
    )