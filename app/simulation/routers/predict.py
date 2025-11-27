from __future__ import annotations
import numpy as np
from fastapi import APIRouter, HTTPException
from ..schemas import PredictRequest, PredictResponse
from ..state import STATE
from ..domain.surface import resolve_ceiling, surface_ac, surface_non_ac, T_OUT_REF
from ..domain.persistence import load_artifacts
from ..domain.energy import estimate_energy
from app.core.config import settings
from ..domain.comfort import pmv_to_ppd

router = APIRouter(tags=["simulation-predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    used_model_id = None
    best_name = None
    final_model = None
    energy_lr = None
    e_min = e_max = t_min = t_max = None
    building_info = None

    if req.model_id:
        bundle = load_artifacts(req.model_id)
        used_model_id = req.model_id
        meta = bundle["meta"]
        best_name = meta["chosen_model"]
        final_model = bundle["final_model"]
        energy_lr = bundle["energy_regressor"]
        e_min, e_max = bundle["energy_min"], bundle["energy_max"]
        t_min, t_max = bundle["temp_min"], bundle["temp_max"]
        building_info = meta.get("building_info") or {}
    else:
        used_model_id = STATE.get("last_model_id")
        best_name = STATE.get("best_model_name")
        final_model = STATE.get("final_model")
        energy_lr = STATE.get("energy_regressor")
        e_min, e_max = STATE.get("energy_min"), STATE.get("energy_max")
        t_min, t_max = STATE.get("temp_min"), STATE.get("temp_max")
        building_info = STATE.get("building_info") or {}

    if final_model is None or best_name is None:
        raise HTTPException(status_code=400, detail="Belum ada model. Sertakan model_id atau jalankan /analyze dulu.")

    ceiling_name = building_info.get("jenis_ceiling") or building_info.get("construction")
    if not ceiling_name:
        raise HTTPException(status_code=400, detail="Metadata model tidak memiliki 'jenis_ceiling'. Latih ulang lewat /analyze.")
    try:
        resolved_name = resolve_ceiling(ceiling_name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Jenis ceiling pada metadata model tidak valid: '{ceiling_name}'.")

    ac_mode_meta = (building_info.get("ac_mode") or "AC").upper()
    if ac_mode_meta not in ("AC", "NON_AC"):
        ac_mode_meta = "AC"

    # Build temporary state for energy estimate based on loaded artifacts/state
    temp_state = {
        "energy_regressor": energy_lr,
        "energy_min": e_min, "energy_max": e_max,
        "temp_min": t_min, "temp_max": t_max,
    }
    ekwh = float(estimate_energy(req.temp, temp_state))
    cost = float(ekwh * settings.TARIFF_IDR_PER_KWH)
    co2_val = req.co2 if (req.co2 is not None) else 450.0
    if ac_mode_meta == "AC":
        surface_val = surface_ac(req.temp, resolved_name)
    else:
        surface_val = surface_non_ac(T_OUT_REF, resolved_name)

    
    x = np.array([[req.temp, req.humidity, req.wind_speed, req.pm2_5, surface_val, co2_val]], dtype=np.float32)

    # Final model objects are returned consistently (for KNN/SVM we use Pipeline with scaler),
    # so we can call `predict` directly for all supported models.
    y_pred = float(final_model.predict(x)[0])

    ppv_int = int(np.rint(np.clip(y_pred, -3, 3)))
    ppd_val = round(pmv_to_ppd(ppv_int), 2)
    info_out = dict(building_info or {})
    if "type" not in info_out:
        _ = info_out.get("jenis_ceiling")  # keep same behavior

    return PredictResponse(
        model_used=best_name,
        ppv=ppv_int,
        ppd=ppd_val, 
        energy_kwh=round(ekwh, 4),
        cost_idr=round(cost, 2),
        model_id=used_model_id,
        building_info=info_out,
    )
