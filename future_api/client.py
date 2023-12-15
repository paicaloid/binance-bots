import logging
import os

import numpy as np
import pandas as pd
from binance.client import Client
from binance.enums import (  # noqa
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

from utils.helpers import kline_list_to_df
from utils.telegram_api import send_message

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")


class BinanceFuturesAPI:
    def __init__(self, base_asset: str, quote_asset: str) -> None:
        self.client = Client(API_KEY, API_SECRET)

        self.base_asset = base_asset
        self.quote_asset = quote_asset
        self.symbol = f"{self.base_asset}{self.quote_asset}"

        self.base_position = 0
        self.quote_position = 0
        self.update_position()

        self.tp_pct = 0.16
        self.sl_pct = 0.02
        self.tl_act_pct = 0.02
        self.tl_exec_pct = 1  # min 0.1, max 5 where 1 for 1%

        # if self.base_position != 0:
        #     raise ValueError("Base position must be 0")

    def update_position(self) -> None:
        f_acc = self.client.futures_account()
        for data in f_acc.get("assets"):
            if data.get("asset") == self.quote_asset:
                self.quote_position = float(data.get("availableBalance"))

        for data in f_acc.get("positions"):
            if data.get("symbol") == self.symbol:
                self.base_position = float(data.get("positionAmt"))

    def cancel_all_orders(self) -> None:
        self.client.futures_cancel_all_open_orders(symbol=self.symbol)
        send_message(msg="Cancel all orders")

    def get_entry_price(self) -> float:
        info = self.client.futures_position_information(symbol=self.symbol)[0]
        return float(info.get("entryPrice"))

    def get_abs_position(self) -> float:
        info = self.client.futures_position_information(symbol=self.symbol)[0]
        return np.abs(float(info.get("positionAmt")))

    def get_real_position(self) -> float:
        info = self.client.futures_position_information(symbol=self.symbol)[0]
        return float(info.get("positionAmt"))

    def historical_kline(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        return kline_list_to_df(
            kline_list=self.client.futures_historical_klines(
                symbol=symbol, interval=interval, start_str=None, limit=limit
            )
        )

    def calculate_quantity(self, ratio: float = 0.8) -> float:
        self.update_position()
        lastest_price = float(
            self.client.futures_symbol_ticker(symbol=self.symbol).get("price")
        )
        quantity = (self.quote_position / lastest_price) * ratio
        return float(f"{quantity:.1f}")

    def enter_long_market(self):
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_BUY,
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=self.calculate_quantity(),
        )
        logging.info("Enter long")
        logging.info(res)
        send_message(msg="Enter long")

    def enter_short_market(self):
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_SELL,
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=self.calculate_quantity(),
        )
        logging.info("Enter short")
        logging.info(res)
        send_message(msg="Enter short")

    def exit_long_market(self):
        try:
            res = self.client.futures_create_order(
                symbol=self.symbol,
                side=SIDE_SELL,
                type=FUTURE_ORDER_TYPE_MARKET,
                # closePosition=True,
                quantity=self.get_abs_position(),
            )
            logging.info("Exit long")
            logging.info(res)
            send_message(msg="Exit long")
        except Exception as e:
            logging.error(e)
            send_message(msg=f"Error: {e}")

    def exit_short_market(self):
        try:
            res = self.client.futures_create_order(
                symbol=self.symbol,
                side=SIDE_BUY,
                type=FUTURE_ORDER_TYPE_MARKET,
                # closePosition=True,
                quantity=self.get_abs_position(),
            )
            logging.info("Exit short")
            logging.info(res)
            send_message(msg="Exit short")
        except Exception as e:
            logging.error(e)
            send_message(msg=f"Error: {e}")

    def place_long_stop_signal(self):
        entry_price = self.get_entry_price()
        tp_price = entry_price * (1 + self.tp_pct)
        tp_price = float(f"{tp_price:.4f}")
        sl_price = entry_price * (1 - self.sl_pct)
        sl_price = float(f"{sl_price:.4f}")
        tl_act_price = entry_price * (1 + self.tl_act_pct)
        tl_act_price = float(f"{tl_act_price:.4f}")
        logging.info(f"entry_price: {entry_price}")
        logging.info(f"TP: {tp_price}, SL: {sl_price}, TL: {tl_act_price}")
        logging.info("Place long stop signal")
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_SELL,
            type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=tp_price,
            closePosition=True,
            timeInForce="GTE_GTC",
        )
        logging.info(res)
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_SELL,
            type=FUTURE_ORDER_TYPE_STOP_MARKET,
            stopPrice=sl_price,
            closePosition=True,
            timeInForce="GTE_GTC",
        )
        logging.info(res)
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_SELL,
            type=FUTURE_ORDER_TYPE_TRAILING_STOP_MARKET,
            activationPrice=tl_act_price,
            callbackRate=self.tl_exec_pct,
            quantity=self.get_abs_position(),
            timeInForce="GTC",
        )
        logging.info(res)
        send_message(
            msg=f"""
            Place long stop signal
            Entry price: {entry_price}
            TP: {tp_price}, SL: {sl_price}, TL: {tl_act_price}
            """
        )

    def place_short_stop_signal(self):
        entry_price = self.get_entry_price()
        tp_price = entry_price * (1 - self.tp_pct)
        tp_price = float(f"{tp_price:.4f}")
        sl_price = entry_price * (1 + self.sl_pct)
        sl_price = float(f"{sl_price:.4f}")
        tl_act_price = entry_price * (1 - self.tl_act_pct)
        tl_act_price = float(f"{tl_act_price:.4f}")
        logging.info(f"entry_price: {entry_price}")
        logging.info(f"TP: {tp_price}, SL: {sl_price}, TL: {tl_act_price}")
        logging.info("Place short stop signal")

        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_BUY,
            type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=tp_price,
            closePosition=True,
            timeInForce="GTE_GTC",
        )
        logging.info(res)
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_BUY,
            type=FUTURE_ORDER_TYPE_STOP_MARKET,
            stopPrice=sl_price,
            closePosition=True,
            timeInForce="GTE_GTC",
        )
        logging.info(res)
        res = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_BUY,
            type=FUTURE_ORDER_TYPE_TRAILING_STOP_MARKET,
            activationPrice=tl_act_price,
            callbackRate=self.tl_exec_pct,
            quantity=self.get_abs_position(),
            timeInForce="GTC",
        )
        logging.info(res)
        send_message(
            msg=f"""
            Place short stop signal
            Entry price: {entry_price}
            TP: {tp_price}, SL: {sl_price}, TL: {tl_act_price}
            """
        )
