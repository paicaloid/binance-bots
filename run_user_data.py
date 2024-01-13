import asyncio
import logging
import os
from datetime import datetime

from binance import AsyncClient, BinanceSocketManager
from dotenv import find_dotenv, load_dotenv

from utils.telegram_api import send_message
from utils.telegram_msg import TelegramMessage

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

logging.getLogger("USER_DATA_STREAM")
logging.basicConfig(
    level=logging.INFO,
    filename="logs/"
    + os.path.basename(__file__)
    + f"{datetime.now():%Y-%m-%d_%H:%M:%S%z}.log",
    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
    style="{",
)


async def main():
    client = await AsyncClient.create(API_KEY, API_SECRET)
    bm = BinanceSocketManager(client)
    ts = bm.futures_user_socket()
    telegram_msg = TelegramMessage()
    async with ts as tscm:
        while True:
            response = await tscm.recv()
            event_type = response.get("e")
            if event_type == "ORDER_TRADE_UPDATE":
                telegram_msg.new_order_message(response=response)
                msg = telegram_msg.entry_message()
                if msg is not None:
                    send_message(msg=msg)
                msg = telegram_msg.exit_message()
                if msg is not None:
                    send_message(msg=msg)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
