import vectorbtpro as vbt
import numpy as np
import pandas as pd

from typing import List

def ta_change(series: pd.Series, period: int = 1) -> pd.Series:
    return (series - series.shift(period))

def calculate_plus_dm(upMove: pd.Series, downMove: pd.Series) -> pd.Series:
    plusDM = pd.Series(np.nan, index=upMove.index)  # Initialize the result Series with NaN values
    positive_move = (upMove > downMove) & (upMove > 0)  # Check if upMove is greater than downMove and greater than 0
    plusDM[positive_move] = upMove[positive_move]  # Assign the positive price movement to plusDM where the condition is true
    plusDM = plusDM.fillna(0)
    return plusDM

def calculate_minus_dm(upMove: pd.Series, downMove: pd.Series) -> pd.Series:
    minusDM = pd.Series(np.nan, index=upMove.index)  # Initialize the result Series with NaN values
    negative_move = (downMove > upMove) & (downMove > 0)  # Check if downMove is greater than upMove and greater than 0
    minusDM[negative_move] = downMove[negative_move]  # Assign the negative price movement to minusDM where the condition is true
    minusDM = minusDM.fillna(0)
    return minusDM

def true_range_rma(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = vbt.pandas_ta("TRUE_RANGE").run(high, low, close)
    trur = vbt.pandas_ta("RMA").run(tr.truerange, length=period)
    return trur.rma

def DX(plusDM: pd.Series, minusDM: pd.Series, trur: pd.Series, period: int = 14) -> List[pd.Series]:
    rma_plusDM = vbt.pandas_ta("RMA").run(plusDM, length=period)
    rma_minusDM = vbt.pandas_ta("RMA").run(minusDM, length=period)
    
    plusDI = 100 * rma_plusDM.rma / trur
    minusDI = 100 * rma_minusDM.rma / trur
    
    dx_rma = vbt.pandas_ta("RMA").run(abs(plusDI - minusDI) / (plusDI + minusDI), length=period)
    dx = 100 * dx_rma.rma
    return dx, plusDI, minusDI

def ADX(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> List[pd.Series]:
    upMove = ta_change(high)
    downMove = - ta_change(low)
    plusDM = calculate_plus_dm(upMove, downMove)
    minusDM = calculate_minus_dm(upMove, downMove)
    trur = true_range_rma(high, low, close, period)
    dx, plusDI, minusDI = DX(plusDM, minusDM, trur, period)
    adx = vbt.pandas_ta("RMA").run(dx, length=14)
    return adx.rma, plusDI, minusDI