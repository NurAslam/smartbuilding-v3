from __future__ import annotations
import numpy as np
import math
from typing import Dict
from sklearn.neural_network import MLPRegressor

def clip01(x):
    return np.clip(x, 0.0, 1.0)


def compute_comfort_weighted(temp: np.ndarray, hum: np.ndarray, wind: np.ndarray, pm: np.ndarray) -> np.ndarray:
    temp_hot  = clip01((temp - 27.0) / 6.0)
    temp_cold = clip01((20.0 - temp) / 5.0)
    humidity_dev = clip01(np.abs(hum - 50.0) / 30.0)
    pm_norm = clip01(pm / 150.0)
    wind_norm = clip01(wind / 8.0)

    wind_effect = - wind_norm * temp_hot + wind_norm * temp_cold
    w_temp, w_hum, w_wind, w_pm = 0.5, 0.2, 0.15, 0.15

    DI = (w_temp * (0.6 * temp_hot + 0.4 * temp_cold) +
          w_hum  * humidity_dev +
          w_pm   * pm_norm +
          w_wind * wind_effect)
    DI = clip01(DI)

    comfort = 3.0 - 6.0 * DI
    return np.clip(comfort, -3.0, 3.0)


def evaluate_cont(y_true: np.ndarray, y_pred_raw: np.ndarray) -> Dict[str, float]:
    from sklearn.metrics import mean_squared_error
    y_pred = np.clip(y_pred_raw, -3, 3)
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(math.sqrt(mse))
    denom = np.where(np.abs(y_true) < 1e-8, np.nan, np.abs(y_true))
    mape = float(np.nanmean(np.abs((y_true - y_pred) / denom) * 100.0))
    if np.isnan(mape): mape = 0.0
    return {"MSE": mse, "RMSE": rmse, "MAPE": mape}

def clamp(x, lo, hi): return max(lo, min(hi, x))


T_NEUTRAL = 24.0               # netral langsung di 24 °C
STEP_DEGC_PER_INDEX = 2.0      # 2°C = 1 tingkat indeks
MAX_WIND_EFFECT = 2.0          # m/s


def comfort_index(T_in: float, humidity: float, wind_speed: float) -> float:
    t_eff = T_in + 0.02 * (humidity - 50.0) - 0.5 * clamp(wind_speed, 0.0, MAX_WIND_EFFECT)
    idx = (t_eff - T_NEUTRAL) / STEP_DEGC_PER_INDEX
    return clamp(idx, -3.0, 3.0)


def index_label(idx: float) -> str:
    k = int(round(idx))
    return {
        -3: "sangat dingin",
        -2: "dingin",
        -1: "agak dingin",
         0: "netral (nyaman)",
         1: "agak panas",
         2: "panas",
         3: "sangat panas",
    }[k]

def pmv_to_ppd(pmv: float) -> float:
    val = 100.0 - 95.0 * math.exp(-0.03353 * (pmv ** 4) - 0.2179 * (pmv ** 2))
    return float(max(0.0, min(100.0, val)))
