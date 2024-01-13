import json
from datetime import datetime, timedelta

import numpy as np
from pydantic import BaseModel

# with open("example_data/user_data_stream/new_market_order.json") as f:
#     d = json.load(f)
#     print(d)


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

    def _reset(self):
        self.order = OrderTrade()
        self.tp = TakeProfitOrder()
        self.sl = StopLossOrder()
        self.ts = TrailingStopOrder()
        self.average_price = None

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
                print(message)
                self._reset()

        elif self.sl.status == "EXPIRED":
            if (
                self.order.status == "FILLED"
                and self.order.order_id == self.sl.order_id
            ):
                message = self.gen_exit_message(exit_type="SL")
                print(message)
                self._reset()

        elif self.ts.status == "EXPIRED":
            if (
                self.order.status == "FILLED"
                and self.order.order_id == self.ts.order_id
            ):
                message = self.gen_exit_message(exit_type="TS")
                print(message)
                self._reset()


cancel_order = json.loads(
    open("example_data/user_data_stream/canceled_order.json").read()
)
new_order = json.loads(
    open("example_data/user_data_stream/new_market_order.json").read()
)
filled_order = json.loads(
    open("example_data/user_data_stream/filled_market_order.json").read()
)
new_tp = json.loads(open("example_data/user_data_stream/new_tp.json").read())
new_sl = json.loads(open("example_data/user_data_stream/new_sl.json").read())
new_ts = json.loads(open("example_data/user_data_stream/new_ts.json").read())


def message_new_order(response: dict) -> str:
    symbol = response.get("o").get("s")
    order_side = response.get("o").get("S")
    order_type = response.get("o").get("o")
    quantity = response.get("o").get("q")
    emoji = "🔽" if order_side == "SELL" else "🔼"
    message = f"\
    Place Order {symbol}📈📈\n\n\
    Side:       {order_side}{emoji}\n\
    Type:       {order_type}\n\
    Quantity:   {quantity}\n\
    "
    return message


# msg_list = [new_order, filled_order, new_tp, new_sl, new_ts]

telegram = TelegramMessage()

# for msg in msg_list:
#     # print(message_new_order(msg))
#     # print(telegram.order)
#     telegram.new_order_message(msg)
#     telegram.entry_message()


# print()

with open("example_data/user_data_stream/list_msg.txt") as f:
    for line in f:
        line = line.strip()
        data = json.loads(line)
        if data.get("e") == "ORDER_TRADE_UPDATE":
            telegram.new_order_message(response=data)
            telegram.entry_message()
            telegram.exit_message()
