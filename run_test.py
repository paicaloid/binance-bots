import asyncio
import logging
import os
import time

from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager


class UnicornBinanceWebsocket:
    def __init__(self) -> None:
        self.ubwa = BinanceWebSocketApiManager()
        self.market = "opusdt"
        channels = ["kline_1m"]
        self.ubwa.create_stream(channels, self.market, output="UnicornFy")

    async def stream_data(self):
        print("waiting 5 seconds")
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
                        if stream_buffer.get("kline").get("is_closed"):
                            logging.info(stream_buffer)

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
    try:
        asyncio.run(ws.stream_data())
    except KeyboardInterrupt:
        print("\r\nGracefully stopping the websocket manager...")
        ws.ubwa.stop_manager_with_all_streams()
