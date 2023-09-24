# import vectorbtpro as vbt
from typing import List

import numpy as np
import pandas as pd
import pandas_ta as ta


def ta_change(series: pd.Series, period: int = 1) -> pd.Series:
    return series - series.shift(period)


def calculate_plus_dm(upMove: pd.Series, downMove: pd.Series) -> pd.Series:
    plusDM = pd.Series(np.nan, index=upMove.index)
    positive_move = (upMove > downMove) & (upMove > 0)
    plusDM[positive_move] = upMove[positive_move]
    plusDM = plusDM.fillna(0)
    return plusDM


def calculate_minus_dm(upMove: pd.Series, downMove: pd.Series) -> pd.Series:
    minusDM = pd.Series(np.nan, index=upMove.index)
    negative_move = (downMove > upMove) & (downMove > 0)
    minusDM[negative_move] = downMove[negative_move]
    minusDM = minusDM.fillna(0)
    return minusDM


def true_range_rma(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    tr = ta.true_range(high=high, low=low, close=close)
    trur = ta.rma(close=tr, length=period)
    return trur


def DX(
    plusDM: pd.Series, minusDM: pd.Series, trur: pd.Series, period: int = 14
) -> List[pd.Series]:
    # rma_plusDM = vbt.pandas_ta("RMA").run(plusDM, length=period)
    # rma_minusDM = vbt.pandas_ta("RMA").run(minusDM, length=period)
    rma_plusDM = ta.rma(close=plusDM, length=period)
    rma_minusDM = ta.rma(close=minusDM, length=period)

    plusDI = 100 * rma_plusDM / trur
    minusDI = 100 * rma_minusDM / trur

    # dx_rma = vbt.pandas_ta("RMA").run(
    #     abs(plusDI - minusDI) / (plusDI + minusDI), length=period
    # )
    dx_rma = ta.rma(close=abs(plusDI - minusDI) / (plusDI + minusDI), length=period)
    dx = 100 * dx_rma
    return dx, plusDI, minusDI


def ADX(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> List[pd.Series]:
    upMove = ta_change(high)
    downMove = -ta_change(low)
    plusDM = calculate_plus_dm(upMove, downMove)
    minusDM = calculate_minus_dm(upMove, downMove)
    trur = true_range_rma(high, low, close, period)
    dx, plusDI, minusDI = DX(plusDM, minusDM, trur, period)
    # adx = vbt.pandas_ta("RMA").run(dx, length=14)
    adx = ta.rma(close=dx, length=period)
    return adx, plusDI, minusDI
