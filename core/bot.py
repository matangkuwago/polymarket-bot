import asyncio
import logging
import requests
import json
import sys
import time
from binance import AsyncClient
from datetime import datetime, timedelta
from core.config import Config
from core.polymarket import PolymarketClient
from core.trader import LiveTrader
from core.utilities import Emailer


class Polymarket5MinuteBot:
    market_timestamp_interval_seconds = 300
    entry_price = Config.TRADE_ENTRY_PRICE
    order_size = Config.TRADE_ORDER_SIZE

    def __init__(self, polymarket_slug_prefix: str, binance_ticker: str, paper_trade: bool):
        self.polymarket_slug_prefix = polymarket_slug_prefix
        self.binance_ticker = binance_ticker
        self.price_history_binance = {}
        self.price_history_polymarket = {}
        self.paper_trade = paper_trade
        self._setup_logging()

    def _setup_logging(self):
        # 1. Create a custom logger
        self.logger = logging.getLogger(Config.LOGGER_NAME)
        self.logger.setLevel(Config.LOG_LEVEL)

        # 2. Define a format for the logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 3. Create a console handler (StreamHandler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(Config.LOG_LEVEL)
        console_handler.setFormatter(formatter)

        # 4. Create a file handler (FileHandler)
        file_handler = logging.FileHandler(
            f'Polymarket5MinuteBot-{self.polymarket_slug_prefix}.log', mode='a')
        file_handler.setLevel(Config.LOG_LEVEL)
        file_handler.setFormatter(formatter)

        # 5. Add the handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    async def run(self):
        start_time = time.time()
        await self.load_binance_price_history()
        await self.load_polymarket_price_history()
        predictions = await self.get_predictions()
        await self.place_orders(predictions, paper_trade=self.paper_trade)
        end_time = time.time()
        email_body = f"""
        Start time: {start_time}.
        End time: {end_time}.
        Total execution time: {end_time - start_time} seconds.
        """
        self.logger.info(email_body)
        Emailer.send_email(
            subject=f"polymarket_bot run ended | {self.polymarket_slug_prefix} | {int(start_time)}", mail_content=email_body)

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
            self.logger.info(f"market for {timestamp}: {market}")
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
        self.logger.info(f"price_history_polymarket:")
        for key, value in self.price_history_polymarket.items():
            self.logger.info(f"{key}: {value}")

    async def get_predictions(self,
                              num_prediction_input=Config.MINIMUM_NUM_PRICE_HISTORY,
                              num_predictions=Config.NUM_PREDICTIONS):

        prediction_input = list(
            x["price"] for x in self.price_history_polymarket.values())[-num_prediction_input:]
        last_market_timestamp = list(self.price_history_polymarket.keys())[-1]
        self.logger.info(f"Last {num_prediction_input} items as list:")
        self.logger.info("\n".join(map(str, prediction_input)))

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
                subject="polymarket_bot: Prediction API error", mail_content=error_message)
            return error_message

        predictions = []

        # setup prediction request call
        predict_url = Config.PREDICTION_API_ENDPOINT
        auth_token = Config.PREDICTION_API_TOKEN
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {"price_history": prediction_input}
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
            error_message = f"Unable to get prediction results after {Config.PREDICTION_API_MAX_POLL} tries."
            self.logger.error(error_message)
            Emailer.send_email(
                subject="polymarket_bot: Prediction API error", mail_content=error_message)
            raise RuntimeError(error_message)

        return predictions

    def _check_balance(self, trader: LiveTrader, predictions):
        usdc_balance = trader.get_usdc_balance()

        order_budget = len(predictions) * \
            self.entry_price * self.order_size
        self.logger.info(
            f"usdc_balance: {usdc_balance}, order_budget: {order_budget}.")
        if order_budget > usdc_balance:
            error_message = f"Not enough account balance to place orders! usdc_balance: {usdc_balance}, order_budget: {order_budget}."
            self.logger.error(error_message)
            Emailer.send_email(
                subject="polymarket_bot: balance error", mail_content=error_message)
            raise RuntimeError(error_message)

    async def place_orders(self, predictions: dict, paper_trade: bool = True):

        trader = LiveTrader(logger=self.logger)
        self._check_balance(trader, predictions)

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
