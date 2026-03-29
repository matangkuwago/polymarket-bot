"""Polymarket API client for reading market data"""

import json
import time
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config


@dataclass
class Market:
    """A single 5-min up/down market."""

    timestamp: int
    slug: str
    title: str
    closed: bool
    outcome: str | None  # "up", "down", or None if not resolved
    up_token_id: str | None
    down_token_id: str | None
    up_price: float
    down_price: float
    price_to_beat: float
    volume: float
    accepting_orders: bool
    taker_fee_bps: int = 1000  # Default 10% base fee
    resolved: bool = False  # True when umaResolutionStatus == "resolved"


class PolymarketClient:
    """Read-only client for Polymarket APIs (no auth needed)."""

    def __init__(self, market_slug_prefix: str, timeout: float | None = None, use_cache: bool = True):
        self.market_slug_prefix = market_slug_prefix
        self.gamma = Config.GAMMA_API
        self.clob = Config.CLOB_API
        self.timeout = timeout or Config.REST_TIMEOUT

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=Config.REST_RETRIES,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=retry_strategy,
        )
        self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "User-Agent": "PolymarketBot/2.0",
                "Accept": "application/json",
                "Connection": "keep-alive",
            }
        )

        # Token ID cache for 5-min markets: timestamp -> (up_token, down_token)
        self._token_cache: dict[int, tuple[str | None, str | None]] = {}
        self._market_cache: dict[int, Market] = {}
        self._cache_ttl = 300  # 5 minutes
        self._use_cache = use_cache

    def get_market(self, timestamp: int, use_cache: bool = True) -> Market | None:
        """Fetch a 5-min market by its timestamp.

        Args:
            timestamp: Unix timestamp of the market
            use_cache: Whether to use cached market data (for token IDs)
        """
        # Check cache first (for recently fetched markets)
        if use_cache and self._use_cache and timestamp in self._market_cache:
            cached = self._market_cache[timestamp]
            # Only return cached if:
            # 1. Market is fully resolved (outcome known) - state is final
            # 2. OR market is still well within its window (prices stable)
            now = int(time.time())
            market_end = timestamp + 300  # 5-min window ends 300s after start

            if cached.closed and cached.outcome:
                # Resolved markets are final - safe to cache forever
                return cached
            elif now < market_end:
                # Market still in window - cache is reasonably fresh
                return cached
            # Otherwise, market may have closed/resolved - fetch fresh data

        slug = f"{self.market_slug_prefix}-{timestamp}"
        try:
            resp = self.session.get(
                f"{self.gamma}/events", params={"slug": slug}, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None

            event = data[0]
            markets = event.get("markets", [])
            event_metadata = event.get("eventMetadata", {})
            price_to_beat = None if 'priceToBeat' not in event_metadata else event_metadata[
                'priceToBeat']
            if not markets:
                return None

            m = markets[0]
            # Parse token IDs
            token_ids = json.loads(m.get("clobTokenIds", "[]"))
            up_token = token_ids[0] if len(token_ids) > 0 else None
            down_token = token_ids[1] if len(token_ids) > 1 else None

            # Cache token IDs (these never change)
            self._token_cache[timestamp] = (up_token, down_token)

            # Parse prices
            prices = json.loads(m.get("outcomePrices", "[0.5, 0.5]"))
            up_price = float(prices[0]) if prices else 0.5
            down_price = float(prices[1]) if len(prices) > 1 else 0.5

            # Determine outcome if resolved
            # A market is truly resolved when:
            # 1. closed=true AND
            # 2. umaResolutionStatus="resolved" (or outcomePrices shows 1.0/0.0)
            outcome = None
            is_closed = m.get("closed", False)
            uma_status = m.get("umaResolutionStatus", "")
            is_resolved = uma_status == "resolved"

            if is_closed and (is_resolved or up_price > 0.99 or down_price > 0.99):
                # Use threshold comparison to handle float precision
                if up_price > 0.99:
                    outcome = "up"
                elif down_price > 0.99:
                    outcome = "down"

            # Extract fee rate from market data (already in Gamma response)
            taker_fee_bps = m.get("takerBaseFee")
            if taker_fee_bps is None:
                taker_fee_bps = 1000
                # Only log once per market
                if timestamp not in self._token_cache:
                    print(
                        f"[polymarket] No takerBaseFee in response for {slug}, using default {taker_fee_bps} bps")
            else:
                taker_fee_bps = int(taker_fee_bps)

            market = Market(
                timestamp=timestamp,
                slug=slug,
                title=event.get("title", ""),
                closed=event.get("closed", False) or m.get("closed", False),
                outcome=outcome,
                up_token_id=up_token,
                down_token_id=down_token,
                up_price=up_price,
                down_price=down_price,
                price_to_beat=price_to_beat,
                volume=event.get("volume", 0),
                accepting_orders=m.get("acceptingOrders", False),
                taker_fee_bps=taker_fee_bps,
                resolved=is_resolved,
            )

            # Cache market
            if self._use_cache:
                self._market_cache[timestamp] = market

            return market
        except requests.exceptions.Timeout:
            # Don't spam logs for timeouts
            return None
        except Exception as e:
            print(f"[polymarket] Error fetching {slug}: {e}")
            return None
