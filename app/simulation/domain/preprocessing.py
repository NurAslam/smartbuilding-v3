from __future__ import annotations
from typing import Optional, Literal
import numpy as np
import pandas as pd
from pandas import Series, DataFrame
from fastapi import HTTPException
from .surface import surface_ac, surface_non_ac, resolve_ceiling, T_OUT_REF


def _get_col_case_insensitive(df: pd.DataFrame, target: str) -> Optional[str]:
    for c in df.columns:
        if c.lower() == target.lower():
            return c
    return None


def derive_surface_series(
    df: DataFrame,
    ceiling_name: str,
    ac_mode: Literal["AC","NON_AC"],
) -> Series:
    """
    Hitung kolom surface_temp. Import fungsi surface dilakukan DI DALAM fungsi
    untuk menghindari circular import dengan surface.py.
    """
    

    name = resolve_ceiling(ceiling_name)

    temp_col = _get_col_case_insensitive(df, "temp")
    if temp_col is None:
        raise HTTPException(400, "Kolom 'temp' (indoor) wajib ada untuk menghitung surface_temp (AC).")

    if ac_mode == "AC":
        return df[temp_col].astype(float).apply(lambda Tin: surface_ac(float(Tin), name))

    out_col = _get_col_case_insensitive(df, "outdoor_temp")
    if out_col is not None:
        return df[out_col].astype(float).apply(lambda Tout: surface_non_ac(float(Tout), name))

    T_out_val = T_OUT_REF
    return pd.Series([surface_non_ac(T_out_val, name) for _ in range(len(df))], index=df.index)


def clean_and_prepare(
    df: DataFrame,
    ceiling_name: str,
    ac_mode: Literal["AC","NON_AC"],
) -> DataFrame:
    from .comfort import compute_comfort_weighted

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for c in ["EnergyConsumption", "SquareFootage"]:
        if c not in df.columns:
            df[c] = np.nan

    exog_base = ["temp", "humidity", "wind_speed", "pm2_5"]
    missing = [c for c in exog_base if _get_col_case_insensitive(df, c) is None]
    if missing:
        raise HTTPException(400, f"Kolom wajib hilang: {missing}. Minimal: {exog_base}")

    temp_c  = _get_col_case_insensitive(df, "temp")
    hum_c   = _get_col_case_insensitive(df, "humidity")
    wind_c  = _get_col_case_insensitive(df, "wind_speed")
    pm_c    = _get_col_case_insensitive(df, "pm2_5")
    co2_c    = _get_col_case_insensitive(df, "co2")
    if co2_c is None:
        df['co2'] = 450.0
    else:
        df['co2'] = df[co2_c].astype(float)
    
    df = df.dropna(subset=[temp_c, hum_c, wind_c, pm_c, co2_c]).copy()

    cscore = compute_comfort_weighted(
        df[temp_c].to_numpy(dtype=float),
        df[hum_c].to_numpy(dtype=float),
        df[wind_c].to_numpy(dtype=float),
        df[pm_c].to_numpy(dtype=float),
        df[co2_c].to_numpy(dtype=float),
    )
    df["comfort_target"] = cscore.astype(np.float32)

    df["surface_temp"] = derive_surface_series(df, ceiling_name, ac_mode).astype(float)

    if "date" in df.columns:
        df = df.sort_values("date")

    df = df.rename(columns={
        temp_c: "temp",
        hum_c: "humidity",
        wind_c: "wind_speed",
        pm_c: "pm2_5",
        co2_c: "co2"
    })

    return df.reset_index(drop=True)
