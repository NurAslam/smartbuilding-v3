from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Any, Dict, List
from fastapi import HTTPException
from joblib import dump as joblib_dump, load as joblib_load

ARTIFACTS_DIR = "./artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def _model_dir(mid: str) -> str:
    return os.path.join(ARTIFACTS_DIR, mid)


def save_artifacts(
    model_id: str,
    best_model_name: str,
    final_model,
    metrics,
    feature_cols,
    building_info,
    chosen_metric,
    energy_state,
    dataset_bytes: bytes,
    app_version: str) -> None:
    d = _model_dir(model_id)
    os.makedirs(d, exist_ok=True)

    # simpan dataset mentah
    with open(os.path.join(d, "dataset.csv"), "wb") as f:
        f.write(dataset_bytes)

    # >>> SEMUA model (termasuk “LSTM” palsu) disimpan via joblib
    model_path = os.path.join(d, "model.joblib")
    joblib_dump(final_model, model_path)

    # energy regressor & meta (tetap seperti semula)
    if energy_state.get("energy_regressor") is not None:
        joblib_dump(energy_state["energy_regressor"], os.path.join(d, "energy_lr.joblib"))
    energy_meta = {
        "energy_min": energy_state.get("energy_min"),
        "energy_max": energy_state.get("energy_max"),
        "temp_min": energy_state.get("temp_min"),
        "temp_max": energy_state.get("temp_max"),
    }
    with open(os.path.join(d, "energy_meta.json"), "w") as f:
        json.dump(energy_meta, f, indent=2)

    meta = {
        "model_id": model_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "chosen_model": best_model_name,
        "chosen_metric": chosen_metric,
        "metrics": metrics,
        "feature_cols": feature_cols,
        "building_info": building_info,
        "app_version": app_version,
    }
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def load_artifacts(model_id: str) -> Dict[str, Any]:
    d = _model_dir(model_id)
    if not os.path.isdir(d):
        raise HTTPException(status_code=404, detail="model_id tidak ditemukan.")

    with open(os.path.join(d, "meta.json"), "r") as f:
        meta = json.load(f)

    # >>> SELALU load joblib (untuk semua model termasuk 'LSTM' palsu)
    model_path = os.path.join(d, "model.joblib")
    if not os.path.exists(model_path):
        raise HTTPException(status_code=500, detail="Artifact model.joblib hilang atau model lama (TensorFlow) tidak didukung di server ini.")
    final_model = joblib_load(model_path)

    with open(os.path.join(d, "energy_meta.json"), "r") as f:
        energy_meta = json.load(f)
    energy_lr_path = os.path.join(d, "energy_lr.joblib")
    energy_lr = joblib_load(energy_lr_path) if os.path.exists(energy_lr_path) else None

    return {
        "meta": meta,
        "final_model": final_model,
        "energy_regressor": energy_lr,
        "energy_min": energy_meta.get("energy_min"),
        "energy_max": energy_meta.get("energy_max"),
        "temp_min": energy_meta.get("temp_min"),
        "temp_max": energy_meta.get("temp_max"),
    }



def list_artifacts() -> List[Dict[str, Any]]:
    items = []
    for mid in sorted(os.listdir(ARTIFACTS_DIR)):
        d = _model_dir(mid)
        meta_path = os.path.join(d, "meta.json")
        if os.path.isdir(d) and os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                info = meta.get("building_info") or {}
                ceiling_val = info.get("jenis_ceiling") or info.get("construction")

                items.append({
                    "model_id": meta.get("model_id"),
                    "created_at": meta.get("created_at"),
                    "building_name": info.get("name"),
                    "building_type": ceiling_val,
                    "chosen_model": meta.get("chosen_model"),
                    "chosen_metric": meta.get("chosen_metric"),
                })
            except Exception:
                continue
    return items


def delete_artifacts(model_id: str) -> None:
    import shutil
    d = _model_dir(model_id)
    if not os.path.isdir(d):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="model_id tidak ditemukan.")
    shutil.rmtree(d)
