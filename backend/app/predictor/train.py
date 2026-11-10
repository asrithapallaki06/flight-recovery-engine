"""Train the delay model and compare it to a simple baseline.

Run directly:  python -m app.predictor.train

The baseline guesses each flight's delay chance from the average delay rate for
its departure hour. If XGBoost can't beat that, the model isn't worth using, so
we always report both.
"""
import json

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score
from xgboost import XGBClassifier

from app.config import MODEL_META_PATH, MODEL_PATH
from app.data.loader import load_training_frame
from app.predictor.features import build_features


def main() -> dict:
    df = load_training_frame().sort_values("FL_DATE")
    # Time-based split: train on earlier days, test on later days, like real life.
    days = sorted(df["FL_DATE"].unique())
    cutoff = days[int(len(days) * 0.8)]
    train, test = df[df["FL_DATE"] < cutoff], df[df["FL_DATE"] >= cutoff]

    X_train, categories = build_features(train)
    X_test, _ = build_features(test, categories)
    y_train, y_test = train["DEP_DEL15"].astype(int), test["DEP_DEL15"].astype(int)

    model = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                          subsample=0.9, colsample_bytree=0.9, eval_metric="logloss")
    model.fit(X_train, y_train)
    p_model = model.predict_proba(X_test)[:, 1]

    hourly_rate = train.groupby("HOUR")["DEP_DEL15"].mean()
    p_base = test["HOUR"].map(hourly_rate).fillna(y_train.mean()).to_numpy()

    metrics = {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_delay_rate": round(float(y_test.mean()), 3),
        "model_auc": round(float(roc_auc_score(y_test, p_model)), 3),
        "baseline_auc": round(float(roc_auc_score(y_test, p_base)), 3),
        "model_brier": round(float(brier_score_loss(y_test, p_model)), 4),
        "baseline_brier": round(float(brier_score_loss(y_test, p_base)), 4),
    }
    model.save_model(MODEL_PATH)
    MODEL_META_PATH.write_text(json.dumps({
        "categories": categories,
        "columns": list(X_train.columns),
        "metrics": metrics,
    }, indent=2))
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    np.random.seed(0)
    main()
