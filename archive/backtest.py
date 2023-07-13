import pandas as pd
import vectorbtpro as vbt

from datetime import datetime, timedelta
from typing import Union

from adx_strategy_no import Strategy


class Backtest():

    def __init__(
        self,
        symbol: str,
        end_date: datetime,
        start_date: Union[datetime, None] = None,
        bar_range: Union[int, None] = 100,
        window_size: int = 250,
        time_frame: str = "1m",
        cash: float = 1000.0
    ) -> None:

        self.symbol = symbol
        self.window_size = window_size
        self.end_date = end_date
        self.bar_range = bar_range
        self.time_frame = time_frame

        if isinstance(start_date, datetime):
            if time_frame == '1m':
                self.start_date = start_date - \
                    timedelta(minutes=self.window_size)
                self.bar_range = end_date - start_date
                self.bar_range = int(self.bar_range.total_seconds() / 60.0)
            elif time_frame == '1h':
                self.start_date = start_date - \
                    timedelta(hours=self.window_size)
                self.bar_range = end_date - start_date
                self.bar_range = int(self.bar_range.total_seconds() / 3600.0)
        else:
            if time_frame == '1m':
                self.start_date = self.lastest_date - \
                    timedelta(minutes=self.bar_range + self.window_size)
            elif time_frame == '1h':
                self.start_date = self.lastest_date - \
                    timedelta(hours=self.bar_range + self.window_size)

        self.port = vbt.pf_enums.ExecState(
            cash=cash,
            position=0.0,
            debt=0.0,
            locked_cash=0.0,
            free_cash=cash,
            val_price=0.0,
            value=0.0
        )

    def get_historical_data(self) -> pd.DataFrame:
        if self.time_frame == '1m':
            timeframe = '1 minutes'
        elif self.time_frame == '1h':
            timeframe = '1 hours'

        data = vbt.BinanceData.fetch(
            self.symbol.upper(),
            start=self.start_date,
            end=self.end_date,
            timeframe=timeframe,
            tz="Asia/Bangkok",
        )
        self.data = data.data[self.symbol.upper()]

    def simulate(self):

        self.strategy = Strategy()

        for index in range(1, self.bar_range + 1):
            data = self.data[index:index + self.window_size]

            self.strategy.execute_order(
                close_price=data["Close"].iloc[-1],
                open_price=data["Open"].iloc[-1],
                high_price=data["High"].iloc[-1],
                low_price=data["Low"].iloc[-1],
            )

            self.strategy.compute_signal(
                close_price=data["Close"],
                high_price=data["High"],
                low_price=data["Low"],
            )

            self.strategy.condition(close_price=data["Close"].iloc[-1])

            print(data.index[-1])
            print(self.strategy.port.port)
            print("--------------------------")


if __name__ == '__main__':
    start_date = datetime.strptime("2023-05-08 02:00:00", "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime("2023-05-08 23:00:00", "%Y-%m-%d %H:%M:%S")
    sim = Backtest(
        symbol="opusdt",
        start_date=start_date,
        end_date=end_date,
        bar_range=239,
        window_size=250,
        time_frame="1h",
    )
    sim.get_historical_data()
    sim.simulate()
    print()
