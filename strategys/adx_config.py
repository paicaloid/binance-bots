from pydantic import BaseSettings


class adxSetting(BaseSettings):
    adx_lenght: int = 14
    adx_level: int = 20
    adx_diff: float = 1.0


class emaSetting(BaseSettings):
    ema_length: int = 20
    ema_short_length: int = 10


class rsiSetting(BaseSettings):
    rsi_lenght: int = 14
    overbought_level: int = 70
    oversold_level: int = 30


class stochasticSetting(BaseSettings):
    smooth_k: int = 3
    smooth_d: int = 3
    stochastic_lenght: int = 14
    overbought_level: int = 80
    oversold_level: int = 20


class stopSetting(BaseSettings):
    stop_loss: float = 0.03
    take_profit: float = 0.06
    trail_stop_activate: float = 0.01
    trail_stop_execute: float = 0.001
