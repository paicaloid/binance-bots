import asyncio
import json
# import pandas as pd
import pytz
# import vectorbtpro as vbt
import websockets


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
            pass

    async def handle_kline_1m_message(self, message) -> None:
        msg = json.loads(message)
        bar = msg['k']
        is_close = bar['x']
        print(bar)
        if is_close:
            print(bar)

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
