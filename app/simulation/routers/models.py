from fastapi import APIRouter, Path
from typing import List
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
