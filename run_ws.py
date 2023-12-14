import asyncio
import logging
import os
import time
from datetime import datetime

import pandas as pd
from binance import AsyncClient, BinanceSocketManager
from dotenv import find_dotenv, load_dotenv

from future_api.client import BinanceFuturesAPI
from strategys.adx_strategy import Strategy
from utils.helpers import kline_to_dataframe
from utils.telegram_api import send_message

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")


logging.getLogger("OPUSDT_ALGO_TRADING_V2")
logging.basicConfig(
    level=logging.INFO,
    filename="logs/"
    + os.path.basename(__file__)
    + f"{datetime.now():%Y-%m-%d_%H:%M:%S%z}.log",
    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
    style="{",
)


class BinanceHandler:
    def __init__(
        self, base_asset: str, quote_asset: str, interval: str = "1h", limit: int = 250
    ):
        self.symbol = f"{base_asset}{quote_asset}"
        self.interval = interval
        self.limit = limit

        self.binance_api = BinanceFuturesAPI(
            base_asset=base_asset, quote_asset=quote_asset
        )
        self.data = self.binance_api.historical_kline(
            symbol=self.symbol, interval=self.interval, limit=self.limit
        )

        self.delay = 2

    def update_dataframe(self, kline: dict):
        new_kline = kline_to_dataframe(kline)
        self.data = pd.concat([self.data, new_kline])
        self.data = self.data.iloc[-self.limit :]

    def check_long_condition(
        self, price_above_ema: bool, price_above_short_ema: bool, run_trend_up: bool
    ):
        position = self.binance_api.get_real_position()
        if position < 0 and price_above_ema:
            self.binance_api.exit_short_market()
            time.sleep(self.delay)
            if run_trend_up and price_above_ema and price_above_short_ema:
                self.binance_api.enter_long_market()
                time.sleep(self.delay)
                self.binance_api.place_long_stop_signal()
                logging.info("Exit short and Enter long")
            else:
                logging.info("Exit short")
        elif (
            position == 0 and run_trend_up and price_above_ema and price_above_short_ema
        ):
            self.binance_api.cancel_all_orders()
            self.binance_api.enter_long_market()
            time.sleep(self.delay)
            self.binance_api.place_long_stop_signal()
            logging.info("Enter long")
        else:
            logging.info("No Long condition")

    def check_short_condition(
        self, price_below_ema: bool, price_below_short_ema: bool, run_trend_down: bool
    ):
        position = self.binance_api.get_real_position()
        if position > 0 and price_below_ema:
            self.binance_api.exit_long_market()
            time.sleep(self.delay)
            if run_trend_down and price_below_ema and price_below_short_ema:
                self.binance_api.enter_short_market()
                time.sleep(self.delay)
                self.binance_api.place_short_stop_signal()
                logging.info("Exit long and Enter short")
            else:
                logging.info("Exit long")
        elif (
            position == 0
            and run_trend_down
            and price_below_ema
            and price_below_short_ema
        ):
            self.binance_api.cancel_all_orders()
            self.binance_api.enter_short_market()
            time.sleep(self.delay)
            self.binance_api.place_short_stop_signal()
            logging.info("Enter short")
        else:
            logging.info("No Short condition")

    def check_close_long_condition(self, price_below_ema: bool):
        position = self.binance_api.get_real_position()
        if position > 0 and price_below_ema:
            self.binance_api.exit_long_market()
            logging.info("Exit long")
        else:
            logging.info("No Close long condition")

    def check_close_short_condition(self, price_above_ema: bool):
        position = self.binance_api.get_real_position()
        if position < 0 and price_above_ema:
            self.binance_api.exit_short_market()
            logging.info("Exit short")
        else:
            logging.info("No Close short condition")


async def main(base_asset: str, quote_asset: str, interval: str, limit: int):
    symbol = f"{base_asset}{quote_asset}"
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    ts = bm.kline_futures_socket(symbol=symbol, interval=interval)

    bn_handler = BinanceHandler(
        base_asset=base_asset, quote_asset=quote_asset, interval=interval, limit=limit
    )
    strategy = Strategy()
    count_alive = 0
    logging.info("Start trading")
    send_message(msg="Start trading")
    async with ts as tscm:
        while True:
            response = await tscm.recv()
            count_alive += 1
            if response.get("e") == "continuous_kline":
                if response.get("k").get("x"):
                    logging.info(response)
                    bn_handler.update_dataframe(kline=response)
                    strategy.compute_signal(
                        close_price=bn_handler.data["close"],
                        high_price=bn_handler.data["high"],
                        low_price=bn_handler.data["low"],
                    )
                    strategy.condition(close_price=bn_handler.data["close"].iloc[-1])
                    long_condition = {
                        "Long": strategy.buy_condition,
                        "Close_Long": strategy.close_long_condition,
                        "Price_above_EMA": strategy.price_above_ema,
                        "Price_above_short_EMA": strategy.price_above_short_ema,
                        "Run_trend_up": strategy.run_trend_up,
                    }
                    short_condition = {
                        "Short": strategy.sell_condition,
                        "Close_Short": strategy.close_short_condition,
                        "Price_below_EMA": strategy.price_below_ema,
                        "Price_below_short_EMA": strategy.price_below_short_ema,
                        "Run_trend_down": strategy.run_trend_down,
                    }
                    logging.info(long_condition)
                    logging.info(short_condition)

                    if strategy.buy_condition:
                        bn_handler.check_long_condition(
                            price_above_ema=strategy.price_above_ema,
                            price_above_short_ema=strategy.price_above_short_ema,
                            run_trend_up=strategy.run_trend_up,
                        )
                    elif strategy.close_long_condition:
                        bn_handler.check_close_long_condition(
                            price_below_ema=strategy.price_below_ema
                        )

                    if strategy.sell_condition:
                        bn_handler.check_short_condition(
                            price_below_ema=strategy.price_below_ema,
                            price_below_short_ema=strategy.price_below_short_ema,
                            run_trend_down=strategy.run_trend_down,
                        )
                    elif strategy.close_short_condition:
                        bn_handler.check_close_short_condition(
                            price_above_ema=strategy.price_above_ema
                        )
                else:
                    # print("Not closed")
                    pass
            else:
                logging.error(response)
                ts.close()
                logging.info("Restarting socket")
                send_message(msg="Restarting socket")
                ts = bm.kline_futures_socket(symbol=symbol, interval=interval)
                count_alive = 0
                continue

            if count_alive > 3000:
                logging.info("Still alive")
                count_alive = 0
                send_message(msg="Still alive")


if __name__ == "__main__":
    # ws = BinanceWebsocket(symbol="OPUSDT")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(base_asset="OP", quote_asset="USDT", interval="1h", limit=250)
    )
    send_message(msg="Trading stopped")
