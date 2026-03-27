import asyncio
import requests
import json
from datetime import datetime
from core.config import Config
from core.trader import LiveTrader
from core.utilities import Emailer, setup_logging, load_daily_balance, save_daily_balance


async def main():
    logger = setup_logging("update_daily_target.log", "update_daily_target")
    user_address = Config.FUNDER_ADDRESS
    portfolio_url = f"https://data-api.polymarket.com/value?user={user_address}"
    response = requests.get(url=portfolio_url)
    portfolio_value = 0
    if response and response.status_code == 200:
        data = response.json()
        portfolio_value = float(data[0]["value"])

    live_trader = LiveTrader()
    usdc_balance = live_trader.get_usdc_balance()
    total_value = portfolio_value + usdc_balance

    date_today = datetime.today().strftime('%Y-%m-%d')
    daily_balance_json = load_daily_balance()
    if date_today not in daily_balance_json:
        daily_balance_json[date_today] = {
            "start_balance": total_value,
            "current_balance": total_value,
            "goal_achieved": False
        }
    else:
        daily_balance_json[date_today]["current_balance"] = total_value
    goal_achieved = daily_balance_json[date_today]["goal_achieved"]

    percent_target = Config.DAILY_BALANCE_TARGET_PERCENT
    start_balance = daily_balance_json[date_today]["start_balance"]
    current_balance = daily_balance_json[date_today]["current_balance"]
    profit = current_balance - start_balance
    profit_percent = profit / start_balance
    timestamp = datetime.now().timestamp()
    subject = ""
    message = (
        f"\n"
        f"start_balance: {start_balance} \n"
        f"current_balance: {current_balance} \n"
        f"percent_target: {percent_target} \n"
        f"profit_percent: {profit_percent} \n"
    )
    if profit_percent > percent_target and not goal_achieved:
        subject = f"polymarket_bot: SET daily profit target achieved | {timestamp}"
        daily_balance_json[date_today]["goal_achieved"] = True
        Emailer.send_email(subject=subject, mail_content=message)
    elif profit_percent <= percent_target and goal_achieved:
        subject = f"polymarket_bot: REVERT daily profit target achieved | {timestamp}"
        daily_balance_json[date_today]["goal_achieved"] = False
        Emailer.send_email(subject=subject, mail_content=message)
    else:
        subject = "No change in goal_achieved state."

    if subject:
        logger.info(subject)
    if message:
        logger.info(message)

    save_daily_balance(daily_balance_json)

asyncio.run(main())
