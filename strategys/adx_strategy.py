import logging

import pandas as pd
import pandas_ta as ta

# from adx import ADX
from .adx import ADX
from .adx_config import (
    adxSetting,
    emaSetting,
    rsiSetting,
    stochasticSetting,
    stopSetting,
)

# import numpy as np
# import vectorbtpro as vbt


# from typing import Union


class Strategy:
    def __init__(self):
        self.adx_setting = adxSetting()
        self.ema_setting = emaSetting()
        self.rsi_setting = rsiSetting()
        self.stochastic_setting = stochasticSetting()
        self.stop_setting = stopSetting()

        self.buy_condition: bool = False
        self.sell_condition: bool = False
        self.close_long_condition: bool = False
        self.close_short_condition: bool = False

        self.price_above_ema: bool = False
        self.price_below_ema: bool = False
        self.price_above_short_ema: bool = False
        self.price_below_short_ema: bool = False

        self.stoc_ob: bool = False
        self.stoc_os: bool = False

        self.run_trend_up: bool = False
        self.run_trend_down: bool = False

        self.adx: float = 0.0
        self.plusDI: float = 0.0
        self.minusDI: float = 0.0
        self.k: float = 0.0
        self.d: float = 0.0
        self.ema: float = 0.0
        self.ema_short: float = 0.0

        self.long_stop_loss: float = 0.0
        self.long_take_profit: float = 0.0
        self.long_trail_stop_activate: float = 0.0
        self.long_trail_stop_execute: float = 0.0

        self.short_stop_loss: float = 0.0
        self.short_take_profit: float = 0.0
        self.short_trail_stop_activate: float = 0.0
        self.short_trail_stop_execute: float = 0.0

        self.current_position: float = 0.0

        self.long_highest_price: float = None
        self.short_lowest_price: float = None

    def compute_signal(
        self,
        close_price: pd.Series,
        high_price: pd.Series,
        low_price: pd.Series,
    ) -> None:
        adx, plusDI, minusDI = ADX(
            high=high_price,
            low=low_price,
            close=close_price,
            period=self.adx_setting.adx_lenght,
        )
        self.adx = adx.iloc[-1]
        self.plusDI = plusDI.iloc[-1]
        self.minusDI = minusDI.iloc[-1]

        # stoch_rsi = vbt.pandas_ta("STOCHRSI").run(
        #     close_price,
        #     length=self.stochastic_setting.stochastic_lenght,
        #     rsi_length=self.rsi_setting.rsi_lenght,
        #     k=self.stochastic_setting.smooth_k,
        #     d=self.stochastic_setting.smooth_d,
        # )
        # self.k = stoch_rsi.stochrsik.iloc[-1]
        # self.d = stoch_rsi.stochrsid.iloc[-1]
        stoch_rsi = ta.stochrsi(
            close=close_price,
            length=self.stochastic_setting.stochastic_lenght,
            rsi_length=self.rsi_setting.rsi_lenght,
            k=self.stochastic_setting.smooth_k,
            d=self.stochastic_setting.smooth_d,
        )
        self.k = stoch_rsi.iloc[-1, 0]
        self.d = stoch_rsi.iloc[-1, 1]
        # ema = vbt.pandas_ta("EMA").run(
        #     close_price,
        #     length=self.ema_setting.ema_length,
        # )
        # self.ema = ema.ema.iloc[-1]
        self.ema = ta.ema(
            close_price,
            length=self.ema_setting.ema_length,
        ).iloc[-1]

        # ema_short = vbt.pandas_ta("EMA").run(
        #     close_price,
        #     length=self.ema_setting.ema_short_length,
        # )

        # self.ema_short = ema_short.ema.iloc[-1]
        self.ema_short = ta.ema(
            close_price,
            length=self.ema_setting.ema_short_length,
        ).iloc[-1]

    def condition(self, close_price: float) -> None:
        self.buy_condition = (
            (self.plusDI > self.minusDI)
            and (self.plusDI > self.adx_setting.adx_level)
            and (self.plusDI - self.minusDI > self.adx_setting.adx_diff)
        )

        self.sell_condition = (
            (self.minusDI > self.plusDI)
            and (self.minusDI > self.adx_setting.adx_level)
            and (self.minusDI - self.plusDI > self.adx_setting.adx_diff)
        )

        self.close_long_condition = (self.plusDI < self.minusDI) or (
            self.plusDI < self.adx_setting.adx_level
        )

        self.close_short_condition = (self.minusDI < self.plusDI) or (
            self.minusDI < self.adx_setting.adx_level
        )

        self.price_above_ema = close_price > self.ema
        self.price_below_ema = close_price < self.ema
        self.price_above_short_ema = close_price > self.ema_short
        self.price_below_short_ema = close_price < self.ema_short

        self.stoc_ob = (self.k >= self.stochastic_setting.overbought_level) and (
            self.d >= self.stochastic_setting.overbought_level
        )
        self.stoc_os = (self.k <= self.stochastic_setting.oversold_level) and (
            self.d <= self.stochastic_setting.oversold_level
        )
        self.run_trend_up = self.k > self.d
        self.run_trend_down = self.k < self.d

    def execute_order_long(
        self,
        close_price: float,
        open_price: float,
        high_price: float,
        low_price: float,
    ) -> None:
        if self.buy_condition:
            if self.current_position < 0 and self.price_above_ema:
                logging.info("Exit Short: %s", close_price)
                self.current_position = 0
            elif self.current_position > 0:
                logging.info("TP/SL/TS")
            elif (
                self.run_trend_up
                and self.price_above_ema
                and self.price_above_short_ema
            ):
                logging.info("Open Long: %s", close_price)
                self.current_position = 1
                self.set_long_sl_tp_tr(price=close_price)

        elif self.current_position > 0:
            if self.close_long_condition or self.price_below_ema:
                logging.info("Exit Long: %s", close_price)
                self.current_position = 0

        else:
            logging.info("No position")

    def execute_order_short(
        self,
        close_price: float,
        open_price: float,
        high_price: float,
        low_price: float,
    ) -> None:
        if self.sell_condition:
            if self.current_position > 0 and self.price_below_ema:
                logging.info("Exit Long: %s", close_price)
                self.current_position = 0
            elif self.current_position < 0:
                logging.info("TP/SL/TS")
            elif (
                self.run_trend_down
                and self.price_below_ema
                and self.price_below_short_ema
            ):
                logging.info("Open Short: %s", close_price)
                self.current_position = -1
                self.set_short_sl_tp_tr(price=close_price)

    def set_short_sl_tp_tr(self, price: float) -> None:
        self.short_stop_loss = price * (1 + self.stop_setting.stop_loss)
        self.short_take_profit = price * (1 - self.stop_setting.take_profit)
        self.short_trail_stop_activate = price * (
            1 - self.stop_setting.trail_stop_activate
        )

        print("Take Profit: ", self.short_take_profit)
        print("Stop Loss: ", self.short_stop_loss)
        print("Trail Stop Activation: ", self.short_trail_stop_activate)

    def set_long_sl_tp_tr(self, price: float) -> None:
        self.long_stop_loss = price * (1 - self.stop_setting.stop_loss)
        self.long_take_profit = price * (1 + self.stop_setting.take_profit)
        self.long_trail_stop_activate = price * (
            1 + self.stop_setting.trail_stop_activate
        )

        logging.info("Take Profit: %s", self.long_take_profit)
        logging.info("Stop Loss: %s", self.long_stop_loss)
        logging.info("Trail Stop Act: %s", self.long_trail_stop_activate)

    def execute_stop_order_short(
        self,
        close_price: float,
        open_price: float,
        high_price: float,
        low_price: float,
    ) -> None:
        if self.current_position < 0:
            if close_price <= self.short_trail_stop_activate:
                print("Trail Stop Activate")
                if (
                    self.short_lowest_price is None
                    or low_price < self.short_lowest_price
                ):
                    self.short_lowest_price = low_price

                if self.short_lowest_price is not None:
                    self.short_trail_stop = self.short_lowest_price * (
                        1 + self.stop_setting.trail_stop_execute
                    )
                    if close_price >= self.short_trail_stop:
                        print("Trail Stop")
                        self.current_position = 0

            if close_price <= self.short_take_profit:
                print("Take Profit")
                self.current_position = 0

    def execute_stop_order_long(
        self,
        current_price: float,
    ) -> None:
        if self.current_position > 0:
            if current_price >= self.long_trail_stop_activate:
                logging.info("Trail Stop Activate")
                if (
                    self.long_highest_price is None
                    or current_price > self.long_highest_price
                ):
                    self.long_highest_price = current_price
                if self.long_highest_price is not None:
                    self.long_trail_stop = self.long_highest_price * (
                        1 - self.stop_setting.trail_stop_execute
                    )
                    if current_price <= self.long_trail_stop:
                        logging.info("Trail Stop: %s", current_price)
                        self.current_position = 0

            if current_price >= self.long_take_profit:
                logging.info("Take Profit: %s", current_price)
                self.current_position = 0
            elif current_price <= self.long_stop_loss:
                logging.info("Stop Loss: %s", current_price)
                self.current_position = 0

    def execute_stop_order_long_backtest(
        self,
        close_price: float,
        open_price: float,
        high_price: float,
        low_price: float,
    ) -> None:
        """
        Check high price against trail stop activation
        For backtesting purposes: use high price instead of current price
        """
        if self.current_position > 0:
            if high_price >= self.long_trail_stop_activate:
                print("Trail Stop Activate")
                if (
                    self.long_highest_price is None
                    or high_price > self.long_highest_price
                ):
                    self.long_highest_price = high_price

                if self.long_highest_price is not None:
                    self.long_trail_stop = self.long_highest_price * (
                        1 - self.stop_setting.trail_stop_execute
                    )
                    if high_price <= self.long_trail_stop:
                        benchmark = self.long_highest_price
                        ts = self.long_trail_stop
                        print(f"TSL | bm: {benchmark} | trail stop: {ts}")
                        self.current_position = 0

            if high_price >= self.long_take_profit:
                print("Take Profit")
                self.current_position = 0
            elif high_price <= self.long_stop_loss:
                print("Stop Loss")
                self.current_position = 0
