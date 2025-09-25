from typing import Dict
import math
import numpy as np
from sklearn.metrics import mean_squared_error

def evaluate_cont(y_true: np.ndarray, y_pred_raw: np.ndarray) -> Dict[str, float]:
    """
    Evaluasi regresi untuk target comfort kontinu [-3, 3].
    Mengembalikan MSE, RMSE, dan MAPE (di-guard agar tidak NaN).
    """
    y_pred = np.clip(y_pred_raw, -3, 3)
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(math.sqrt(mse))
    denom = np.where(np.abs(y_true) < 1e-8, np.nan, np.abs(y_true))
    mape = float(np.nanmean(np.abs((y_true - y_pred) / denom) * 100.0))
    if np.isnan(mape):
        mape = 0.0
    return {"MSE": mse, "RMSE": rmse, "MAPE": mape}
