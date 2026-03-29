import json
import os
import time
import logging
from glob import glob
from dataclasses import dataclass, asdict
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY
from core.config import Config
from core.wallet import Wallet
from core.polymarket import Market
from core.utilities import Emailer, setup_logging


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
    """Live trading via Polymarket CLOB API."""

    # Minimum order size
    MIN_ORDER_SIZE = 5.0

    def __init__(self, wallet: Wallet, logger=None):
        """Initialize live trader."""
        self.wallet = wallet
        self.client = self.wallet.clob_client
        self.logger = (logging.getLogger(Config.LOGGER_NAME)
                       if logger is None else logger)

    def _validate_order(self, market: Market, direction: str, entry_price, amount: float) -> tuple[bool, str]:
        """Validate order parameters before submission."""
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

    def get_order(self, order_id: str):
        return self.client.get_order(order_id)

    @staticmethod
    def calculate_fee(price: float, base_fee_bps: int) -> float:
        """Calculate actual fee percentage from price and base fee.

        Fee formula: fee = price * (1 - price) * base_fee / 10000
        At 50¢ with base_fee=1000: 0.50 * 0.50 * 0.10 = 2.5%
        """
        if base_fee_bps == 0:
            return 0.0
        return price * (1 - price) * base_fee_bps / 10000

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
        fee_pct = self.calculate_fee(entry_price, fee_rate_bps)

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
                    usdc_balance = self.wallet.available_balance()
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

    def get_statistics(self, start_ts: int = None, end_ts: int = None):
        trade_stats = {}
        for trade_item in self.trade_files:
            timestamp = trade_item["timestamp"]
            if (start_ts and timestamp < start_ts) or (end_ts and end_ts < timestamp):
                continue
            trade = trade_item["trade"]
            market_slug = trade.market_slug[:-11]
            if market_slug not in trade_stats:
                trade_stats[market_slug] = {
                    "record_count": 0,
                    "wins": 0,
                    "matched": 0,
                    "matched_wins": 0,
                }

            trade_stats[market_slug]["record_count"] += 1
            if trade.order_status == "MATCHED":
                trade_stats[market_slug]["matched"] += 1
                if trade.won:
                    trade_stats[market_slug]["matched_wins"] += 1

            if trade.won:
                trade_stats[market_slug]["wins"] += 1

        return trade_stats
