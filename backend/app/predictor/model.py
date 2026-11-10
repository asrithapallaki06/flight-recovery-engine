"""Load the trained delay model and score flights with a delay-risk probability."""
import json
from functools import lru_cache

import pandas as pd
from xgboost import XGBClassifier

from app.config import MODEL_META_PATH, MODEL_PATH
from app.predictor import train
from app.predictor.features import build_features


@lru_cache(maxsize=1)
def _load() -> tuple[XGBClassifier, dict]:
    """Load once and reuse. Trains a model first if none exists yet."""
    if not MODEL_PATH.exists() or not MODEL_META_PATH.exists():
        train.main()
    model = XGBClassifier()
    model.load_model(MODEL_PATH)
    meta = json.loads(MODEL_META_PATH.read_text())
    return model, meta


def predict_risk(rows: pd.DataFrame) -> list[float]:
    """Probability (0-1) that each flight departs 15+ minutes late."""
    model, meta = _load()
    X, _ = build_features(rows, meta["categories"])
    X = X.reindex(columns=meta["columns"], fill_value=0)
    return [round(float(p), 3) for p in model.predict_proba(X)[:, 1]]


def model_metrics() -> dict:
    return _load()[1]["metrics"]
