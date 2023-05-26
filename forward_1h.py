import json

from ws import ThreadClient
from adx_strategy_no import Strategy

import asyncio
import requests
import websockets
import pytz
import pandas as pd
from datetime import datetime, timedelta
import vectorbtpro as vbt
import sqlalchemy
import csv

import os

# def load_env():
#     with open('.env') as f:
#         for line in f:
#             if line.startswith('#') or not line.strip():
#                 continue
#             key, value = line.strip().split('=', 1)
#             os.environ[key] = value

# load_env()

# api_key = os.getenv("BINANCE_API_KEY")
# secret_key = os.getenv("SECRET_KEY")


engine = sqlalchemy.create_engine('sqlite:///btcusdtStream.db')

class BinanceWebsocketHandler:
    def __init__(
        self, 
        symbol: str = "btcusdt", 
        interval: str = "1h", 
        trade: bool = False,
        bar_range: int = 250,
        sql: bool = True
    ) -> None:
        
        self.symbol = symbol
        self.tz = pytz.timezone('Asia/Bangkok')
        self.bar_range = bar_range
        self.sql = sql
        
        self.connections = []
        self.connections.append(f'wss://stream.binance.com:9443/ws/{self.symbol}@kline_{interval}')
        # self.connections.append(f'wss://stream.binance.com:9443/ws/userData')
        # if trade:
        #     # self.connections.append(f'wss://stream.binance.com:9443/ws/{self.symbol}@trade')
        #     self.connections.append(f'wss://stream.binance.com:9443/ws/{self.symbol}@kline_1s')
            
        self.get_historical_data()
        self.strategy = Strategy()
        self.trade = trade

        
    def get_historical_data(self) -> None:
        print("Preparing data...")
        date_now = datetime.now(tz=self.tz).replace(second=0, microsecond=0,minute=0)
        start_date = date_now - timedelta(hours=self.bar_range)
        
        data = vbt.BinanceData.fetch(
            self.symbol.upper(),
            start=start_date,
            end=date_now,
            timeframe="1 hours",
            tz="Asia/Bangkok",
        )
        self.data = data.data[self.symbol.upper()]
        self.data.index = self.data.index.rename('Datetime')

        if self.sql:
            self.data.to_sql('opusdt', engine, if_exists='append')
    
    def msg_to_dataframe(self, info: dict, interval: str) -> pd.DataFrame:
        
        cur_datetime = datetime.fromtimestamp(info['t']/1000, tz=self.tz)
        df = pd.DataFrame([info])
        # print(df)
        df = df.drop(['T','t', 's', 'i', 'f', 'L', 'x', 'B'], axis=1)
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
        
        if self.sql:
            df.to_sql(f'opusdt_{interval}', engine, if_exists='append')
            
        return df
    
    def update_dataframe(self, lastest_df: pd.DataFrame) -> None:
        self.data = pd.concat([self.data, lastest_df])
        self.data = self.data[-self.bar_range:]
        # print(self.data)
    
    async def handle_kline_1h_message(self, message) -> None:
        msg = json.loads(message)
        # ref https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#klinecandlestick-streams
        bar = msg['k']
        is_close = bar['x']
        high_1_tick = bar["h"]
        low_1_tick = bar["l"]
        
        if is_close:
            cur_date = datetime.fromtimestamp(bar['t']/1000, tz=self.tz)
            
            # Update dataframe
            # print('Update...')
            df = self.msg_to_dataframe(info=bar, interval="1h")
            self.update_dataframe(lastest_df=df)
            
            # Place orders if possible
            self.strategy.execute_order(
                open_price=self.data["Open"].iloc[-1],
                close_price=self.data["Close"].iloc[-1],
                high_price=self.data["High"].iloc[-1],
                low_price=self.data["Low"].iloc[-1],
                trade=self.trade
            )

            # Calculate indicators
            self.strategy.compute_signal(
                close_price=self.data['Close'],
                high_price=self.data['High'],
                low_price=self.data['Low'],
            )
            
            self.strategy.condition(close_price=self.data["Close"].iloc[-1])

            print(self.data.index[-1])
            print("Open",self.data["Open"].iloc[-1])
            print("High",self.data["High"].iloc[-1])
            print("Low",self.data["Low"].iloc[-1])
            print("Close",self.data["Close"].iloc[-1])
            if(len(self.strategy.save) != 0):
                action = self.strategy.save.pop(0)
            else:
                action = "None"
            
            # write to csv 
            to_write = [self.data.index[-1],action, self.data["Open"].iloc[-1],
                        self.data["High"].iloc[-1], self.data["Low"].iloc[-1],
                        self.data["Close"].iloc[-1], self.strategy.ema, self.strategy.ema_short,
                        self.strategy.plusDI,self.strategy.minusDI]
            with open('trade_data.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(to_write)

            # print(self.strategy.short_take_profit,self.strategy.short_stop_loss,self.strategy.short_trail_stop_activate,self.strategy.short_trail_stop_execute)
            # print(self.strategy.port.port)
            print("--------------------------")
            # Create order for next bar
            # self.indicators.calculate_order(cur_date=cur_date)
        else:
            if(self.strategy.port.get_position() > 0):
                self.strategy.long_tp_sl_ts(high_price=high_1_tick,low_price=low_1_tick)
            elif (self.strategy.port.get_position() < 0):
                self.strategy.short_tp_sl_ts(high_price=high_1_tick,low_price=low_1_tick)

    async def handle_kline_1s_message(self, message):
        # print(f'Trade message received')
        msg = json.loads(message)
        bar = msg['k']
        is_close = bar['x']
        if is_close:
            df = self.msg_to_dataframe(info=bar, interval="1m")
        
    async def handle_user_data(self, message):
        msg = json.loads(message)
        if msg['e'] == 'outboundAccountInfo': # all account info
            print(msg)

    async def handle_socket(self, uri):
        async with websockets.connect(uri) as websocket:
            if 'kline_1h' in uri:
                handle_message = self.handle_kline_1h_message
            elif 'kline_1s' in uri:
                handle_message = self.handle_kline_1s_message
            elif 'userData' in uri:
                handle_message = self.handle_user_data
            async for message in websocket:
                await handle_message(message)

    async def run(self):
        await asyncio.wait([self.handle_socket(uri) for uri in self.connections])

if __name__ == '__main__':
    handler = BinanceWebsocketHandler(
        symbol='opusdt',
        interval='1h',
        trade=True,
        bar_range=250,
        sql=False
    )
    asyncio.get_event_loop().run_until_complete(handler.run())