from __future__ import print_function
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
import logging
import time
import threading
import os
import pytz
import sqlalchemy
import pandas as pd
from datetime import datetime
from strategys.utils import get_historical_data
from strategys.adx_strategy import Strategy

logging.getLogger("unicorn_binance_websocket_forward_testing")
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.basename(__file__) + '.log',
    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
    style="{"
)


def unicornfy_to_dataframe(
    kline_data: dict,
    tz: pytz.timezone = pytz.timezone('Asia/Bangkok')
) -> pd.DataFrame:
    """
    Convert UnicornFy kline data to pandas DataFrame
    :param kline_data: UnicornFy kline data
    :param tz: timezone
    :return: pandas DataFrame
    """
    cur_datetime = datetime.fromtimestamp(
        kline_data['kline_start_time']/1000,
        tz=tz
    )
    df = pd.DataFrame([kline_data])
    df = df.drop([
        'kline_start_time',
        'kline_close_time',
        'symbol', 'interval',
        'first_trade_id',
        'last_trade_id',
        'is_closed',
        'ignore'
        ], axis=1
    )
    df = df.rename(columns={
        'open_price': 'Open',
        'high_price': 'High',
        'low_price': 'Low',
        'close_price': 'Close',
        'base_volume': 'Volume',
        'quote': 'Quote volume',
        'number_of_trades': 'Trade count',
        'taker_by_base_asset_volume': 'Taker base volume',
        'taker_by_quote_asset_volume': 'Taker quote volume'
    })
    df = df.astype(float)
    df["Trade count"] = df["Trade count"].astype(int)
    df['Datetime'] = cur_datetime
    df = df.set_index('Datetime')
    return df


class UnicornBinanceWebsocket:
    def __init__(self) -> None:
        self.ubwa = BinanceWebSocketApiManager()
        self.bar_range = 250

        self.market = "opusdt"
        channels = ["kline_1m", "trade"]
        self.ubwa.create_stream(channels, self.market, output="UnicornFy")

        self.data = get_historical_data(
            symbol=self.market,
            interval="1m",
            bar_range=250
        )

        self.db_engine = sqlalchemy.create_engine(
            f"sqlite:///{self.market}stream.db",
        )
        self.data.to_sql(self.market, self.db_engine, if_exists="replace")
        self.strategy = Strategy()

    def kline_handler(self, stream_data: dict):
        if stream_data["kline"]["is_closed"]:
            kline_df = unicornfy_to_dataframe(kline_data=stream_data["kline"])
            kline_df.to_sql(self.market, self.db_engine, if_exists="append")
            self.data = pd.concat([self.data, kline_df])
            self.data = self.data[-self.bar_range:]

            self.strategy.compute_signal(
                close_price=self.data['Close'],
                high_price=self.data['High'],
                low_price=self.data['Low'],
            )

            self.strategy.condition(
                close_price=self.data['Close'].iloc[-1],
            )

            self.strategy.execute_order_long(
                close_price=self.data['Close'].iloc[-1],
                open_price=self.data['Open'].iloc[-1],
                high_price=self.data['High'].iloc[-1],
                low_price=self.data['Low'].iloc[-1],
            )

    def trade_handler(self, stream_data: dict):
        current_price = float(stream_data["price"])
        self.strategy.execute_stop_order_long(
            current_price=current_price,
        )

    def print_stream_data_from_stream_buffer(self):
        print("waiting 10 seconds, then we start flushing the stream_buffer")
        time.sleep(10)
        while True:
            if self.ubwa.is_manager_stopping():
                exit(0)
            oldest_stream = self.ubwa.pop_stream_data_from_stream_buffer()
            if oldest_stream is False:
                time.sleep(0.01)
            else:
                try:
                    if oldest_stream["event_type"] == "kline":
                        self.kline_handler(oldest_stream)
                    elif oldest_stream["event_type"] == "trade":
                        self.trade_handler(oldest_stream)

                except KeyError:
                    self.ubwa.add_to_stream_buffer(oldest_stream)


ws = UnicornBinanceWebsocket()
worker_thread = threading.Thread(
    target=ws.print_stream_data_from_stream_buffer,
    args=()
)
worker_thread.start()
