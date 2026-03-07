import logging
import sys
from binance import AsyncClient
from datetime import datetime, timedelta
from core.polymarket import PolymarketClient
from core.config import Config


class Polymarket5MinuteBot:
    market_timestamp_interval_seconds = 300

    def __init__(self, polymarket_slug_prefix: str, binance_ticker: str):
        self.polymarket_slug_prefix = polymarket_slug_prefix
        self.binance_ticker = binance_ticker
        self.price_history_binance = {}
        self.price_history_polymarket = {}
        self._setup_logging()

    def _setup_logging(self):
        # 1. Create a custom logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(Config.LOG_LEVEL)

        # 2. Define a format for the logs
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 3. Create a console handler (StreamHandler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(Config.LOG_LEVEL)
        console_handler.setFormatter(formatter)

        # 4. Create a file handler (FileHandler)
        file_handler = logging.FileHandler(f'Polymarket5MinuteBot-{self.polymarket_slug_prefix}.log', mode='a')
        file_handler.setLevel(Config.LOG_LEVEL)
        file_handler.setFormatter(formatter)

        # 5. Add the handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    async def run(self):
        await self.load_binance_price_history()
        await self.load_polymarket_price_history()
        await self.get_predictions()

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

        current_market = datetime.now().replace(
            minute=(datetime.now().minute - (datetime.now().minute % 5)), 
            second=0, 
            microsecond=0)
        self.logger.info(f"price_history_binance: {self.price_history_binance}")

    async def load_polymarket_price_history(self):
        market_interval_minutes = 5
        num_markets_to_fetch = 30

        client = PolymarketClient(market_slug_prefix=self.polymarket_slug_prefix)
        current_market = datetime.now().replace(
            minute=(datetime.now().minute - (datetime.now().minute % 5)), 
            second=0, 
            microsecond=0)

        for i in range(num_markets_to_fetch):
            timestamp = int(current_market.timestamp())
            market = client.get_market(timestamp)
            price_to_beat_raw = market.price_to_beat
            if price_to_beat_raw is None:
                source = "binance"
                price = self.price_history_binance[timestamp]
                self.logger.info(f"Using Binance price data for timestamp {timestamp}: {price}" )
            else:
                source = "polymarket"
                price = float(price_to_beat_raw)
            self.price_history_polymarket[timestamp] = {"price": price, "source": source}
            current_market = current_market - timedelta(minutes=market_interval_minutes)

        self.price_history_polymarket = dict(sorted(self.price_history_polymarket.items(), key=lambda item: item[0]))
        self.logger.info(f"price_history_polymarket:")
        for key, value in self.price_history_polymarket.items():
            self.logger.info(f"{key}: {value}")

    async def get_predictions(self, 
                              num_prediction_input=Config.MINIMUM_NUM_PRICE_HISTORY, 
                              num_predictions=Config.NUM_PREDICTIONS):

        prediction_input = list(x["price"] for x in self.price_history_polymarket.values())[-num_prediction_input:]
        last_market_timestamp = list(self.price_history_polymarket.keys())[-1]
        self.logger.info(f"Last {num_prediction_input} items as list:")
        self.logger.info("\n".join(map(str, prediction_input)))

        predicted_directions = await self._get_predictions_from_api(prediction_input, num_predictions)

        predictions = {}
        timestamp_interval = 300
        timestamp_range = range(last_market_timestamp+timestamp_interval, last_market_timestamp*num_predictions*timestamp_interval, timestamp_interval)
        index_range = range(num_predictions)
        for i, timestamp in zip(index_range, timestamp_range):
            predictions[timestamp] = predicted_directions[i]

        self.logger.info(f"predicted_directions: {predicted_directions}")
        self.logger.info(f"last_market_timestamp: {last_market_timestamp}")
        self.logger.info(f"Predictions:")
        self.logger.info(", ".join([f"{key}: {value}" for key, value in predictions.items()]))

    async def _get_predictions_from_api(self, prediction_input, num_predictions):
        # generate random predictions for now
        import random
        predictions = []
        for _ in range(num_predictions):
            if random.randint(1, 6) > 3:
                prediction = "up"
            else:
                prediction = "down"
            predictions.append(prediction)
        return predictions