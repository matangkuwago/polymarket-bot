import asyncio
import io
import csv
import requests
import json
import time
from binance import AsyncClient
from datetime import datetime, timedelta
from core.config import Config
from core.polymarket import PolymarketClient
from core.trader import LiveTrader
from core.utilities import Emailer, setup_logging


class Polymarket5MinuteBot:
    market_timestamp_interval_seconds = 300
    entry_price = Config.TRADE_ENTRY_PRICE
    order_size = Config.TRADE_ORDER_SIZE

    def __init__(self, polymarket_slug_prefix: str, binance_ticker: str):
        self.polymarket_slug_prefix = polymarket_slug_prefix
        self.binance_ticker = binance_ticker
        self.price_history_binance = {}
        self.price_history_polymarket = {}
        self.logger = setup_logging(f'{self.polymarket_slug_prefix}.log')

        # get paper trade settings
        paper_trade_settings = Config.get_paper_trade_settings()
        if self.polymarket_slug_prefix not in paper_trade_settings:
            error_message = f"Paper trade settings not found for {self.polymarket_slug_prefix}!"
            self.logger.error(error_message)
            raise KeyError(error_message)
        self.paper_trade = paper_trade_settings[self.polymarket_slug_prefix]
        self.logger.info(
            f"PAPER TRADE setting for {self.polymarket_slug_prefix}: {self.paper_trade}")

    async def run(self):
        start_time = time.time()
        self.logger.info(
            f"polymarket_bot run started | {self.polymarket_slug_prefix}")
        self.save_override_settings_online()
        await self.load_binance_price_history()
        await self.load_polymarket_price_history()
        predictions = await self.get_predictions()
        await self.place_orders(predictions, paper_trade=self.paper_trade)

        end_time = time.time()
        self.logger.info(
            f"polymarket_bot run ended | {self.polymarket_slug_prefix}")
        self.logger.info(
            f"Total execution time: {end_time - start_time} seconds.")

    def save_override_settings_online(self):

        csv_url = Config.MARKET_SETTINGS_OVERRIDE_URL
        self.logger.info(f"Getting market settings online: {csv_url}")
        response = requests.get(url=csv_url)
        csv_content_response = response.content.decode('utf-8')
        csv_contents = csv.reader(io.StringIO(csv_content_response))

        online_settings = {}

        next(csv_contents)
        for line in csv_contents:
            market = line[0]
            online_settings[market] = dict(Config.MARKET_SETTINGS_DEFAULT)
            online_settings[market]["paper_trade"] = str(
                line[1]).lower() == "true"

        if online_settings:
            self.logger.info(
                f"Online market settings retrieved online: {json.dumps(online_settings, indent=4)}")
            local_market_settings = Config._get_all_market_settings()
            for market in online_settings.keys():
                if market not in local_market_settings:
                    local_market_settings[market] = dict(
                        online_settings[market])
                else:
                    local_market_settings[market] = local_market_settings[market] | online_settings[market]
            Config._save_all_market_settings(local_market_settings)
            self.logger.info(
                f"Saved market settings: {json.dumps(local_market_settings, indent=4)}")

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
                subject="polymarket_bot: Prediction API error", mail_content=error_message)
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
