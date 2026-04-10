import asyncio
import io
import csv
import requests
import json
import time
from datetime import datetime
from binance import AsyncClient
from datetime import datetime, timedelta
from core.config import Config
from core.polymarket import PolymarketClient
from core.trader import LiveTrader, TradeStats
from core.utilities import Emailer, setup_logging
from core.wallet import WalletManager


class Polymarket5MinuteBot:
    market_timestamp_interval_seconds = 300

    def __init__(self, polymarket_slug_prefix: str):
        self.bot_id = Config.BOT_ID
        self.polymarket_slug_prefix = polymarket_slug_prefix
        self.binance_ticker = f"{polymarket_slug_prefix[:3]}USDT".upper()
        self.price_history_binance = {}
        self.price_history_polymarket = {}
        self.logger = setup_logging(
            log_file=f"{self.polymarket_slug_prefix}-{self.bot_id}.log",
            logger_name=f"{self.polymarket_slug_prefix}-{self.bot_id}"
        )

        # get settings
        market_settings = Config.get_bot_market_settings(
            self.bot_id,
            self.polymarket_slug_prefix
        )
        self.logger.info(
            f"market_settings for {self.polymarket_slug_prefix}: {market_settings}")
        self.paper_trade = market_settings["paper_trade"]
        self.entry_price = market_settings["entry_price"]
        self.order_size = market_settings["order_size"]
        self.threshold_low = market_settings["threshold_low"]
        self.threshold_high = market_settings["threshold_high"]
        self.threshold_count = market_settings["threshold_count"]
        self.do_check_performance = market_settings["do_check_performance"]
        self.do_check_conflict = market_settings["do_check_conflict"]
        self.threshold_hours = market_settings["threshold_hours"]

        if self.do_check_performance:
            self.check_performance()
        self.wallet = WalletManager().get_wallet(self.bot_id)

    def __del__(self):
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

    def no_conflict(self):
        if not self.do_check_conflict:
            return True

        all_settings = Config._get_all_market_settings()

        # check if other bots are running the same market
        settings_filtered_other_bot = dict(
            filter(
                lambda x: x[0] != self.bot_id and
                not x[1][self.polymarket_slug_prefix]["paper_trade"],
                all_settings.items()
            )
        )
        if settings_filtered_other_bot:
            self.logger.info(f"conflicts found in other bots running {self.polymarket_slug_prefix}: "
                             f"{list(settings_filtered_other_bot.keys())}")
            return False

        # check if our bot is running a market
        settings_filtered_same_bot = list(
            filter(
                lambda x: not all_settings[self.bot_id][x]["paper_trade"],
                all_settings[self.bot_id]
            )
        )
        if settings_filtered_same_bot:
            self.logger.info(f"conflicts found within {self.bot_id} running other markets: "
                             f"{settings_filtered_same_bot}")
            return False

        self.logger.info(f"conflicts not found for {self.bot_id}, "
                         f"{self.polymarket_slug_prefix}")
        return True

    def get_performance(self, hours):
        trade_stats = TradeStats()
        date_limit = (datetime.now() -
                      timedelta(hours=hours))
        timestamp = date_limit.timestamp()
        data = trade_stats.get_statistics(start_ts=timestamp)
        data = dict(filter(
            lambda x: x[0] == self.polymarket_slug_prefix,
            data.items()
        )) if data else None

        if not data:
            return (0, 0)

        record_count = sum([data[x]["record_count"] for x in data])
        wins = sum([data[x]["wins"] for x in data])
        performance = wins/record_count if record_count > 0 else 0
        return (record_count, performance)

    def check_performance(self):
        hours = self.threshold_hours
        record_count, performance = self.get_performance(hours)
        if record_count < self.threshold_count:
            self.logger.info(
                f"check_performance: record_count ({record_count}) "
                f"< threshold_count ({self.threshold_count})"
            )
            return

        send_email_notification = False
        if self.paper_trade and performance <= self.threshold_low and self.no_conflict():
            self.paper_trade = False
            Config.save_bot_market_setting(
                self.bot_id,
                self.polymarket_slug_prefix,
                "paper_trade",
                self.paper_trade
            )
            log_message = (
                f"paper_trade set to {self.paper_trade}: "
                f"performance: {performance:.2f} vs "
                f"threshold {self.threshold_low:.2f}"
            )
            self.logger.info(log_message)
            send_email_notification = True
        elif not self.paper_trade and performance >= self.threshold_high:
            self.paper_trade = True
            Config.save_bot_market_setting(
                self.bot_id,
                self.polymarket_slug_prefix,
                "paper_trade",
                self.paper_trade
            )
            log_message = (
                f"paper_trade set to {self.paper_trade}: "
                f"performance: {performance:.2f} vs "
                f"threshold {self.threshold_high:.2f}"
            )
            self.logger.info(log_message)
            send_email_notification = True
        else:
            log_message = (
                f"check_performance: no change: paper_trade {self.paper_trade}, "
                f"record_count: {record_count:.2f}, "
                f"performance: {performance:.2f}, "
                f"threshold_hours {self.threshold_hours}, "
                f"threshold_low {self.threshold_low:.2f}, "
                f"threshold_high {self.threshold_high:.2f}"
            )
            self.logger.info(log_message)

        if send_email_notification:
            timestamp = datetime.now().timestamp()
            subject = (
                f"{self.bot_id}: polymarket_bot: {self.polymarket_slug_prefix}: "
                f"paper_trade setting is now {self.paper_trade} | "
                f"{timestamp}"
            )
            mail_content = log_message
            Emailer.send_email(
                subject=subject,
                mail_content=mail_content
            )

    async def run(self):
        start_time = time.time()
        self.logger.info(
            f"polymarket_bot run started | {self.polymarket_slug_prefix}")
        await self.load_binance_price_history()
        await self.load_polymarket_price_history()
        predictions = await self.get_predictions()
        await self.place_orders(predictions, paper_trade=self.paper_trade)
        end_time = time.time()

        self.logger.info(
            f"polymarket_bot run ended | {self.polymarket_slug_prefix}")
        self.logger.info(
            f"Total execution time: {end_time - start_time} seconds")

    async def load_binance_price_history(self):
        index_timestamp = 0
        index_closing_price = 4

        client = await AsyncClient.create()
        async for kline in await client.get_historical_klines_generator(
            self.binance_ticker,
            AsyncClient.KLINE_INTERVAL_5MINUTE,
            "2.5 hours ago"
        ):
            timestamp = int(kline[index_timestamp]/1000)
            price = float(kline[index_closing_price])
            self.price_history_binance[timestamp] = price

        await client.close_connection()

        self.logger.info(
            f"price_history_binance: {self.price_history_binance}")

    async def load_polymarket_price_history(self):
        market_interval_minutes = 5
        num_markets_to_fetch = 30

        client = PolymarketClient(
            market_slug_prefix=self.polymarket_slug_prefix)
        current_market = datetime.now().replace(
            minute=(datetime.now().minute - (datetime.now().minute % 5)),
            second=0,
            microsecond=0)

        for i in range(num_markets_to_fetch):
            timestamp = int(current_market.timestamp())
            market = client.get_market(timestamp)
            self.logger.debug(f"market for {timestamp}: {market}")
            price_to_beat_raw = market.price_to_beat
            if price_to_beat_raw is None:
                source = "binance"
                price = self.price_history_binance[timestamp]
                self.logger.info(
                    f"Using Binance price data for timestamp {timestamp}: {price}")
            else:
                source = "polymarket"
                price = float(price_to_beat_raw)
            self.price_history_polymarket[timestamp] = {
                "price": price, "source": source}
            current_market = current_market - \
                timedelta(minutes=market_interval_minutes)

        self.price_history_polymarket = dict(
            sorted(self.price_history_polymarket.items(), key=lambda item: item[0]))
        self.logger.debug(f"price_history_polymarket:")
        for key, value in self.price_history_polymarket.items():
            self.logger.debug(f"{key}: {value}")

    async def get_predictions(self,
                              num_prediction_input=Config.MINIMUM_NUM_PRICE_HISTORY,
                              num_predictions=Config.NUM_PREDICTIONS):

        prediction_input = list(
            x["price"] for x in self.price_history_polymarket.values())[-num_prediction_input:]
        last_market_timestamp = list(self.price_history_polymarket.keys())[-1]
        self.logger.debug(f"Last {num_prediction_input} items as list:")
        self.logger.debug("\n".join(map(str, prediction_input)))

        predicted_directions = await self._get_predictions_from_api(prediction_input, num_predictions)

        predictions = {}
        timestamp_interval = 300
        timestamp_range = range(
            last_market_timestamp + timestamp_interval,
            last_market_timestamp * num_predictions * timestamp_interval,
            timestamp_interval)
        index_range = range(num_predictions)
        for i, timestamp in zip(index_range, timestamp_range):
            predictions[timestamp] = predicted_directions[i]

        self.logger.info(f"predicted_directions: {predicted_directions}")
        self.logger.info(f"last_market_timestamp: {last_market_timestamp}")
        self.logger.info(f"Predictions:")
        self.logger.info(
            ", ".join([f"{key}: {value}" for key, value in predictions.items()]))

        return predictions

    async def _get_predictions_from_api(self, prediction_input, num_predictions):

        def _log_response_error(response):
            response_text = None if not response or not response.content else response.content
            error_message = f"Unable to send prediction request. Status code is {status_code}, message is {response_text}"
            self.logger.error(error_message)
            Emailer.send_email(
                subject=f"{self.bot_id}: polymarket_bot: Prediction API error", mail_content=error_message)
            return error_message

        predictions = []

        # setup prediction request call
        predict_url = Config.PREDICTION_API_ENDPOINT
        auth_token = Config.PREDICTION_API_TOKEN
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {
            "ticker": self.polymarket_slug_prefix[:3],
            "price_history": prediction_input,
            "num_predictions": num_predictions,
        }
        # send prediction request
        response = requests.post(predict_url, json=data, headers=headers)
        status_code = 404
        if response and response.status_code:
            status_code = response.status_code
        if status_code == 202 and response.content:
            request_id = response.content.decode('utf-8')
        else:
            error_message = _log_response_error(response)
            raise RuntimeError(error_message)

        # poll for result
        results_url = f"{Config.PREDICTION_API_RESULTS_ENDPOINT}/{request_id}"
        for _ in range(Config.PREDICTION_API_MAX_POLL):
            response = requests.get(results_url, headers=headers)
            status_code = response.status_code
            if status_code == Config.PREDICTION_API_WAITING_STATUS_CODE:
                self.logger.info(
                    f"Waiting for prediction result for request_id {request_id}...")
                await asyncio.sleep(1)
            elif status_code == 200:
                response_content = response.content.decode('utf-8')
                result_json = json.loads(response_content)
                predictions = result_json["result"]
                break
            else:
                error_message = _log_response_error(response)
                raise RuntimeError(error_message)

        if not predictions:
            error_message = f"Unable to get prediction results after {Config.PREDICTION_API_MAX_POLL} tries"
            self.logger.error(error_message)
            Emailer.send_email(
                subject=f"{self.bot_id}: polymarket_bot: Prediction API error", mail_content=error_message)
            raise RuntimeError(error_message)

        return predictions

    def _check_balance(self, predictions):
        usdc_balance = self.wallet.available_balance()

        order_budget = len(predictions) * \
            self.entry_price * self.order_size
        self.logger.info(
            f"usdc_balance: {usdc_balance}, order_budget: {order_budget}")
        if order_budget > usdc_balance:
            error_message = (f"Not enough account balance to place orders! "
                             f"usdc_balance: {usdc_balance}, order_budget: {order_budget}")
            self.logger.error(error_message)
            Emailer.send_email(
                subject=f"{self.bot_id}: polymarket_bot: balance error", mail_content=error_message)
            raise RuntimeError(error_message)

    async def place_orders(self, predictions: dict, paper_trade: bool = True):

        self._check_balance(predictions)
        trader = LiveTrader(wallet=self.wallet, logger=self.logger)

        client = PolymarketClient(
            market_slug_prefix=self.polymarket_slug_prefix)
        for timestamp, direction in predictions.items():
            market = client.get_market(timestamp)
            trade = trader.place_limit_order(
                market=market,
                direction=direction,
                entry_price=self.entry_price,
                amount=self.order_size,
                paper_trade=paper_trade
            )
            trade.save()
            self.logger.info(f"Order has been placed:")
            self.logger.info(f"market: {market}")
            self.logger.info(f"market: {direction}")
            self.logger.info(f"entry_price: {self.entry_price}")
            self.logger.info(f"amount: {self.order_size}")
