"""Turn raw flight + weather rows into the numeric columns the model learns from.

The same function is used for training and for live predictions, so the model
always sees features built exactly the same way.
"""
import pandas as pd

NUMERIC = ["HOUR", "DOW", "MONTH", "DISTANCE", "TEMP_F", "PRECIP_IN", "WIND_KT", "VIS_MI", "THUNDER"]
CATEGORICAL = ["OP_CARRIER", "DEST"]


def build_features(df: pd.DataFrame, categories: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (feature table, category lists).

    Pass the category lists saved at training time when predicting, so a
    carrier or airport always maps to the same column.
    """
    out = df.copy()
    dates = pd.to_datetime(out["FL_DATE"])
    out["DOW"] = dates.dt.dayofweek
    out["MONTH"] = dates.dt.month
    if categories is None:
        categories = {col: sorted(out[col].astype(str).unique()) for col in CATEGORICAL}
    for col in CATEGORICAL:
        out[col] = pd.Categorical(out[col].astype(str), categories=categories[col])
    X = pd.get_dummies(out[NUMERIC + CATEGORICAL], columns=CATEGORICAL, dtype=int)
    return X, categories
