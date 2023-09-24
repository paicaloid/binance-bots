import asyncio
import logging
import os
import sys
import time
from typing import List

import pandas as pd
import sqlalchemy
from binance.client import Client
from binance.helpers import round_step_size
from dotenv import find_dotenv, load_dotenv
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager

from strategys.adx_strategy import Strategy
from utils.helpers import (
    get_balances,
    get_current_price,
    get_kline_1H,
    get_open_orders,
    get_symbol_info,
    kline_list_to_df,
    place_order_market_buy,
    place_order_market_sell,
    unicornfy_to_dataframe,
)

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")


class BinanceAPI:
    def __init__(self, symbol: str, bar_range: int = 250):
        self.bar_range = bar_range
        self.client = Client(api_key=API_KEY, api_secret=API_SECRET)
        self.symbol_info = get_symbol_info(
            client=self.client,
            symbol=symbol,
        )
        self.balances = get_balances(client=self.client)
        self.check_portfolio()
        self.position = 0
        self.highest_price = 0

    def check_portfolio(self):
        base_asset = self.symbol_info.base_asset
        base_asset_vol = float(self.balances.get(base_asset).get("free"))
        lot_size_min_qty = self.symbol_info.lot_size_filter.min_qty
        if base_asset_vol > lot_size_min_qty:
            logging.info(
                "Base asset volume %s is greater than lot size min qty %s",
                base_asset_vol,
                lot_size_min_qty,
            )
            logging.info("please adjust your portfolio")
            sys.exit(1)

        orders = get_open_orders(client=self.client, symbol=self.symbol_info.symbol)
        if orders:
            logging.info(f"Open orders for {self.symbol_info.symbol} found")
            logging.info("please close all open orders")
            sys.exit(1)

    def get_historical_data(self):
        kline_list = get_kline_1H(
            client=self.client,
            symbol=self.symbol_info.symbol,
            limit=self.bar_range,
        )
        return kline_list_to_df(kline_list=kline_list)

    def place_market_order(self, strategy: Strategy):
        if strategy.buy_condition:
            if self.position < 0 and strategy.price_above_ema:
                logging.info("Exit short position")
                self.position = 0
            elif self.position > 0:
                logging.info("TP/SL/TS")
            elif (
                strategy.run_trend_up
                and strategy.price_above_ema
                and strategy.price_above_short_ema
            ):
                logging.info("Enter long position")
                self.balances = get_balances(client=self.client)
                quote_asset_vol = self.balances.get(self.symbol_info.quote_asset).get(
                    "free"
                )
                res = place_order_market_buy(
                    client=self.client,
                    symbol=self.symbol_info.symbol,
                    quote_order_qty=float(quote_asset_vol),
                )
                logging.info(res)
                self.position = 1
                current_price = get_current_price(symbol=self.symbol_info.symbol)
                strategy.set_long_sl_tp_tr(price=current_price)

        elif self.position > 0:
            if strategy.close_long_condition or strategy.price_below_ema:
                logging.info("Exit long position")
                self.balances = get_balances(client=self.client)
                base_asset_vol = self.balances.get(self.symbol_info.base_asset).get(
                    "free"
                )
                res = place_order_market_sell(
                    client=self.client,
                    symbol=self.symbol_info.symbol,
                    quantity=round_step_size(
                        float(base_asset_vol), self.symbol_info.lot_size_filter.min_qty
                    ),
                )
                logging.info(res)
                self.position = 0
                self.highest_price = 0
        else:
            logging.info("No buy condition")

    def place_stop_order_long(self, current_price: float, strategy: Strategy):
        if self.position > 0:
            if current_price >= strategy.long_trail_stop_activate:
                logging.info(f"Trail stop activated @ {current_price}")

                if current_price > self.highest_price:
                    self.highest_price = current_price
                    logging.info(f"New highest price @ {self.highest_price}")

                if self.highest_price > 0:
                    strategy.long_trail_stop = self.highest_price * (
                        1 - strategy.stop_setting.trail_stop_execute
                    )
                    if current_price <= strategy.long_trail_stop:
                        logging.info(
                            f"Trail stop executed @ {strategy.long_trail_stop}"
                        )
                        self.balances = get_balances(client=self.client)
                        base_asset_vol = self.balances.get(
                            self.symbol_info.base_asset
                        ).get("free")
                        res = place_order_market_sell(
                            client=self.client,
                            symbol=self.symbol_info.symbol,
                            quantity=round_step_size(
                                float(base_asset_vol),
                                self.symbol_info.lot_size_filter.min_qty,
                            ),
                        )
                        logging.info(res)
                        self.position = 0
                        self.highest_price = 0

            if current_price >= strategy.long_take_profit:
                logging.info(f"Take profit executed @ {strategy.long_take_profit}")
                self.balances = get_balances(client=self.client)
                base_asset_vol = self.balances.get(self.symbol_info.base_asset).get(
                    "free"
                )
                res = place_order_market_sell(
                    client=self.client,
                    symbol=self.symbol_info.symbol,
                    quantity=round_step_size(
                        float(base_asset_vol),
                        self.symbol_info.lot_size_filter.min_qty,
                    ),
                )
                logging.info(res)
                self.position = 0
                self.highest_price = 0
            elif current_price <= strategy.long_stop_loss:
                logging.info(f"Stop loss executed @ {strategy.long_stop_loss}")
                self.balances = get_balances(client=self.client)
                base_asset_vol = self.balances.get(self.symbol_info.base_asset).get(
                    "free"
                )
                res = place_order_market_sell(
                    client=self.client,
                    symbol=self.symbol_info.symbol,
                    quantity=round_step_size(
                        float(base_asset_vol),
                        self.symbol_info.lot_size_filter.min_qty,
                    ),
                )
                logging.info(res)
                self.position = 0
                self.highest_price = 0


class UnicornBinanceWebsocket:
    def __init__(
        self,
        symbol: str = "OPUSDT",
        bar_range: int = 250,
        channels: List[str] = ["kline_1h", "trade"],
    ) -> None:
        self.symbol = symbol
        self.bar_range = bar_range

        # Biannce API
        self.binance_api = BinanceAPI(symbol=symbol, bar_range=bar_range)

        # Historical data
        self.data = self.binance_api.get_historical_data()
        self.db_engine = sqlalchemy.create_engine(
            f"sqlite:///database/{symbol}_stream.db",
        )
        self.data.to_sql(symbol, self.db_engine, if_exists="replace")

        # Binance Websocket
        self.ubwa = BinanceWebSocketApiManager()
        self.symbol = symbol
        self.channels = channels
        self.ubwa.create_stream(
            channels=self.channels,
            markets=self.symbol,
            output="UnicornFy",
        )

        # Strategy
        self.strategy = Strategy()

        # Compute when entering the trade
        self.strategy.compute_signal(
            close_price=self.data["close"],
            high_price=self.data["high"],
            low_price=self.data["low"],
        )
        self.strategy.condition(
            close_price=self.data["close"].iloc[-1],
        )
        self.binance_api.place_market_order(strategy=self.strategy)

    async def kline_handler(self, stream_data: dict):
        if stream_data.get("kline").get("is_closed"):
            logging.info(stream_data)
            kline_df = unicornfy_to_dataframe(kline=stream_data.get("kline"))
            kline_df.to_sql(self.symbol, self.db_engine, if_exists="append")
            self.data = pd.concat([self.data, kline_df])
            self.data = self.data[-self.bar_range :]

            self.strategy.compute_signal(
                close_price=self.data["close"],
                high_price=self.data["high"],
                low_price=self.data["low"],
            )
            self.strategy.condition(
                close_price=self.data["close"].iloc[-1],
            )

            self.binance_api.place_market_order(strategy=self.strategy)

    async def trade_handler(self, stream_data: dict):
        current_price = float(stream_data.get("price"))
        self.binance_api.place_stop_order_long(
            current_price=current_price, strategy=self.strategy
        )

    async def stream_data(self):
        logging.info("waiting 5 seconds")
        time.sleep(5)
        while True:
            if self.ubwa.is_manager_stopping():
                exit(0)
            stream_buffer = self.ubwa.pop_stream_data_from_stream_buffer()
            if stream_buffer is False:
                time.sleep(0.01)
            else:
                try:
                    if stream_buffer.get("event_type") == "kline":
                        await self.kline_handler(stream_data=stream_buffer)
                    elif stream_buffer.get("event_type") == "trade":
                        pass
                except KeyError:
                    self.ubwa.add_to_stream_buffer(stream_buffer)


if __name__ == "__main__":
    logging.getLogger("unicorn_binance_websocket_api")
    logging.basicConfig(
        level=logging.INFO,
        filename="logs/" + os.path.basename(__file__) + ".log",
        format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
        style="{",
    )
    ws = UnicornBinanceWebsocket()
    # ws = UnicornBinanceWebsocket(channels=["kline_1m", "trade"])

    try:
        asyncio.run(ws.stream_data())
    except KeyboardInterrupt:
        print("\r\nGracefully stopping the websocket manager...")
        ws.ubwa.stop_manager_with_all_streams()
    # b_api = BinanceAPI(symbol="OPUSDT")
