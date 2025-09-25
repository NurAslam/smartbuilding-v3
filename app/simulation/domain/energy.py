from __future__ import annotations
from typing import Any, Dict
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def fit_energy_regressor(df: pd.DataFrame) -> Dict[str, Any]:
    out = {"energy_regressor": None, "energy_min": None, "energy_max": None, "temp_min": None, "temp_max": None}
    if "EnergyConsumption" in df.columns and df["EnergyConsumption"].notna().any():
        valid = df[["temp", "EnergyConsumption"]].dropna()
        if len(valid) >= 5 and valid["EnergyConsumption"].std() > 0:
            lr = LinearRegression()
            lr.fit(valid[["temp"]].values, valid["EnergyConsumption"].values)
            out["energy_regressor"] = lr
            out["energy_min"] = float(valid["EnergyConsumption"].min())
            out["energy_max"] = float(valid["EnergyConsumption"].max())
            out["temp_min"] = float(valid["temp"].min())
            out["temp_max"] = float(valid["temp"].max())
            return out
    out["temp_min"] = float(df["temp"].min())
    out["temp_max"] = float(df["temp"].max())
    out["energy_min"] = 0.0
    out["energy_max"] = 1.0
    return out


def estimate_energy(temp_value: float, state_dict: Dict[str, Any]) -> float:
    lr = state_dict.get("energy_regressor")
    if lr is not None:
        return float(max(lr.predict(np.array([[temp_value]]))[0], 0.0))
    tmin, tmax = state_dict.get("temp_min"), state_dict.get("temp_max")
    emin, emax = state_dict.get("energy_min"), state_dict.get("energy_max")
    if tmin is None or tmax is None or abs(tmax - tmin) < 1e-8:
        return float(emin or 0.0)
    ratio = float(np.clip((temp_value - tmin) / (tmax - tmin), 0.0, 1.0))
    return float(emin + ratio * (emax - emin))
