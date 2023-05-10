import pandas as pd
import vectorbtpro as vbt

from pydantic import BaseSettings

from indicators.adx import ADX

class adxSetting(BaseSettings):
    adx_lenght : int = 14
    adx_level : int = 20
    adx_diff : float = 1.0

class emaSetting(BaseSettings):
    ema_length : int = 20
    ema_short_length : int = 10

class rsiSetting(BaseSettings):
    rsi_lenght : int = 14
    overbought_level : int = 70
    oversold_level : int = 30

class stochasticSetting(BaseSettings):
    smooth_k : int = 3
    smooth_d : int = 3
    stochastic_lenght : int = 14
    overbought_level : int = 80
    oversold_level : int = 20

class stopSetting(BaseSettings):
    stop_loss : float = 0.03
    take_profit : float = 0.16
    trail_stop_activate : float = 0.01
    trail_stop_execute : float = 0.001

class Strategy:

    def __init__(
        self,
        adx_setting : adxSetting = adxSetting(),
        ema_setting : emaSetting = emaSetting(),
        rsi_setting : rsiSetting = rsiSetting(),
        stochastic_setting : stochasticSetting = stochasticSetting(),
        sl_tp_ts_setting : stopSetting = stopSetting(),
    ):
        self.adx_setting = adx_setting
        self.ema_setting = ema_setting
        self.rsi_setting = rsi_setting
        self.stochastic_setting = stochastic_setting
        self.sl_tp_ts_setting = sl_tp_ts_setting

    def compute_signal(
        self,
        close_price: pd.Series,
        high_price: pd.Series,
        low_price: pd.Series,
    ):
        adx, plusDI, minusDI = ADX(
            high=high_price,
            low=low_price,
            close=close_price,
            period=self.adx_setting.adx_lenght,
        )

        self.adx = adx.iloc[-1]
        self.plusDI = plusDI.iloc[-1]
        self.minusDI = minusDI.iloc[-1]


        stoch_rsi = vbt.pandas_ta("STOCHRSI").run(
            close_price, 
            length=self.stochastic_setting.stochastic_lenght, 
            rsi_length=self.rsi_setting.rsi_lenght,
            k=self.stochastic_setting.smooth_k,
            d=self.stochastic_setting.smooth_d,
        )
        self.k = stoch_rsi.stochrsid.iloc[-1]
        self.d = stoch_rsi.stochrsik.iloc[-1]

        ema = vbt.pandas_ta("EMA").run(
            close_price, 
            length=self.ema_setting.ema_length,
        )
        self.ema = ema.ema.iloc[-1]
        
        ema_short = vbt.pandas_ta("EMA").run(
            close_price,
            length=self.ema_setting.ema_short_length,
        )

        self.ema_short = ema_short.ema.iloc[-1]

