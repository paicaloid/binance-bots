from __future__ import print_function
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
import logging
import time
import threading
import os

logging.getLogger("unicorn_binance_websocket_api")
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.basename(__file__) + '.log',
    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
    style="{"
)

# create instance of BinanceWebSocketApiManager
ubwa = BinanceWebSocketApiManager()

markets = ["opusdt"]
channels = ["kline_15m"]

for channel in channels:
    ubwa.create_stream(channel, markets, output="UnicornFy")


def print_stream_data_from_stream_buffer(ubwa):
    print("waiting 30 seconds, then we start flushing the stream_buffer")
    time.sleep(10)
    while True:
        if ubwa.is_manager_stopping():
            exit(0)
        oldest_stream = ubwa.pop_stream_data_from_stream_buffer()
        if oldest_stream is False:
            time.sleep(0.01)
        else:
            try:
                # remove # to activate the print function:
                # print(oldest_stream["kline"])
                # is_close = oldest_stream['data']['x']
                # logging.info(oldest_stream)
                if oldest_stream["kline"]["is_closed"]:
                    logging.info(oldest_stream)

            except KeyError:
                # Any kind of error...
                # not able to process the data?
                # write it back to the stream_buffer
                ubwa.add_to_stream_buffer(oldest_stream)


# start a worker process to process to move the received stream_data
# from the stream_buffer to a print function
worker_thread = threading.Thread(
    target=print_stream_data_from_stream_buffer,
    args=(ubwa,)
)
worker_thread.start()

# time.sleep(5)

# while True:
#     ubwa.print_summary()
#     time.sleep(60)
