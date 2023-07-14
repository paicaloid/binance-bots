import asyncio
import json
import pandas as pd
import pytz
# import vectorbtpro as vbt
import websockets
import logging

from utils import get_historical_data, msg_to_dataframe
from adx_strategy import Strategy


class BinanceWebsocketHandler:
    def __init__(
        self,
        symbol: str = "btcusdt",
        interval: str = "1m",
        bar_range: int = 250,
        sql: bool = True
    ) -> None:
        self.symbol = symbol
        self.intreval = interval
        self.tz = pytz.timezone('Asia/Bangkok')
        self.bar_range = bar_range
        self.sql = sql

        self.connections = []
        self.connections.append(
            f'wss://stream.binance.com:9443/ws/{self.symbol}@kline_{interval}'
        )
        self.connections.append(
            f'wss://stream.binance.com:9443/ws/{self.symbol}@trade'
        )

        self.data = get_historical_data(
            symbol=self.symbol,
            interval=self.intreval,
            bar_range=self.bar_range
        )
        self.strategy = Strategy()

    def update_dataframe(self, lastest_df: pd.DataFrame) -> None:
        self.data = pd.concat([self.data, lastest_df])
        self.data = self.data[-self.bar_range:]

    async def handle_trade_message(self, message) -> None:
        msg = json.loads(message)
        current_price = float(msg['p'])
        self.strategy.execute_stop_order_long(
            current_price=current_price,
        )

    async def handle_kline_1m_message(self, message) -> None:
        msg = json.loads(message)
        bar = msg['k']
        is_close = bar['x']
        # print(
        #     "open: ", bar['o'],
        #     "close: ", bar['c'],
        #     "high: ", bar['h'],
        #     "low: ", bar['l'],
        # )
        # self.strategy.execute_stop_order_long(
        #     close_price=float(bar['c']),
        #     open_price=float(bar['o']),
        #     high_price=float(bar['h']),
        #     low_price=float(bar['l']),
        # )
        if is_close:
            df = msg_to_dataframe(info=bar, interval=self.intreval, tz=self.tz)
            self.update_dataframe(df)

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
            # self.strategy.execute_order_short(
            #     close_price=self.data['Close'].iloc[-1],
            #     open_price=self.data['Open'].iloc[-1],
            #     high_price=self.data['High'].iloc[-1],
            #     low_price=self.data['Low'].iloc[-1],
            # )

    async def handle_socket(self, uri):
        async with websockets.connect(uri) as websocket:
            if 'kline_1m' in uri:
                handle_message = self.handle_kline_1m_message
            elif 'kline_1h' in uri:
                handle_message = self.handle_kline_1h_message
            elif "trade" in uri:
                handle_message = self.handle_trade_message

            try:
                async for message in websocket:
                    await handle_message(message)
            except asyncio.TimeoutError:
                logging.warning(f"Connection to {uri} timed out. Retrying...")
                # print(f"Connection to {uri} timed out. Retrying...")
                await self.handle_socket(uri)  # retry connection
            async for message in websocket:
                await handle_message(message)

    async def run(self):
        await asyncio.gather(
            *[self.handle_socket(uri) for uri in self.connections]
        )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename="logfile",
        filemode="a+",
        # format="%(asctime)-15s %(levelname)-8s %(message)s"
    )
    handler = BinanceWebsocketHandler(
        symbol='opusdt',
        interval='1m',
        # trade=True,
        bar_range=250,
        sql=False
    )
    asyncio.get_event_loop().run_until_complete(handler.run())
