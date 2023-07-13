import asyncio
import json
import pandas as pd
import pytz
import vectorbtpro as vbt
import websockets

from datetime import datetime, timedelta

from utils import msg_to_dataframe
from adx_strategy_no import Strategy


class BinanceWebsocketHandler:
    def __init__(
        self,
        symbol: str = "btcusdt",
        interval: str = "1m",
        trade: bool = True,
        bar_range: int = 250,
        sql: bool = True
    ) -> None:

        self.symbol = symbol
        self.intreval = interval
        self.tz = pytz.timezone('Asia/Bangkok')
        self.bar_range = bar_range
        self.sql = sql

        self.connections = []
        self.connections.append(f'wss://stream.binance.com:9443/ws/{self.symbol}@kline_{interval}')
        if trade:
            # self.connections.append(f'wss://stream.binance.com:9443/ws/{self.symbol}@trade')
            # self.connections.append(f'wss://stream.binance.com:9443/ws/{self.symbol}@kline_1s')
            pass

        self.get_historical_data()
        self.strategy = Strategy()

    def get_historical_data(self) -> None:
        print("Preparing data...")

        date_now = datetime.now(tz=self.tz).replace(second=0, microsecond=0)
        if self.intreval == '1m':
            start_date = date_now - timedelta(minutes=self.bar_range)
            timeframe = '1 minutes'
        elif self.intreval == '1h':
            start_date = date_now - timedelta(hours=self.bar_range)
            timeframe = '1 hours'

        data = vbt.BinanceData.fetch(
            self.symbol.upper(),
            start=start_date,
            end=date_now,
            timeframe=timeframe,
            tz="Asia/Bangkok",
        )
        self.data = data.data[self.symbol.upper()]
        self.data.index = self.data.index.rename('Datetime')

    def update_dataframe(self, lastest_df: pd.DataFrame) -> None:
        self.data = pd.concat([self.data, lastest_df])
        self.data = self.data[-self.bar_range:]

    async def handle_kline_1m_message(self, message) -> None:
        msg = json.loads(message)
        bar = msg['k']
        is_close = bar['x']

        if is_close:
            # cur_date = datetime.fromtimestamp(bar['t']/1000, tz=self.tz)
            df = msg_to_dataframe(info=bar, interval=self.intreval, tz=self.tz)
            # print(df)
            self.update_dataframe(lastest_df=df)
            self.strategy.execute_order(
                close_price=df['Close'].iloc[-1],
                open_price=df['Open'].iloc[-1],
                high_price=df['High'].iloc[-1],
                low_price=df['Low'].iloc[-1],
            )

            self.strategy.compute_signal(
                close_price=df['Close'],
                high_price=df['High'],
                low_price=df['Low'],
            )

            self.strategy.condition(
                close_price=df['Close'].iloc[-1],
            )

            print(df.index[-1])
            print(self.strategy.port.port)
            print("=====")

    async def handle_socket(self, uri):
        async with websockets.connect(uri) as websocket:
            if 'kline_1m' in uri:
                handle_message = self.handle_kline_1m_message
            elif 'kline_1s' in uri:
                handle_message = self.handle_kline_1s_message
            async for message in websocket:
                await handle_message(message)

    async def run(self):
        await asyncio.wait([self.handle_socket(uri) for uri in self.connections])


if __name__ == '__main__':
    handler = BinanceWebsocketHandler(
        symbol='opusdt',
        interval='1m',
        trade=False,
        bar_range=250,
        sql=False
    )
    asyncio.get_event_loop().run_until_complete(handler.run())
