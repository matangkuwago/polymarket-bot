# DEPRECATED: Use polymarket_algo.* packages instead. This file exists for backward compatibility.
"""Trading execution — paper and live modes."""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from glob import glob
from tabulate import tabulate
from typing import cast
from core.config import Config
from core.polymarket import Market, PolymarketClient
from core.utilities import Emailer, setup_logging
from py_clob_client.clob_types import OrderArgs, OrderType, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY


@dataclass
class Trade:
    """Record of a trade (paper or live) with full history."""

    # === CORE FIELDS ===
    order_id: str  # Order ID from exchange (live) or random str (paper trade)
    timestamp: int  # market timestamp (unix seconds)
    market_slug: str  # e.g., "btc-updown-5m-1771051500"
    direction: str  # "up" or "down" - your bet direction
    amount: float  # your bet size in USD (after any partial fill)
    entry_price: float  # displayed market price when you decided to bet
    paper_trade: bool  # True = simulation, False = live trade
    executed_at: int | None = None  # when you placed your bet (unix ms)
    fee_rate_bps: int = 0  # base fee in basis points (e.g., 1000)
    fee_pct: float = 0.0  # actual fee percentage at execution price

    # === RESOLUTION FIELDS ===
    outcome: str | None = None  # "up" or "down" after market closes
    pnl: float = 0.0  # net profit/loss after fees
    settled_at: int | None = None  # when trade was settled (unix ms)
    won: bool | None = None  # True if direction == outcome

    # === ORDER STATUS (live trading) ===
    order_status: str = "pending"  # pending, submitted, filled, cancelled, failed

    # Settlement status tracking
    settlement_status: str = "pending"  # "pending", "settled", or "force_exit"
    # "insufficient_bankroll" or "shutdown" (only when force_exit)
    force_exit_reason: str | None = None

    def save(self, save_dir=Config.TRADE_RECORDS_DIR):
        os.makedirs(save_dir, exist_ok=True)
        filepath = f"{save_dir}/{self.market_slug}.trade"
        """Saves the dataclass instance to a JSON file."""
        # Use asdict() to convert the dataclass instance to a dictionary
        data = asdict(self)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)

            logger = logging.getLogger(Config.LOGGER_NAME)
            logger.info(
                f"Order for market {self.market_slug} successfully saved to {filepath}.")
        except IOError as e:
            logger.error(
                f"Error saving order for market {self.market_slug} to {filepath}: {e}")

    @classmethod
    def load(cls, market_slug: str, trade_files_directory=Config.TRADE_RECORDS_DIR):
        """Loads a dataclass instance from a JSON file."""
        filepath = f"{trade_files_directory}/{market_slug}.trade"
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            # Unpack the dictionary to create a new instance of the class
            return cls(**data)
        except FileNotFoundError:
            logger = logging.getLogger(Config.LOGGER_NAME)
            logger.info(
                f"Error: Order for {market_slug} file not found at {filepath}!")
            return None
        except json.JSONDecodeError:
            logger = logging.getLogger(Config.LOGGER_NAME)
            logger.error(
                f"Error decoding Order for {market_slug} from file at {filepath}!")
            return None


class LiveTrader:
    """Live trading via Polymarket CLOB API.

    Supports:
    - EOA/MetaMask wallets (signature_type=0, default)
    - Magic/proxy wallets (signature_type=1, requires funder address)
    - FOK (Fill-Or-Kill) market orders for immediate execution
    - Order status tracking and confirmation
    """

    # Minimum order size
    MIN_ORDER_SIZE = 5.0

    def __init__(self, market_cache=None, logger=None):
        """Initialize live trader.

        Args:
            market_cache: Optional MarketDataCache for faster orderbook lookups
        """
        if not Config.PRIVATE_KEY:
            raise ValueError("PRIVATE_KEY not set in .env")

        # Validate proxy wallet config
        if Config.SIGNATURE_TYPE == 1 and not Config.FUNDER_ADDRESS:
            raise ValueError(
                "FUNDER_ADDRESS required for proxy wallet (SIGNATURE_TYPE=1)")

        self._market_cache = market_cache
        self.logger = (logging.getLogger(Config.LOGGER_NAME)
                       if logger is None else logger)

        self._init_client()

    def _init_client(self):
        """Initialize py-clob-client with wallet credentials."""
        try:
            from py_clob_client.client import ClobClient

            if Config.SIGNATURE_TYPE == 1 or Config.SIGNATURE_TYPE == 2:
                if not Config.FUNDER_ADDRESS:
                    raise ValueError(
                        "FUNDER_ADDRESS required when SIGNATURE_TYPE=1 or 2")
                self.logger.info(
                    f"[LiveTrader] Using proxy wallet with funder: {Config.FUNDER_ADDRESS[:10]}...")
                self.client = ClobClient(
                    host=Config.CLOB_API,
                    key=Config.PRIVATE_KEY,
                    chain_id=Config.CHAIN_ID,
                    signature_type=Config.SIGNATURE_TYPE,
                    funder=Config.FUNDER_ADDRESS,
                )
            else:
                self.client = ClobClient(
                    host=Config.CLOB_API,
                    key=Config.PRIVATE_KEY,
                    chain_id=Config.CHAIN_ID,
                )

            # Derive API credentials
            creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(creds)

            wallet_type = "EOA" if Config.SIGNATURE_TYPE == 0 else "proxy"
            self.logger.info(
                f"[LiveTrader] Live trading client initialized ({wallet_type} wallet)")

        except ImportError:
            raise ImportError(
                "py-clob-client not installed. Run: pip install py-clob-client")
        except Exception as e:
            raise RuntimeError(f"Failed to init trading client: {e}")

    def _validate_order(self, market: Market, direction: str, entry_price, amount: float) -> tuple[bool, str]:
        """Validate order parameters before submission.

        Returns:
            (is_valid, error_message)
        """
        # Check minimum order size
        if amount < self.MIN_ORDER_SIZE:
            return (
                False,
                f"Order size ${amount:.2f} below minimum ${self.MIN_ORDER_SIZE:.2f}.",
            )

        if entry_price <= 0:
            return (
                False,
                f"Entry price ${entry_price:.2f} should be greater than zero.",
            )

        # Check token ID exists
        token_id = market.up_token_id if direction == "up" else market.down_token_id
        if not token_id:
            return False, f"No token ID for {direction} side"

        # Check market is accepting orders
        if not market.accepting_orders:
            return False, f"Market {market.slug} not accepting orders"

        # Check market is not closed
        if market.closed:
            return False, f"Market {market.slug} is closed"

        return True, ""

    def _get_order_status(self, order_id: str, max_attempts: int = 5, poll_interval: float = 0.5) -> dict:
        """Poll for order status until filled or timeout.

        Args:
            order_id: Order ID to check
            max_attempts: Maximum polling attempts
            poll_interval: Seconds between polls

        Returns:
            Order status dict with keys: status, filled_size, avg_price, etc.
        """
        for attempt in range(max_attempts):
            try:
                order = self.client.get_order(order_id)
                status = order.get("status", "unknown")

                # FOK orders should be immediately filled or cancelled
                if status in ("FILLED", "MATCHED"):
                    return {
                        "status": "filled",
                        "filled_size": float(order.get("size_matched", order.get("size", 0))),
                        "avg_price": float(order.get("price", 0)),
                        "order": order,
                    }
                elif status in ("CANCELED", "CANCELLED", "EXPIRED"):
                    return {
                        "status": "cancelled",
                        "filled_size": 0,
                        "avg_price": 0,
                        "order": order,
                    }
                elif status == "LIVE":
                    # FOK should not rest on book, but check anyway
                    time.sleep(poll_interval)
                    continue
                else:
                    # Unknown status, keep polling
                    time.sleep(poll_interval)

            except Exception as e:
                self.logger.info(
                    f"[LiveTrader] Error polling order {order_id}: {e}")
                time.sleep(poll_interval)

        # Timeout - return unknown status
        return {
            "status": "unknown",
            "filled_size": 0,
            "avg_price": 0,
            "order": None,
        }

    def get_usdc_balance(self):
        balance = 0
        collateral = self.client.get_balance_allowance(
            params=BalanceAllowanceParams(
                asset_type=AssetType.COLLATERAL, signature_type=Config.SIGNATURE_TYPE)
        )

        if collateral and 'balance' in collateral:
            balance = float(collateral['balance']) / Config.USDC_TICK_SIZE

        return balance

    def get_order(self, order_id: str):
        return self.client.get_order(order_id)

    def place_limit_order(
        self,
        market: Market,
        direction: str,
        entry_price: float,
        amount: float,
        paper_trade: bool
    ) -> Trade | None:
        """Place a live bet using FOK (Fill-Or-Kill) market order.

        FOK orders fill immediately at the best available price or are cancelled.
        This is ideal for copy trading where speed matters.

        Returns None if order is rejected (validation failed, market closed, etc.)
        """
        # Validate order parameters
        is_valid, error_msg = self._validate_order(
            market, direction, entry_price, amount)
        if not is_valid:
            self.logger.info(f"[LiveTrader] Order rejected: {error_msg}")
            return None

        token_id = market.up_token_id if direction == "up" else market.down_token_id

        executed_at = int(time.time() * 1000)  # milliseconds
        order_id = None
        order_status = "pending"

        # Get fee rate from market
        fee_rate_bps = market.taker_fee_bps if hasattr(
            market, "taker_fee_bps") else 1000
        fee_pct = PolymarketClient.calculate_fee(entry_price, fee_rate_bps)

        try:
            if not token_id:
                raise ValueError(f"No token ID for {direction} side")

            # Create GTC limit order
            market_order = OrderArgs(
                token_id=token_id,
                price=entry_price,
                size=amount,
                side=BUY,
                expiration=(market.timestamp+Config.TRADE_ORDER_EXPIRATION)
            )

            # Sign and submit the order
            signed_order = self.client.create_order(market_order)
            if paper_trade:
                order_id = os.urandom(15).hex()
            else:
                response = self.client.post_order(signed_order, OrderType.GTD)
                order_id = response.get(
                    "orderID", response.get("id", "unknown"))

                if Config.EMAIL_LIMIT_ORDER_INFO:
                    # send notification
                    usdc_balance = self.get_usdc_balance()
                    subject = f"polymarket_bot: Order created successfully for market {market.slug}"
                    mail_content = f"Order ID: {order_id}: https://polymarket.com/event/{market.slug}"
                    mail_content += f"\nBalance: {usdc_balance}"
                    Emailer.send_email(
                        subject=subject, mail_content=mail_content)

            order_status = "submitted"

            # Log limit order
            paper_trade_text = "[PAPER TRADE]" if paper_trade else ""
            self.logger.info(
                f"[LiveTrader]{paper_trade_text} Limit Order placed ${amount:.2f} on {direction.upper()} @ price {entry_price:.2f} "
                f"| {market.title} | order={order_id} (GTC)"
            )

        except Exception as e:
            self.logger.info(f"[LiveTrader] Order failed: {e}")
            order_id = f"FAILED:{e}"
            order_status = "failed"

        return Trade(
            order_id=order_id,
            timestamp=market.timestamp,
            market_slug=market.slug,
            direction=direction,
            amount=amount,
            entry_price=entry_price,
            paper_trade=paper_trade,
            executed_at=executed_at,
            fee_rate_bps=fee_rate_bps,
            fee_pct=fee_pct,
            order_status=order_status,
        )


class TradeStats:

    def __init__(self, trade_files_directory: str = Config.TRADE_RECORDS_PROCESSED_DIR):
        self.trade_files_directory = trade_files_directory
        self.trade_files = []
        self.logger = setup_logging(
            log_file="trade_stats.log",
            logger_name="TradeStats"
        )

        trade_files = glob(os.path.join(self.trade_files_directory, '*.trade'))
        trade_files.sort()
        for file in trade_files:
            market_slug = os.path.basename(file).replace(".trade", "")
            timestamp = int(market_slug[-10:])
            trade = Trade.load(
                market_slug, trade_files_directory=self.trade_files_directory)
            if not trade:
                continue
            self.trade_files.append({"timestamp": timestamp, "trade": trade})

    def get_trade_files(self):
        return self.trade_files

    def get_statistics(self, timestamp_earliest: int = None):
        trade_stats = {}
        for trade_item in self.trade_files:
            timestamp = trade_item["timestamp"]
            if timestamp_earliest and timestamp < timestamp_earliest:
                continue
            trade = trade_item["trade"]
            market_slug = trade.market_slug[:-11]
            if market_slug not in trade_stats:
                trade_stats[market_slug] = {
                    "record_count": 0,
                    "num_won": 0,
                    "num_unmatched": 0,
                    "num_unmatched_wins": 0,
                }

            trade_stats[market_slug]["record_count"] += 1
            if not trade.paper_trade and trade.order_status != "MATCHED":
                trade_stats[market_slug]["num_unmatched"] += 1
                if trade.won:
                    trade_stats[market_slug]["num_unmatched_wins"] += 1
            if trade.won:
                trade_stats[market_slug]["num_won"] += 1

        for market_slug in trade_stats:
            trade_stats[market_slug]["percent"] = float(
                trade_stats[market_slug]["num_won"] /
                trade_stats[market_slug]["record_count"]
            )

        return trade_stats

    def evaluate_paper_trade_settings_change(self, timestamp_earliest: int = None):
        def _can_we_revert_paper_trade_setting(record_count: int,
                                               percent_win: float,
                                               is_paper_trade_on: bool):
            if is_paper_trade_on:
                if record_count >= Config.PAPER_TRADE_MIN_EVALUATION_COUNT and \
                        percent_win >= Config.PAPER_TRADE_EVALUATION_PERCENT_THRESHOLD:
                    return True

            if not is_paper_trade_on:
                if record_count < Config.PAPER_TRADE_MIN_EVALUATION_COUNT:
                    return True

                if percent_win < Config.PAPER_TRADE_EVALUATION_PERCENT_THRESHOLD:
                    return True

            return False

        self.logger.info(f"evaluate_paper_trade_settings_change start")
        trade_stats = self.get_statistics(timestamp_earliest)
        if not trade_stats:
            self.logger.info(f"No trade records found yet.")
        paper_trade_settings = Config.get_paper_trade_settings()
        for market_slug in trade_stats:
            if market_slug not in paper_trade_settings:
                raise KeyError(
                    f"{market_slug} not found in paper trade settings!")
            is_paper_trade_on = paper_trade_settings[market_slug]
            record_count = trade_stats[market_slug]["record_count"]
            num_wins = trade_stats[market_slug]["num_won"]
            if record_count == 0:
                return
            percent_win = float(num_wins/record_count)
            if _can_we_revert_paper_trade_setting(record_count, percent_win, is_paper_trade_on):
                old_paper_trade_setting = is_paper_trade_on
                new_paper_trade_setting = not is_paper_trade_on
                paper_trade_settings[market_slug] = new_paper_trade_setting
                Config.save_paper_trade_settings(paper_trade_settings)
                subject = (
                    f"polymarket_bot: Paper Trade setting for {market_slug} "
                    f"changed to {new_paper_trade_setting} | "
                    f"{int(datetime.now().timestamp())}"
                )
                mail_content = (
                    f"market_slug: {market_slug}\n"
                    f"old_paper_trade_setting: {old_paper_trade_setting}\n"
                    f"new_paper_trade_setting: {new_paper_trade_setting}\n"
                    f"min_count {Config.PAPER_TRADE_MIN_EVALUATION_COUNT}\n"
                    f"record_count: {record_count}\n"
                    f"percent_win: {percent_win*100:.2f}%\n"
                )
                self.logger.info(subject)
                self.logger.info(mail_content)
                Emailer.send_email(subject, mail_content)
            else:
                self.logger.info(
                    f"Paper Trade setting for {market_slug} will be kept to {is_paper_trade_on}."
                )
        self.logger.info(f"evaluate_paper_trade_settings_change end")

    @staticmethod
    def _format_table_title(title, format):
        if format == "html":
            return f"<br/><h4>{title}</h4>"

        return f"\n\n{title}:\n"

    @staticmethod
    def _tabulate_results(table_title: str, results: dict, format: str = "html"):
        data = []
        headers = ["Market", "Count", "Wins", "%"]
        results_sorted = sorted(
            results.items(), key=lambda x: x[1]["percent"], reverse=True)
        percents = []
        count_total = 0
        win_total = 0
        num_unmatched_total = 0
        num_unmatched_wins_total = 0
        for market, result in results_sorted:
            count = result['record_count']
            count_total += count
            wins = result['num_won']
            win_total += wins
            num_unmatched_total += int(result['num_unmatched'])
            num_unmatched_wins_total += int(result['num_unmatched_wins'])
            percent = f"{result['percent']*100:.2f}%"
            percents.append(result['percent']*100)
            data.append([market[:3], count, wins, percent])
        percent_average = f"{(sum(percents) / len(percents)):.2f}%" if percents else "N/A"
        data.append(["-"*11, "-"*11, "-"*11, "-"*11])
        data.append(["", count_total, win_total, percent_average])

        if num_unmatched_total > 0:
            unmatched_percent_average = f"{(num_unmatched_wins_total / num_unmatched_total)*100:.2f}%"
            data.append(["-"*11, "-"*11, "-"*11, "-"*11])
            data.append(["x", num_unmatched_total,
                        num_unmatched_wins_total, unmatched_percent_average])

        return (
            f"{TradeStats._format_table_title(table_title, format)}" +
            tabulate(data, headers=headers, tablefmt=format)
        )

    def send_stats_email(self):
        if not self.trade_files:
            self.logger.info("No trade records found.")
            return

        email_lines = []
        email_lines += [self._tabulate_results("All",
                                               self.get_statistics())]

        hours = [1, 2, 4, 8, 24]
        for hour in hours:
            date_limit = datetime.now() - timedelta(hours=hour)
            timestamp = date_limit.timestamp()
            email_lines += [self._tabulate_results(f"{hour}H",
                                                   self.get_statistics(timestamp))]

        subject = f"polymarket_bot: stats | {int(datetime.now().timestamp())}"
        mail_content = "".join(email_lines)

        Emailer.send_email(subject, mail_content=mail_content,
                           mail_content_html=mail_content)
