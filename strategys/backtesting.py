from datetime import datetime, timedelta
from typing import Union
import vectorbtpro as vbt
import pandas as pd

from adx_strategy import Strategy


def bar_range_converter(
    end_date: datetime,
    start_date: Union[datetime, None],
    bar_range: Union[int, None],
    time_frame: str,
    window_size: int,
) -> int:
    if isinstance(start_date, datetime):
        if time_frame == "1h":
            start_date = start_date - timedelta(hours=window_size)
            bar_range = end_date - start_date
            bar_range = int(bar_range.total_seconds() / 3600.0)
        else:
            raise ValueError("Only 1h timeframe is supported")
    else:
        if time_frame == "1h":
            start_date = end_date - timedelta(hours=window_size + bar_range)
        else:
            raise ValueError("Only 1h timeframe is supported")

    return start_date, bar_range


class Backtest:

    def __init__(
        self,
        symbol: str,
        end_date: datetime,
        start_date: datetime,
        window_size: int = 250,
        time_frame: str = "1h",
    ) -> None:

        self.symbol = symbol
        self.time_frame = time_frame
        self.end_date = end_date
        self.window_size = window_size

        if isinstance(start_date, datetime):
            if time_frame == "1h":
                self.start_date = start_date - timedelta(hours=window_size)
                self.bar_range = end_date - start_date
                self.bar_range = int(self.bar_range.total_seconds() / 3600.0)
        else:
            raise ValueError("Only datetime is supported")

        self.get_historical_data()
        self.strategy = Strategy()

    def get_historical_data(self) -> pd.DataFrame:
        if self.time_frame == '1h':
            timeframe = '1 hours'
        else:
            raise ValueError("Only 1h timeframe is supported")

        data = vbt.BinanceData.fetch(
            self.symbol.upper(),
            start=self.start_date,
            end=self.end_date,
            timeframe=timeframe,
            tz="Asia/Bangkok",
        )
        self.data = data.data[self.symbol.upper()]

    def simulate(self) -> None:
        for index in range(1, self.bar_range + 1):
            data = self.data[index:index + self.window_size]
            cur_date = data.index[-1]
            print(cur_date)

            self.strategy.compute_signal(
                close_price=data['Close'],
                high_price=data['High'],
                low_price=data['Low'],
            )

            self.strategy.condition(
                close_price=data['Close'].iloc[-1],
            )

            self.strategy.execute_order_long(
                close_price=data['Close'].iloc[-1],
                open_price=data['Open'].iloc[-1],
                high_price=data['High'].iloc[-1],
                low_price=data['Low'].iloc[-1],
            )

            # self.strategy.execute_order_short(
            #     close_price=data['Close'].iloc[-1],
            #     open_price=data['Open'].iloc[-1],
            #     high_price=data['High'].iloc[-1],
            #     low_price=data['Low'].iloc[-1],
            # )

            self.strategy.execute_stop_order_long_backtest(
                close_price=data['Close'].iloc[-1],
                open_price=data['Open'].iloc[-1],
                high_price=data['High'].iloc[-1],
                low_price=data['Low'].iloc[-1],
            )
            print()


if __name__ == '__main__':
    start_date = datetime.strptime("2023-07-01 02:00:00", "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime("2023-07-02 23:00:00", "%Y-%m-%d %H:%M:%S")
    sim = Backtest(
        symbol="opusdt",
        start_date=start_date,
        end_date=end_date,
        window_size=250,
        time_frame="1h",
    )
    sim.simulate()
    print()
