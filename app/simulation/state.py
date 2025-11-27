from typing import Any, Dict, List

STATE: Dict[str, Any] = {
    "best_model_name": None,     # "LinearRegression" | "DecisionTree" | "KNN" | "SVM" | "RandomForest" | "XGBoost"
    "final_model": None,         # model for inference
    "feature_cols": ["temp", "humidity", "wind_speed", "pm2_5", "co2","surface_temp"],
    "metrics": {},
    "building_info": {},
    "energy_regressor": None,    # LinearRegression
    "energy_min": None,
    "energy_max": None,
    "temp_min": None,
    "temp_max": None,
    "last_model_id": None,
}
