from __future__ import annotations
import numpy as np
from typing import Any, Dict
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from .comfort import evaluate_cont, make_lstm


def train_and_eval_all(X_train, y_train, X_test, y_test) -> Dict[str, Dict[str, float]]:
    metrics: Dict[str, Dict[str, float]] = {}

    rf = RandomForestRegressor(n_estimators=200, max_depth=None, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    metrics["RF"] = evaluate_cont(y_test, rf.predict(X_test))

    xgb = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=400,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        n_jobs=-1,
        random_state=42,
        eval_metric="rmse",
    )
    xgb.fit(X_train, y_train)
    metrics["XGB"] = evaluate_cont(y_test, xgb.predict(X_test))

    svr = Pipeline([("scaler", StandardScaler()), ("model", SVR(C=10.0, epsilon=0.1, kernel="rbf"))])
    svr.fit(X_train, y_train)
    metrics["SVR"] = evaluate_cont(y_test, svr.predict(X_test))

    # LSTM
    from sklearn.preprocessing import StandardScaler as SKS
    import tensorflow as tf
    scaler_nn = SKS()
    Xtr = scaler_nn.fit_transform(X_train)
    Xte = scaler_nn.transform(X_test)
    Xtr_lstm = Xtr.reshape((-1, 1, Xtr.shape[1]))
    Xte_lstm = Xte.reshape((-1, 1, Xte.shape[1]))
    ytr_lstm, yte_lstm = y_train.copy(), y_test.copy()

    tf.keras.utils.set_random_seed(42)
    lstm = make_lstm(n_features=X_train.shape[1])
    lstm.fit(Xtr_lstm, ytr_lstm, epochs=40, batch_size=16, verbose=0)
    y_pred_lstm = lstm.predict(Xte_lstm, verbose=0).flatten()
    metrics["LSTM"] = evaluate_cont(yte_lstm, y_pred_lstm)

    return metrics


def refit_final_model(best_model_name: str, X_full, y_full):
    if best_model_name == "RF":
        rf_final = RandomForestRegressor(n_estimators=200, max_depth=None, random_state=42, n_jobs=-1)
        rf_final.fit(X_full, y_full)
        return rf_final
    elif best_model_name == "XGB":
        xgb_final = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=400,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            n_jobs=-1,
            random_state=42,
            eval_metric="rmse",
        )
        xgb_final.fit(X_full, y_full)
        return xgb_final
    elif best_model_name == "SVR":
        svr_final = Pipeline([("scaler", StandardScaler()), ("model", SVR(C=10.0, epsilon=0.1, kernel="rbf"))])
        svr_final.fit(X_full, y_full)
        return svr_final
    else:
        from sklearn.preprocessing import StandardScaler
        import tensorflow as tf
        scaler_full = StandardScaler()
        Xs_full = scaler_full.fit_transform(X_full)
        X_full_lstm = Xs_full.reshape((-1, 1, Xs_full.shape[1]))
        tf.keras.utils.set_random_seed(42)
        lstm_full = make_lstm(n_features=X_full.shape[1])
        lstm_full.fit(X_full_lstm, y_full, epochs=40, batch_size=16, verbose=0)
        return {"model": lstm_full, "scaler": scaler_full}
