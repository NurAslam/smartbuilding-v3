from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    feature_cols: List[str]
    metrics: Dict[str, Dict[str, float]]
    chosen_model: str
    chosen_metric: str
    model_id: str


class PredictRequest(BaseModel):
    temp: float
    humidity: float
    wind_speed: float
    pm2_5: float
    co2 : Optional[float]  = None
    model_id: Optional[str] = None
    square_footage: Optional[float] = None


class PredictResponse(BaseModel):
    model_used: str
    ppv: int
    ppd: float
    energy_kwh: float
    cost_idr: float
    model_id: Optional[str] = None
    building_info: Dict[str, Any]


class ModelListItem(BaseModel):
    model_id: str
    created_at: str
    building_name: Optional[str]
    building_type: Optional[str]
    chosen_model: str
    chosen_metric: str


class SurfaceComfortResponse(BaseModel):
    ceiling: str
    T_out: float
    T_in: float
    surface_non_ac: float
    surface_ac: float
    index: float
    label: str


class ModelDetail(BaseModel):
    model_id: str
    created_at: str
    building_info: Dict[str, Any]
    chosen_model: str
    chosen_metric: str
    metrics: Dict[str, Dict[str, float]]
    feature_cols: List[str]
    app_version: str
