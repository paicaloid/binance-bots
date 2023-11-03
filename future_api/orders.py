import os

from binance.client import Client
from binance.enums import (
    FUTURE_ORDER_TYPE_LIMIT,
    FUTURE_ORDER_TYPE_LIMIT_MAKER,
    FUTURE_ORDER_TYPE_MARKET,
    FUTURE_ORDER_TYPE_STOP,
    FUTURE_ORDER_TYPE_STOP_MARKET,
    FUTURE_ORDER_TYPE_TAKE_PROFIT,
    FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
    FUTURE_ORDER_TYPE_TRAILING_STOP_MARKET,
    SIDE_BUY,
    SIDE_SELL,
    TIME_IN_FORCE_FOK,
    TIME_IN_FORCE_GTC,
    TIME_IN_FORCE_IOC,
)
from dotenv import find_dotenv, load_dotenv

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# print(API_KEY)
# print(API_SECRET)

client = Client(API_KEY, API_SECRET)


def place_order():
    client.futures_create_order(
        symbol="OPUSDT",
        side=SIDE_BUY,
        # positionSide="LONG",
        type=FUTURE_ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=6,
        price=1.3500,
    )


def take_profit():
    client.futures_create_order(
        symbol="OPUSDT",
        side=SIDE_SELL,
        # positionSide="LONG",
        type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
        stopPrice=1.431,
        closePosition=True,
        timeInForce="GTE_GTC",
    )


def stop_loss():
    client.futures_create_order(
        symbol="OPUSDT",
        side=SIDE_SELL,
        # positionSide="LONG",
        type=FUTURE_ORDER_TYPE_STOP_MARKET,
        stopPrice=1.3095,
        closePosition=True,
        timeInForce="GTE_GTC",
    )


def trail_stop():
    client.futures_create_order(
        symbol="OPUSDT",
        side=SIDE_SELL,
        # positionSide="LONG",
        type=FUTURE_ORDER_TYPE_TRAILING_STOP_MARKET,
        activationPrice=1.3905,
        callbackRate=1,
        # closePosition=True,
        quantity=6,
        timeInForce="GTC",
    )


# take_profit()
# stop_loss()
trail_stop()

# balance = client.futures_account_balance()
# print(balance)

# temp = client.futures_get_open_orders(symbol="OPUSDT")
# print(len(temp))
# print(temp[0])

# temp = client.futures_get_all_orders(symbol="OPUSDT")
# print(len(temp))
# print(temp)
# for data in temp:
#     print(data.get("status"))

# temp = client.futures_account()
# print(temp.keys())
# # print(temp.get("assets"))
# print(temp.get("positions"))
