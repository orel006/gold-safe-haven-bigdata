"""
เตรียมข้อมูลสรุปสำหรับ Streamlit Dashboard
============================================
อ่าน output จาก spark_transform.py + feature/labeled datasets
แล้ว copy/สร้าง ไฟล์ทั้งหมดลง data/dashboard/

Dashboard จะอ่านเฉพาะ data/dashboard/ — ไม่อ่าน raw data ตรง ๆ
"""
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from src.config import (
    PATH_DATA_DASHBOARD,
    PATH_DATA_INTEGRATED,
    PATH_DATA_SPARK_OUTPUT,
    PATH_REPORTS,
    PRIMARY_GOLD_TICKER,
    ensure_all_directories,
)


def run_generate_dashboard_data() -> None:
    ensure_all_directories()
    PATH_DATA_DASHBOARD.mkdir(parents=True, exist_ok=True)
    PATH_REPORTS.mkdir(parents=True, exist_ok=True)

    # ── 1) Copy ไฟล์จาก spark_output → dashboard ──
    print("[generate_dashboard_data] 1) Copy spark_transform outputs ...")
    spark_files = [
        "stats_per_asset.csv",
        "stats_per_crisis.csv",
        "stats_crisis_vs_normal.csv",
        "return_ranking.csv",
        "safe_haven_score.csv",
        "safe_haven_ranking.csv",
        "market_breadth.csv",
        "market_breadth_by_group.csv",
        "rolling_corr_multi.csv",
        "risk_detail.csv",
        "bottom_line.csv",
        "transformation_meta.csv",
        "crisis_events.csv",
    ]
    copied = 0
    for fname in spark_files:
        src = PATH_DATA_SPARK_OUTPUT / fname
        dst = PATH_DATA_DASHBOARD / fname
        if src.exists():
            # ใช้ copyfile แทน copy2 เพราะ Docker bind mount บน Windows
            # มักไม่อนุญาตให้ container เปลี่ยน metadata/mtime ของไฟล์ปลายทาง
            shutil.copyfile(src, dst)
            copied += 1
        else:
            print(f"  [WARN] ไม่พบ {src.name} — ข้าม")
    print(f"  Copied {copied}/{len(spark_files)} files")

    # ── 2) สร้างไฟล์เพิ่มเติมจาก feature/labeled datasets ──
    feat_path = PATH_DATA_INTEGRATED / "feature_dataset.parquet"
    lab_path = PATH_DATA_INTEGRATED / "labeled_dataset.parquet"
    master_path = PATH_DATA_INTEGRATED / "master_asset_panel.parquet"

    if not feat_path.exists():
        print("[WARN] ไม่พบ feature_dataset.parquet")
        return
    if not lab_path.exists():
        print("[WARN] ไม่พบ labeled_dataset.parquet")
        return

    feat = pd.read_parquet(feat_path)
    lab = pd.read_parquet(lab_path)
    feat["date"] = pd.to_datetime(feat["date"], errors="coerce")
    lab["date"] = pd.to_datetime(lab["date"], errors="coerce")

    # ── analysis panel สำหรับ interactive dashboard filters ──
    # Dashboard อ่านไฟล์ processed นี้เท่านั้น แล้วค่อย filter ตามช่วงเวลา/asset ใน Streamlit
    print("[generate_dashboard_data] analysis_panel ...")
    analysis_cols = [
        "date", "asset", "group", "open", "high", "low", "close", "adj_close", "volume",
        "daily_return", "log_return", "cumulative_return", "drawdown",
        "rolling_volatility_21d", "rolling_volatility_63d",
        "rolling_corr_gold_spy_30d", "rolling_corr_gold_spy_90d",
        "rolling_corr_gold_tlt_90d", "rolling_corr_gold_uup_90d", "rolling_corr_gold_btc_90d",
        "VIXCLS", "USREC", "vix_level", "recession_flag", "fed_rate", "treasury_10y",
        "real_yield", "breakeven_inflation", "dollar_index", "inflation_yoy",
        "crisis_by_vix", "crisis_by_recession", "crisis_by_spy_drawdown",
        "final_crisis_label", "gold_safe_haven_success", "spy_drawdown",
    ]
    keep_cols = [c for c in analysis_cols if c in lab.columns]
    lab[keep_cols].to_parquet(PATH_DATA_DASHBOARD / "analysis_panel.parquet", index=False)

    # ── asset_summary (crisis vs normal mean return) — backward compat ──
    print("[generate_dashboard_data] 2) asset_summary ...")
    tmp = lab.copy()
    tmp["regime"] = np.where(tmp["final_crisis_label"] == 1, "crisis", "normal")
    g = tmp.groupby(["asset", "regime"])["daily_return"].mean().reset_index()
    g.to_csv(PATH_DATA_DASHBOARD / "asset_summary.csv", index=False, encoding="utf-8-sig")

    # ── crisis_summary (รายวัน) ──
    print("[generate_dashboard_data] 3) crisis_summary ...")
    base_cols = ["date", "final_crisis_label", "gold_safe_haven_success"]
    if "VIXCLS" in lab.columns:
        base_cols.append("VIXCLS")
    u = lab[base_cols].drop_duplicates("date")
    u.to_csv(PATH_DATA_DASHBOARD / "crisis_summary.csv", index=False, encoding="utf-8-sig")

    # ── failure cases ──
    print("[generate_dashboard_data] 4) failure_cases ...")
    gcols = ["date", "gold_safe_haven_success", "daily_return"]
    if "VIXCLS" in lab.columns:
        gcols.append("VIXCLS")
    gold_dates = lab[
        (lab["asset"] == PRIMARY_GOLD_TICKER) & (lab["final_crisis_label"] == 1)
    ][gcols].drop_duplicates("date")
    fails = gold_dates[gold_dates["gold_safe_haven_success"] == 0]
    fails.to_csv(PATH_DATA_DASHBOARD / "failure_cases.csv", index=False, encoding="utf-8-sig")

    # ── price trends ──
    print("[generate_dashboard_data] 5) price_trends ...")
    if master_path.exists():
        m = pd.read_parquet(master_path)
        m["date"] = pd.to_datetime(m["date"], errors="coerce")
        m.to_parquet(PATH_DATA_DASHBOARD / "price_trends.parquet", index=False)

    # ── cumulative returns ──
    print("[generate_dashboard_data] 6) cumulative_returns ...")
    px = feat.sort_values(["asset", "date"])
    px["cum"] = px.groupby("asset")["daily_return"].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    px[["date", "asset", "cum"]].to_csv(
        PATH_DATA_DASHBOARD / "cumulative_returns.csv", index=False, encoding="utf-8-sig"
    )

    # ── rolling correlation (backward compat) ──
    print("[generate_dashboard_data] 7) rolling_correlation ...")
    cols = ["date"]
    for c in feat.columns:
        if c.startswith("rolling_corr"):
            cols.append(c)
    if len(cols) > 1:
        feat[cols].drop_duplicates("date").to_csv(
            PATH_DATA_DASHBOARD / "rolling_correlation.csv", index=False, encoding="utf-8-sig"
        )

    # ── risk summary (backward compat) ──
    print("[generate_dashboard_data] 8) risk_summary ...")
    risk_cols = []
    if "rolling_volatility_21d" in feat.columns:
        risk_cols.append("rolling_volatility_21d")
    if "drawdown" in feat.columns:
        risk_cols.append("drawdown")
    if risk_cols:
        risk = feat.groupby("asset")[risk_cols].mean().reset_index()
        risk.to_csv(PATH_DATA_DASHBOARD / "risk_summary.csv", index=False, encoding="utf-8-sig")

    # ── safe_haven_ranking (composite score) ──
    # Keep this separate from return_ranking.csv:
    # Return Ranking = mean crisis return only.
    # Safe Haven Ranking = weighted composite score from spark_transform.py.
    sh = PATH_DATA_DASHBOARD / "safe_haven_score.csv"
    if sh.exists():
        sh_df = pd.read_csv(sh)
        if "safe_haven_score" in sh_df.columns:
            sh_df = sh_df.sort_values("safe_haven_score", ascending=False).reset_index(drop=True)
            sh_df["rank"] = range(1, len(sh_df) + 1)
            sh_df.to_csv(PATH_DATA_DASHBOARD / "safe_haven_ranking.csv", index=False, encoding="utf-8-sig")
    else:
        print("  [WARN] ไม่พบ safe_haven_score.csv — ไม่สร้าง safe_haven_ranking.csv")

    # ── Final insight summary ──
    lines = [
        "# Final Insights (สรุปสำหรับรายงาน)",
        "",
        "## 1) Multi-source data",
        "- ใช้ Yahoo (หลายสินทรัพย์) + FRED (macro/stress) เพื่อเพิ่ม variety และตอบคำถาม **WHY**",
        "",
        "## 2) PySpark Transformation Layer",
        "- spark_transform.py สร้างสถิติสรุป, Safe Haven Score, Market Breadth, Return Ranking",
        "- Dashboard อ่านเฉพาะ processed data จาก data/dashboard/ ไม่อ่าน raw data",
        "",
        "## 3) Airflow",
        "- Airflow orchestrate pipeline แบบ repeatable และตรวจสอบสถานะแต่ละขั้นได้",
        "",
        "## 4) Parquet",
        "- Parquet อ่านเร็ว บีบอัดดี เหมาะกับข้อมูลขนาดใหญ่และ Spark",
        "",
        "## 5) Safe Haven Score",
        "- ใช้ composite score 6 มิติ (return, outperform, drawdown, vol, corr, hit rate)",
        "- แยกชัดจาก Return Ranking — mean return ≠ safe haven",
        "",
        "## 6) Key insight",
        "- ทองเป็น **conditional safe haven** — ดีในบางวิกฤต ล้มเหลวในบางช่วง",
        "",
    ]
    (PATH_REPORTS / "final_insight_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"[generate_dashboard_data] เสร็จสมบูรณ์ — ไฟล์ใน {PATH_DATA_DASHBOARD}")


if __name__ == "__main__":
    run_generate_dashboard_data()
