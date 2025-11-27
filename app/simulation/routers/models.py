from fastapi import APIRouter, Path
from typing import List, Dict, Any
import numpy as np
from ..schemas import ModelListItem, ModelDetail
from ..domain.persistence import list_artifacts, load_artifacts, delete_artifacts

router = APIRouter(tags=["simulation-models"])


@router.get("/models", response_model=List[ModelListItem])
def list_models():
    items = list_artifacts()
    items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
    return [ModelListItem(**it) for it in items]


@router.get("/models/{model_id}", response_model=ModelDetail)
def get_model(model_id: str = Path(...)):
    bundle = load_artifacts(model_id)
    meta = bundle["meta"]

    info = dict(meta.get("building_info") or {})
    ceiling_val = info.get("jenis_ceiling") or info.get("construction")
    if ceiling_val:
        info["type"] = ceiling_val

    return ModelDetail(
        model_id=meta["model_id"],
        created_at=meta["created_at"],
        building_info=info,
        chosen_model=meta["chosen_model"],
        chosen_metric=meta["chosen_metric"],
        metrics=meta["metrics"],
        feature_cols=meta["feature_cols"],
        app_version=meta.get("app_version", ""),
    )


@router.delete("/models/{model_id}")
def delete_model(model_id: str = Path(...)):
    delete_artifacts(model_id)
    return {"status": "deleted", "model_id": model_id}


@router.get("/models/{model_id}/boxplot")
def get_model_boxplot(model_id: str = Path(...)) -> Dict[str, Any]:
    """
    Return box plot data (five-number summary) for all models.
    
    Response format:
    {
        "model_id": "...",
        "chosen_metric": "RMSE",
        "data": {
            "LinearRegression": {
                "min": 0.1,
                "q1": 0.3,
                "median": 0.5,
                "q3": 0.7,
                "max": 1.0
            },
            ...
        }
    }
    """
    bundle = load_artifacts(model_id)
    meta = bundle["meta"]
    
    metrics = meta.get("metrics", {})
    
    # Calculate five-number summary for each model from residuals
    boxplot_data = {}
    for model_name, model_metrics in metrics.items():
        residuals = model_metrics.get("residuals", [])
        if residuals:
            residuals_arr = np.array(residuals)
            boxplot_data[model_name] = {
                "min": float(np.min(residuals_arr)),
                "q1": float(np.percentile(residuals_arr, 25)),
                "median": float(np.percentile(residuals_arr, 50)),
                "q3": float(np.percentile(residuals_arr, 75)),
                "max": float(np.max(residuals_arr)),
            }
    
    return {
        "model_id": model_id,
        "chosen_metric": meta.get("chosen_metric", "RMSE"),
        "data": boxplot_data,
    }

