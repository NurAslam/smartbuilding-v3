from __future__ import annotations

# Default hyper-parameters for available regressors.
# Keputusan parameter bersifat bebas sesuai permintaan — dapat diubah nanti tanpa
# menyentuh logika training/evaluasi.

MODEL_PARAMS = {
    "LinearRegression": {},

    "DecisionTree": {
        "random_state": 42,
        "max_depth": 200,
    },

    "KNN": {
        "n_neighbors": 5,
        "weights": "uniform",
        "algorithm": "auto",
    },

    "SVM": {
        "C": 1.0,
        "epsilon": 0.1,
        "kernel": "rbf",
    },

    "RandomForest": {
        "n_estimators": 100,
        "max_depth": None,
        "random_state": 42,
        "n_jobs": -1,
    },

    "XGBoost": {
        "objective": "reg:squarederror",
        "n_estimators": 100,
        "max_depth": 3,
        "learning_rate": 0.1,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "reg_lambda": 1.0,
        "n_jobs": -1,
        "random_state": 42,
        "eval_metric": "rmse",
    },
}
