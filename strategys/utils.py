import pandas as pd
import pytz
import vectorbtpro as vbt
from datetime import datetime, timedelta
import logging


def msg_to_dataframe(
    info: dict,
    interval: str,
    tz: pytz.timezone
) -> pd.DataFrame:
    cur_datetime = datetime.fromtimestamp(info['t']/1000, tz=tz)
    # print(cur_datetime)
    logging.info(cur_datetime)
    df = pd.DataFrame([info])
    df = df.drop(['T', 't', 's', 'i', 'f', 'L', 'x', 'B'], axis=1)
    df = df.rename(columns={
        'o': 'Open',
        'h': 'High',
        'l': 'Low',
        'c': 'Close',
        'v': 'Volume',
        'q': 'Quote volume',
        'n': 'Trade count',
        'V': 'Taker base volume',
        'Q': 'Taker quote volume'
    })
    df = df.astype(float)
    df["Trade count"] = df["Trade count"].astype(int)

    df['Datetime'] = cur_datetime
    df = df.set_index('Datetime')

    # if self.sql:
    #     df.to_sql(f'btcusdt_{interval}', engine, if_exists='append')

    return df


def get_historical_data(
    symbol: str,
    interval: str,
    bar_range: int,
) -> pd.DataFrame:
    # print("Preparing data...")
    logging.info("Preparing data...")

    date_now = datetime.now(
        tz=pytz.timezone('Asia/Bangkok')
    ).replace(second=0, microsecond=0)

    if interval == '1m':
        start_date = date_now - timedelta(minutes=bar_range)
        timeframe = '1 minutes'
    elif interval == '1h':
        start_date = date_now - timedelta(hours=bar_range)
        timeframe = '1 hours'
    else:
        raise ValueError(f'Interval {interval} is not supported.')

    data = vbt.BinanceData.fetch(
        symbol.upper(),
        start=start_date,
        end=date_now,
        timeframe=timeframe,
        tz="Asia/Bangkok",
    )
    data = data.data[symbol.upper()]
    data.index = data.index.rename('Datetime')

    return data
