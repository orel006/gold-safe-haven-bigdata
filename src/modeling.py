"""
Machine Learning Benchmark — ทำนาย gold_safe_haven_success ในวันที่ crisis
=============================================================================
ใช้ TimeSeriesSplit เพื่อลด data leakage (ข้อมูลการเงินมีลำดับเวลา)

เหตุผลที่ใช้ TimeSeriesSplit แทน KFold:
  - ข้อมูลการเงินมีลำดับเวลา ถ้าใช้ KFold ปกติจะเกิด look-ahead bias
  - features จากอนาคตรั่วไหลเข้า training set ทำให้ accuracy เกินจริง
  - TimeSeriesSplit split ตามเวลา: train = อดีต, test = อนาคต

ใช้ sklearn Pipeline ครอบ SimpleImputer + StandardScaler + Model:
  - SimpleImputer เติม missing values ภายใน training fold เท่านั้น
  - StandardScaler fit เฉพาะ training fold เพื่อกัน data leakage
  - ใช้ lag-1 features เพื่อไม่ให้ daily return ของวันเดียวกับ target รั่วเข้าโมเดล
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from src.config import (
    MODEL_RANDOM_SEED,
    PATH_DATA_DASHBOARD,
    PATH_DATA_INTEGRATED,
    PATH_REPORTS,
    PRIMARY_GOLD_TICKER,
    ensure_all_directories,
)

try:
    from xgboost import XGBClassifier

    HAS_XGB = True
except Exception:
    HAS_XGB = False


RAW_FEATURE_COLUMNS = [
    "daily_return",
    "spy_daily_return",
    "rolling_volatility_21d",
    "rolling_volatility_63d",
    "drawdown",
    "rolling_corr_gold_spy_90d",
    "vix_level",
    "recession_flag",
    "inflation_yoy",
    "fed_rate",
    "treasury_10y",
    "real_yield",
    "breakeven_inflation",
    "dollar_index",
]


def build_training_table(labeled: pd.DataFrame) -> pd.DataFrame:
    """
    สร้าง training table จากแถวของทอง โดยใช้ feature lag 1 วัน
    เพื่อหลีกเลี่ยง leakage จาก return วันเดียวกับ target
    """
    g = labeled[labeled["asset"] == PRIMARY_GOLD_TICKER].copy()
    g = g.sort_values("date").drop_duplicates("date")

    spy_r = labeled[labeled["asset"] == "SPY"][["date", "daily_return"]].drop_duplicates("date")
    spy_r = spy_r.rename(columns={"daily_return": "spy_daily_return"})
    g = g.merge(spy_r, on="date", how="left")

    # alias macro ถ้ายังเป็นชื่อ FRED
    if "vix_level" not in g.columns and "VIXCLS" in g.columns:
        g["vix_level"] = g["VIXCLS"]
    if "recession_flag" not in g.columns and "USREC" in g.columns:
        g["recession_flag"] = g["USREC"]
    if "fed_rate" not in g.columns and "FEDFUNDS" in g.columns:
        g["fed_rate"] = g["FEDFUNDS"]
    if "treasury_10y" not in g.columns and "DGS10" in g.columns:
        g["treasury_10y"] = g["DGS10"]
    if "real_yield" not in g.columns and "DFII10" in g.columns:
        g["real_yield"] = g["DFII10"]
    if "breakeven_inflation" not in g.columns and "T10YIE" in g.columns:
        g["breakeven_inflation"] = g["T10YIE"]
    if "dollar_index" not in g.columns and "DTWEXBGS" in g.columns:
        g["dollar_index"] = g["DTWEXBGS"]

    lag_cols = []
    for col in RAW_FEATURE_COLUMNS:
        if col in g.columns:
            g[col] = pd.to_numeric(g[col], errors="coerce")
            lag_col = f"{col}_lag1"
            g[lag_col] = g[col].shift(1)
            lag_cols.append(lag_col)

    use_cols = ["date", "gold_safe_haven_success"] + lag_cols
    out = g[use_cols].dropna(subset=["date", "gold_safe_haven_success"]).copy()
    out["gold_safe_haven_success"] = out["gold_safe_haven_success"].astype(int)
    return out.sort_values("date").reset_index(drop=True)


def run_modeling() -> None:
    ensure_all_directories()
    path_in = PATH_DATA_INTEGRATED / "labeled_dataset.parquet"
    if not path_in.exists():
        path_in = PATH_DATA_INTEGRATED / "labeled_dataset.csv"
    if not path_in.exists():
        raise FileNotFoundError("ไม่พบ labeled_dataset — รัน crisis_labeling ก่อน")

    df = pd.read_parquet(path_in) if path_in.suffix == ".parquet" else pd.read_csv(path_in)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    train_df = build_training_table(df)
    if len(train_df) < 50:
        print("[modeling] ข้อมูล crisis+target น้อยเกินไป — ข้ามการเทรน")
        return

    feature_cols = [c for c in train_df.columns if c not in ["date", "gold_safe_haven_success"]]
    X_df = train_df[feature_cols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    X = X_df.values
    y = train_df["gold_safe_haven_success"].values

    tscv = TimeSeriesSplit(n_splits=min(5, max(2, len(train_df) // 30)))

    # สร้าง Pipeline: StandardScaler → Model (ป้องกัน data leakage จาก scaling)
    model_defs = {
        "LogisticRegression": LogisticRegression(max_iter=3000, random_state=MODEL_RANDOM_SEED),
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=MODEL_RANDOM_SEED),
    }
    if HAS_XGB:
        model_defs["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9,
            random_state=MODEL_RANDOM_SEED, eval_metric="logloss",
        )
    else:
        model_defs["GradientBoosting"] = GradientBoostingClassifier(random_state=MODEL_RANDOM_SEED)

    # สร้าง sklearn Pipeline ครอบ imputer + scaler + model
    pipelines = {}
    for name, model in model_defs.items():
        pipelines[name] = Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("model", model),
        ])

    # Cross-validation แต่ละโมเดล
    leaderboard_rows = []
    fold_detail_rows = []
    best_name, best_f1 = None, -1.0

    PATH_DATA_DASHBOARD.mkdir(parents=True, exist_ok=True)
    PATH_REPORTS.mkdir(parents=True, exist_ok=True)

    preprocessing_report = pd.DataFrame(
        {
            "feature": feature_cols,
            "missing_count_before_imputer": X_df.isna().sum().values,
            "missing_rate_before_imputer": X_df.isna().mean().values,
            "preprocessing": "SimpleImputer(strategy='median') -> StandardScaler",
            "leakage_control": "lag_1_day_features + TimeSeriesSplit",
        }
    )
    preprocessing_report.to_csv(PATH_DATA_DASHBOARD / "ml_preprocessing_report.csv", index=False, encoding="utf-8-sig")
    preprocessing_report.to_csv(PATH_REPORTS / "ml_preprocessing_report.csv", index=False, encoding="utf-8-sig")

    for name, pipe in pipelines.items():
        print(f"[modeling] Training {name} ...")
        accs, precs, recs, f1s, aucs = [], [], [], [], []
        last_cm = None
        fold = 0

        for train_idx, test_idx in tscv.split(X):
            fold += 1
            pipe.fit(X[train_idx], y[train_idx])
            pred = pipe.predict(X[test_idx])
            prob = pipe.predict_proba(X[test_idx])[:, 1] if hasattr(pipe, "predict_proba") else pred.astype(float)

            acc = accuracy_score(y[test_idx], pred)
            prec = precision_score(y[test_idx], pred, zero_division=0)
            rec = recall_score(y[test_idx], pred, zero_division=0)
            f1 = f1_score(y[test_idx], pred, zero_division=0)
            try:
                auc = roc_auc_score(y[test_idx], prob)
            except Exception:
                auc = np.nan

            accs.append(acc)
            precs.append(prec)
            recs.append(rec)
            f1s.append(f1)
            aucs.append(auc)

            # บันทึก fold detail
            fold_detail_rows.append({
                "model": name, "fold": fold,
                "accuracy": acc, "precision": prec,
                "recall": rec, "f1": f1, "roc_auc": auc,
                "train_size": len(train_idx), "test_size": len(test_idx),
            })

            last_cm = confusion_matrix(y[test_idx], pred)

        mean_f1 = float(np.nanmean(f1s))
        leaderboard_rows.append({
            "model": name,
            "accuracy": float(np.nanmean(accs)),
            "precision": float(np.nanmean(precs)),
            "recall": float(np.nanmean(recs)),
            "f1": mean_f1,
            "roc_auc": float(np.nanmean([a for a in aucs if not np.isnan(a)])) if any(not np.isnan(a) for a in aucs) else np.nan,
            "accuracy_std": float(np.nanstd(accs)),
            "f1_std": float(np.nanstd(f1s)),
        })

        if mean_f1 > best_f1:
            best_f1, best_name = mean_f1, name

        # บันทึก confusion matrix ของโมเดลนี้ (fold สุดท้าย)
        if last_cm is not None:
            cm_df = pd.DataFrame(
                last_cm,
                index=["true_0", "true_1"],
                columns=["pred_0", "pred_1"],
            )
            cm_df.to_csv(PATH_DATA_DASHBOARD / f"confusion_matrix_{name}.csv", encoding="utf-8-sig")

    # บันทึก leaderboard
    res = pd.DataFrame(leaderboard_rows).sort_values("f1", ascending=False)
    res.to_csv(PATH_DATA_DASHBOARD / "ml_leaderboard.csv", index=False, encoding="utf-8-sig")
    res.to_csv(PATH_REPORTS / "model_results.csv", index=False, encoding="utf-8-sig")
    # backward compat
    res.to_csv(PATH_DATA_DASHBOARD / "ml_results.csv", index=False, encoding="utf-8-sig")

    # บันทึก fold detail
    fold_df = pd.DataFrame(fold_detail_rows)
    fold_df.to_csv(PATH_DATA_DASHBOARD / "ml_fold_detail.csv", index=False, encoding="utf-8-sig")

    # Feature importance — ทุกโมเดลที่มี
    for name, pipe in pipelines.items():
        pipe.fit(X, y)
        model_obj = pipe.named_steps["model"]
        if hasattr(model_obj, "feature_importances_"):
            fi = pd.DataFrame({
                "feature": feature_cols,
                "importance": model_obj.feature_importances_,
            }).sort_values("importance", ascending=False)
            fi.to_csv(PATH_DATA_DASHBOARD / f"feature_importance_{name}.csv", index=False, encoding="utf-8-sig")
            # backward compat: ถ้าเป็น RF ให้เขียนไฟล์เดิมด้วย
            if "Random" in name or "Forest" in name:
                fi.to_csv(PATH_DATA_DASHBOARD / "feature_importance.csv", index=False, encoding="utf-8-sig")
        elif hasattr(model_obj, "coef_"):
            fi = pd.DataFrame({
                "feature": feature_cols,
                "importance": np.abs(model_obj.coef_[0]),
            }).sort_values("importance", ascending=False)
            fi.to_csv(PATH_DATA_DASHBOARD / f"feature_importance_{name}.csv", index=False, encoding="utf-8-sig")

    # backward compat: confusion_matrix.csv
    splits = list(tscv.split(X))
    if splits:
        best_pipe = pipelines.get(best_name, list(pipelines.values())[0])
        tr, te = splits[-1]
        best_pipe.fit(X[tr], y[tr])
        pred_te = best_pipe.predict(X[te])
        cm = confusion_matrix(y[te], pred_te)
        pd.DataFrame(cm, index=["true_0", "true_1"], columns=["pred_0", "pred_1"]).to_csv(
            PATH_DATA_DASHBOARD / "confusion_matrix.csv", encoding="utf-8-sig"
        )

    print("[modeling] สรุปโมเดล (TimeSeriesSplit + Pipeline):")
    print(res.to_string(index=False))
    print(f"  โมเดลที่ดีที่สุดจาก F1: {best_name} (F1={best_f1:.4f})")


if __name__ == "__main__":
    run_modeling()
