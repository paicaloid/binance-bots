import asyncio
import logging
import os

from binance import AsyncClient, BinanceSocketManager

logging.getLogger("test_binance_websocket_api")
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.basename(__file__) + ".log",
    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
    style="{",
)


async def main():
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    ts = bm.kline_futures_socket("OPUSDT", interval="1m")
    # then start receiving messages

    async with ts as tscm:
        while True:
            response = await tscm.recv()

            if response.get("e") == "error":
                # close and restart the socket
                logging.error(response)
                ts.close()
                ts = bm.kline_futures_socket("OPUSDT", interval="1m")
                continue
            else:
                if response.get("k").get("x"):
                    logging.info(response)

    await client.close_connection()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("ok")
