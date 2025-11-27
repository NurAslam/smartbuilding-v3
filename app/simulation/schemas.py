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


# ======================== Forecasting Schemas ========================

class ForecastResponse(BaseModel):
    """Response untuk forecast endpoints"""
    granularity: str  # "daily", "weekly", "monthly"
    forecast_hours: Optional[int] = None  # untuk daily
    forecast_days: Optional[int] = None  # untuk weekly/monthly
    forecast: List[float]  # array of predicted values
    model_used: str  # "LSTM" atau "RNN"
    ref_datetime: Optional[str] = None  # untuk daily (ISO format)
    ref_date: Optional[str] = None  # untuk weekly/monthly (YYYY-MM-DD)
    forecast_start: str  # ISO datetime atau date
    forecast_end: str  # ISO datetime atau date
    forecast_days_labels: Optional[List[str]] = None  # day names untuk weekly


class ModelDetail(BaseModel):
    model_id: str
    created_at: str
    building_info: Dict[str, Any]
    chosen_model: str
    chosen_metric: str
    metrics: Dict[str, Dict[str, float]]
    feature_cols: List[str]
    app_version: str
