from __future__ import annotations
import uuid
from typing import Literal, Dict
import numpy as np

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..schemas import AnalyzeResponse
from ..state import STATE
from ..domain.surface import resolve_ceiling
from ..domain.preprocessing import clean_and_prepare
from ..domain.energy import fit_energy_regressor
from ..domain.models_ml import train_and_eval_all, refit_final_model
from ..domain.persistence import save_artifacts
from ..domain.io_utils import read_csv_upload_and_bytes

router = APIRouter(tags=["simulation-analyze"])

SIM_APP_VERSION = "1.2.0"


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(..., description="CSV minimal: temp,humidity,wind_speed,pm2_5; opsional: date,EnergyConsumption,SquareFootage"),
    building_name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    ceiling: str = Form(..., description="Nama Ceiling (persis seperti di /list-ceiling, alias didukung)"),
    ac_mode: Literal["AC","NON_AC"] = Form("AC"),
    model_selection_metric: Literal["RMSE", "MSE", "MAPE"] = Form("RMSE"),
    persist: bool = Form(True),
):
    df_raw, csv_bytes = read_csv_upload_and_bytes(file)

    resolved_name = resolve_ceiling(ceiling)
    building_info = {
        "name": building_name,
        "lat": latitude,
        "lon": longitude,
        "jenis_ceiling": resolved_name,
        "ac_mode": ac_mode,
    }
    STATE["building_info"] = building_info

    df = clean_and_prepare(df_raw, ceiling_name=resolved_name, ac_mode=ac_mode)

    feature_cols = ["temp", "humidity", "wind_speed", "pm2_5", "surface_temp"]
    X_full = df[feature_cols].values.astype(np.float32)
    y_full = df["comfort_target"].values.astype(np.float32)

    energy_state = fit_energy_regressor(df)
    STATE.update(energy_state)

    n = len(df)
    if n < 5:
        raise HTTPException(status_code=400, detail="Dataset terlalu sedikit setelah preprocessing (min 5 baris).")
    test_size = max(1, int(0.2 * n))
    train_size = n - test_size
    X_train, y_train = X_full[:train_size], y_full[:train_size]
    X_test,  y_test  = X_full[train_size:], y_full[train_size:]

    metrics: Dict[str, Dict[str, float]] = train_and_eval_all(X_train, y_train, X_test, y_test)

    chosen_metric = model_selection_metric
    best_model_name = min(["RF", "XGB", "SVR", "LSTM"], key=lambda m: metrics[m][chosen_metric])

    final_model = refit_final_model(best_model_name, X_full, y_full)

    model_id = str(uuid.uuid4())
    if persist:
        save_artifacts(
            model_id=model_id,
            best_model_name=best_model_name,
            final_model=final_model,
            metrics=metrics,
            feature_cols=feature_cols,
            building_info=building_info,
            chosen_metric=chosen_metric,
            energy_state=energy_state,
            dataset_bytes=csv_bytes,
            app_version=SIM_APP_VERSION,
        )

    STATE["best_model_name"] = best_model_name
    STATE["final_model"] = final_model
    STATE["metrics"] = metrics
    STATE["feature_cols"] = feature_cols
    STATE["last_model_id"] = model_id

    return AnalyzeResponse(
        feature_cols=feature_cols,
        metrics=metrics,
        chosen_model=best_model_name,
        chosen_metric=chosen_metric,
        model_id=model_id,
    )
