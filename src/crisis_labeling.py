"""
Crisis Labeling — สร้าง regime crisis vs normal และ target gold safe haven
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from src.config import (
    PATH_DATA_INTEGRATED,
    PATH_REPORTS,
    PRIMARY_GOLD_TICKER,
    VIX_CRISIS_THRESHOLD,
    SPY_DRAWDOWN_CRISIS_THRESHOLD,
    ensure_all_directories,
)


def build_date_level_labels(feat: pd.DataFrame) -> pd.DataFrame:
    """
    สร้างตารางรายวันที่มี crisis flags และ gold_safe_haven_success
    """
    feat = feat.sort_values("date")

    # VIX จากคอลัมน์ FRED เดิม
    vix_col = "VIXCLS" if "VIXCLS" in feat.columns else "vix_level"
    usrec_col = "USREC" if "USREC" in feat.columns else "recession_flag"

    d_vix = feat[["date", vix_col]].drop_duplicates("date").sort_values("date")
    d_vix = d_vix.rename(columns={vix_col: "_vix"})
    d_vix["crisis_by_vix"] = (d_vix["_vix"] >= VIX_CRISIS_THRESHOLD).astype(int)

    d_rec = feat[["date", usrec_col]].drop_duplicates("date").sort_values("date")
    d_rec = d_rec.rename(columns={usrec_col: "_usrec"})
    d_rec["crisis_by_recession"] = (d_rec["_usrec"].fillna(0) >= 1).astype(int)

    spy = feat[feat["asset"] == "SPY"][["date", "drawdown"]].drop_duplicates("date").sort_values("date")
    spy = spy.rename(columns={"drawdown": "spy_drawdown"})
    spy["crisis_by_spy_drawdown"] = (spy["spy_drawdown"] <= SPY_DRAWDOWN_CRISIS_THRESHOLD).astype(int)

    gold = feat[feat["asset"] == PRIMARY_GOLD_TICKER][["date", "daily_return"]].drop_duplicates("date")
    gold = gold.rename(columns={"daily_return": "gold_return"})
    spy_ret = feat[feat["asset"] == "SPY"][["date", "daily_return"]].drop_duplicates("date")
    spy_ret = spy_ret.rename(columns={"daily_return": "spy_return"})

    lab = d_vix[["date", "crisis_by_vix"]].merge(d_rec[["date", "crisis_by_recession"]], on="date", how="outer")
    lab = lab.merge(spy[["date", "crisis_by_spy_drawdown", "spy_drawdown"]], on="date", how="outer")
    lab = lab.merge(gold, on="date", how="left")
    lab = lab.merge(spy_ret, on="date", how="left")

    lab["final_crisis_label"] = (
        (lab["crisis_by_vix"].fillna(0) == 1)
        | (lab["crisis_by_recession"].fillna(0) == 1)
        | (lab["crisis_by_spy_drawdown"].fillna(0) == 1)
    ).astype(int)

    # Target: เฉพาะวันที่ crisis
    def _success_row(r):
        if r["final_crisis_label"] != 1:
            return np.nan
        gr = r["gold_return"]
        sr = r["spy_return"]
        if pd.isna(gr) or pd.isna(sr):
            return np.nan
        if (gr > sr) or ((gr >= 0) and (sr < 0)):
            return 1.0
        return 0.0

    lab["gold_safe_haven_success"] = lab.apply(_success_row, axis=1)
    return lab


def run_crisis_labeling() -> None:
    ensure_all_directories()
    path_in = PATH_DATA_INTEGRATED / "feature_dataset.parquet"
    if not path_in.exists():
        path_in = PATH_DATA_INTEGRATED / "feature_dataset.csv"
    if not path_in.exists():
        raise FileNotFoundError("ไม่พบ feature_dataset — รัน feature_engineering ก่อน")

    feat = pd.read_parquet(path_in) if path_in.suffix == ".parquet" else pd.read_csv(path_in)
    feat["date"] = pd.to_datetime(feat["date"], errors="coerce")

    labels = build_date_level_labels(feat)
    labeled = feat.merge(
        labels[
            [
                "date",
                "crisis_by_vix",
                "crisis_by_recession",
                "crisis_by_spy_drawdown",
                "final_crisis_label",
                "gold_safe_haven_success",
                "spy_drawdown",
            ]
        ],
        on="date",
        how="left",
    )

    # asset outperform ในวัน crisis (เรียงจาก return สูงสุด) — เก็บเฉพาะวันที่ crisis
    crisis_days = labeled[labeled["final_crisis_label"] == 1][["date", "asset", "daily_return"]].copy()

    out_csv = PATH_DATA_INTEGRATED / "labeled_dataset.csv"
    out_pq = PATH_DATA_INTEGRATED / "labeled_dataset.parquet"
    labeled.to_csv(out_csv, index=False, encoding="utf-8-sig")
    labeled.to_parquet(out_pq, index=False, engine="pyarrow")
    print(f"[crisis_labeling] บันทึก {out_pq} ({len(labeled)} rows)")

    # สรุปจำนวนวัน
    u = labels.drop_duplicates("date")
    n_crisis = int((u["final_crisis_label"] == 1).sum())
    n_normal = int((u["final_crisis_label"] == 0).sum())
    u_c = u[u["final_crisis_label"] == 1]
    n_succ = int(u_c["gold_safe_haven_success"].fillna(-1).eq(1).sum())
    n_fail = int(u_c["gold_safe_haven_success"].fillna(-1).eq(0).sum())

    summ = pd.DataFrame(
        [
            {"metric": "crisis_days", "value": n_crisis},
            {"metric": "normal_days", "value": n_normal},
            {"metric": "gold_safe_haven_success_days", "value": n_succ},
            {"metric": "gold_safe_haven_fail_days", "value": n_fail},
        ]
    )
    PATH_REPORTS.mkdir(parents=True, exist_ok=True)
    summ_path = PATH_REPORTS / "crisis_label_summary.csv"
    summ.to_csv(summ_path, index=False, encoding="utf-8-sig")
    print(f"[crisis_labeling] สรุป -> {summ_path}")


if __name__ == "__main__":
    run_crisis_labeling()
