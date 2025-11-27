from __future__ import annotations
import numpy as np
from typing import Dict

from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from xgboost import XGBRegressor

# evaluasi tetap dari modulmu yang lama
from .comfort import evaluate_cont
from .model_params import MODEL_PARAMS


def train_and_eval_all(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test:  np.ndarray,
    y_test:  np.ndarray,
) -> Dict[str, Dict]:
    """Latih beberapa regresor pada holdout, kembalikan metrics dan residuals.
    
    Returns:
        Dict dengan struktur:
        {
            "LinearRegression": {
                "RMSE": float, "MSE": float, "MAPE": float,
                "residuals": list of errors per sample
            },
            ...
        }
    """
    metrics: Dict[str, Dict] = {}
    # Build and fit requested models. We follow the user's explicit list:
    # Linear Regression, Decision Tree, KNN, SVM, Random Forest, XGBoost

    # Linear Regression
    lr_params = MODEL_PARAMS.get("LinearRegression", {})
    lr = LinearRegression(**lr_params)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    metrics["LinearRegression"] = evaluate_cont(y_test, y_pred_lr)
    metrics["LinearRegression"]["residuals"] = np.abs(y_test - np.clip(y_pred_lr, -3, 3)).tolist()

    # Decision Tree
    dt_params = MODEL_PARAMS.get("DecisionTree", {})
    dt = DecisionTreeRegressor(**dt_params)
    dt.fit(X_train, y_train)
    y_pred_dt = dt.predict(X_test)
    metrics["DecisionTree"] = evaluate_cont(y_test, y_pred_dt)
    metrics["DecisionTree"]["residuals"] = np.abs(y_test - np.clip(y_pred_dt, -3, 3)).tolist()

    # KNN (scale inputs)
    knn_params = MODEL_PARAMS.get("KNN", {})
    knn = Pipeline([("scaler", StandardScaler()), ("model", KNeighborsRegressor(**knn_params))])
    knn.fit(X_train, y_train)
    y_pred_knn = knn.predict(X_test)
    metrics["KNN"] = evaluate_cont(y_test, y_pred_knn)
    metrics["KNN"]["residuals"] = np.abs(y_test - np.clip(y_pred_knn, -3, 3)).tolist()

    # SVM (SVR) (scale inputs)
    svm_params = MODEL_PARAMS.get("SVM", {})
    svm = Pipeline([("scaler", StandardScaler()), ("model", SVR(**svm_params))])
    svm.fit(X_train, y_train)
    y_pred_svm = svm.predict(X_test)
    metrics["SVM"] = evaluate_cont(y_test, y_pred_svm)
    metrics["SVM"]["residuals"] = np.abs(y_test - np.clip(y_pred_svm, -3, 3)).tolist()

    # Random Forest
    rf_params = MODEL_PARAMS.get("RandomForest", {})
    rf = RandomForestRegressor(**rf_params)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    metrics["RandomForest"] = evaluate_cont(y_test, y_pred_rf)
    metrics["RandomForest"]["residuals"] = np.abs(y_test - np.clip(y_pred_rf, -3, 3)).tolist()

    # XGBoost
    xgb_params = MODEL_PARAMS.get("XGBoost", {})
    xgb = XGBRegressor(**xgb_params)
    xgb.fit(X_train, y_train)
    y_pred_xgb = xgb.predict(X_test)
    metrics["XGBoost"] = evaluate_cont(y_test, y_pred_xgb)
    metrics["XGBoost"]["residuals"] = np.abs(y_test - np.clip(y_pred_xgb, -3, 3)).tolist()

    return metrics


def refit_final_model(best_model_name: str, X_full: np.ndarray, y_full: np.ndarray):
    """Refit model terbaik pada seluruh data dan kembalikan model final.

    Nama `best_model_name` harus salah satu dari:
    "LinearRegression", "DecisionTree", "KNN", "SVM", "RandomForest", "XGBoost".
    """

    if best_model_name == "LinearRegression":
        params = MODEL_PARAMS.get("LinearRegression", {})
        model = LinearRegression(**params)
        model.fit(X_full, y_full)
        return model

    if best_model_name == "DecisionTree":
        params = MODEL_PARAMS.get("DecisionTree", {})
        model = DecisionTreeRegressor(**params)
        model.fit(X_full, y_full)
        return model

    if best_model_name == "KNN":
        params = MODEL_PARAMS.get("KNN", {})
        model = Pipeline([("scaler", StandardScaler()), ("model", KNeighborsRegressor(**params))])
        model.fit(X_full, y_full)
        return model

    if best_model_name == "SVM":
        params = MODEL_PARAMS.get("SVM", {})
        model = Pipeline([("scaler", StandardScaler()), ("model", SVR(**params))])
        model.fit(X_full, y_full)
        return model

    if best_model_name == "RandomForest":
        params = MODEL_PARAMS.get("RandomForest", {})
        model = RandomForestRegressor(**params)
        model.fit(X_full, y_full)
        return model

    if best_model_name == "XGBoost":
        params = MODEL_PARAMS.get("XGBoost", {})
        model = XGBRegressor(**params)
        model.fit(X_full, y_full)
        return model

    raise ValueError(f"Unknown model name: {best_model_name}")
