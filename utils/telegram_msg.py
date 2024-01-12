import os
from datetime import datetime, timedelta

import numpy as np
from binance.client import Client
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")


class OrderBase(BaseModel):
    order_id: int = None
    time: int = None
    symbol: str = None
    side: str = None
    order_type: str = None
    status: str = None
    time_in_force: str = None
    quantity: float = None
    position_side: str = None


class OrderTrade(OrderBase):
    average_price: float = None


class TakeProfitOrder(OrderBase):
    stop_price: float = None


class StopLossOrder(OrderBase):
    stop_price: float = None


class TrailingStopOrder(OrderBase):
    activation_price: float = None


class TelegramMessage:
    def __init__(self):
        self._reset()
        self.client = Client(API_KEY, API_SECRET)

    def _reset(self):
        self.order = OrderTrade()
        self.tp = TakeProfitOrder()
        self.sl = StopLossOrder()
        self.ts = TrailingStopOrder()
        self.average_price = None

    def entry_message(self):
        if self.order.status == "FILLED":
            if (
                self.tp.status == "NEW"
                and self.sl.status == "NEW"
                and self.ts.status == "NEW"
            ):
                order_side = "SHORT" if self.order.side == "SELL" else "LONG"
                timestamp = datetime.fromtimestamp(
                    int(self.order.time / 1000)
                ) - timedelta(hours=1)
                timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                symbol = self.order.symbol
                quantity = self.order.quantity
                tp_price = self.tp.stop_price
                sl_price = self.sl.stop_price
                ts_price = self.ts.activation_price
                self.average_price = self.order.average_price

                l1 = "✅✅✅ PLACE NEW ORDER ✅✅✅\n"
                l3 = f"Time:    {timestamp} 🕘\n"
                l4 = f"Size:    {quantity}\n\n"

                if order_side == "SHORT":
                    l2 = f"📣📣📣   {order_side} {symbol}  📣📣📣\n\n"
                    l5 = f"SL:      {sl_price} 💲🔼\n"
                    l6 = f"Entry:   {self.average_price} 💲❇️\n"
                    l7 = f"TS:      {ts_price} 💲🔽\n"
                    l8 = f"TP:      {tp_price} 💲🔽\n"

                else:
                    l2 = f"📣📣📣   {order_side} {symbol}  📣📣📣\n\n"
                    l5 = f"TP:      {tp_price} 💲🔼\n"
                    l6 = f"TS:      {ts_price} 💲🔼\n"
                    l7 = f"Entry:   {self.average_price} 💲❇️\n"
                    l8 = f"SL:      {sl_price} 💲🔽\n"

                message = f"{l1}{l2}{l3}{l4}{l5}{l6}{l7}{l8}"
                self.order = OrderTrade()
        else:
            message = None

        return message

    def gen_exit_message(self, exit_type: str):
        exit_price = self.order.average_price
        pnl = np.abs(exit_price - self.average_price) * self.order.quantity
        timestamp = datetime.fromtimestamp(int(self.order.time / 1000)) - timedelta(
            hours=1
        )
        timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        if exit_type == "TP":
            l1 = "💚💚💚 TAKE PROFIT 💚💚💚\n"
            l2 = f"Time:       {timestamp}\n"
            l3 = f"PNL:        {pnl:.2f}\n"
            message = f"{l1}{l2}{l3}"
        elif exit_type == "SL":
            pnl = -pnl
            l1 = "💔💔💔 STOP LOSS 💔💔💔\n"
            l2 = f"Time:       {timestamp}\n"
            l3 = f"PNL:        {pnl:.2f}\n"
            message = f"{l1}{l2}{l3}"
        elif exit_type == "TS":
            l1 = "💙💙💙 TRAILING STOP 💙💙💙\n"
            l2 = f"Time:       {timestamp}\n"
            l3 = f"PNL:        {pnl:.2f}\n"
            message = f"{l1}{l2}{l3}"
        return message

    def exit_message(self):
        if self.tp.status == "EXPIRED":
            if (
                self.order.status == "FILLED"
                and self.order.order_id == self.tp.order_id
            ):
                message = self.gen_exit_message(exit_type="TP")
                symbol = self.order.symbol
                self._reset()
                self.client.futures_cancel_all_open_orders(symbol=symbol)

        elif self.sl.status == "EXPIRED":
            if (
                self.order.status == "FILLED"
                and self.order.order_id == self.sl.order_id
            ):
                message = self.gen_exit_message(exit_type="SL")
                symbol = self.order.symbol
                self._reset()
                self.client.futures_cancel_all_open_orders(symbol=symbol)

        elif self.ts.status == "EXPIRED":
            if (
                self.order.status == "FILLED"
                and self.order.order_id == self.ts.order_id
            ):
                message = self.gen_exit_message(exit_type="TS")
                self._reset()
        else:
            message = None

        return message

    def new_order_message(self, response: dict) -> str:
        order_type = response.get("o").get("o")

        if order_type == "MARKET":
            self.order = OrderTrade(
                order_id=response.get("o").get("i"),
                time=response.get("o").get("T"),
                symbol=response.get("o").get("s"),
                side=response.get("o").get("S"),
                order_type=response.get("o").get("o"),
                status=response.get("o").get("X"),
                time_in_force=response.get("o").get("f"),
                quantity=response.get("o").get("q"),
                position_side=response.get("o").get("ps"),
                average_price=response.get("o").get("ap"),
            )

        elif order_type == "TAKE_PROFIT_MARKET":
            self.tp = TakeProfitOrder(
                order_id=response.get("o").get("i"),
                time=response.get("o").get("T"),
                symbol=response.get("o").get("s"),
                side=response.get("o").get("S"),
                order_type=response.get("o").get("o"),
                status=response.get("o").get("X"),
                time_in_force=response.get("o").get("f"),
                quantity=response.get("o").get("q"),
                position_side=response.get("o").get("ps"),
                stop_price=response.get("o").get("sp"),
            )

        elif order_type == "STOP_MARKET":
            self.sl = StopLossOrder(
                order_id=response.get("o").get("i"),
                time=response.get("o").get("T"),
                symbol=response.get("o").get("s"),
                side=response.get("o").get("S"),
                order_type=response.get("o").get("o"),
                status=response.get("o").get("X"),
                time_in_force=response.get("o").get("f"),
                quantity=response.get("o").get("q"),
                position_side=response.get("o").get("ps"),
                stop_price=response.get("o").get("sp"),
            )

        elif order_type == "TRAILING_STOP_MARKET":
            self.ts = TrailingStopOrder(
                order_id=response.get("o").get("i"),
                time=response.get("o").get("T"),
                symbol=response.get("o").get("s"),
                side=response.get("o").get("S"),
                order_type=response.get("o").get("o"),
                status=response.get("o").get("X"),
                time_in_force=response.get("o").get("f"),
                quantity=response.get("o").get("q"),
                position_side=response.get("o").get("ps"),
                activation_price=response.get("o").get("AP"),
            )
