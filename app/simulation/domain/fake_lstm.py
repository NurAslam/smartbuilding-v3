"""
This module used to provide a fake LSTM (MLP-based) regressor used by older
code paths. The project no longer uses the fake LSTM; model implementations
were replaced with conventional scikit-learn / xgboost regressors. The file
is kept as a harmless stub to avoid accidental import errors from out-of-date
artifacts, but it contains no active model implementation.

Do not use; remove this file if you are sure no external artifacts reference it.
"""

def make_lstm(*args, **kwargs):
    raise RuntimeError("fake_lstm is removed — use the configured sklearn/xgboost models instead")
