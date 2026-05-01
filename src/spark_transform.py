"""
PySpark Transformation / Statistics Layer
==========================================
สร้าง dashboard-ready datasets จากข้อมูลที่ผ่าน crisis_labeling แล้ว
ใช้ PySpark เป็น engine หลักในการ transform + aggregate

Output ทั้งหมดเขียนลง data/spark_output/ แล้ว generate_dashboard_data จะ copy ไป data/dashboard/

หมายเหตุ: ถ้า PySpark ไม่พร้อม จะ fallback ใช้ Pandas แทน (เพื่อให้ pipeline ไม่พัง)
"""
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from src.config import (
    NAMED_CRISIS_EVENTS,
    PATH_DATA_CLEANED,
    PATH_DATA_INTEGRATED,
    PATH_DATA_SPARK_OUTPUT,
    PATH_REPORTS,
    PRIMARY_GOLD_TICKER,
    ROLLING_CORR_WINDOWS,
    SAFE_HAVEN_WEIGHTS,
    ensure_all_directories,
)


# ============================================================
# HELPER: ลอง PySpark ก่อน ถ้าไม่ได้ fallback Pandas
# ============================================================
USE_SPARK = False
SPARK_RUNTIME_STATUS = "pyspark_not_installed"
try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    USE_SPARK = True
    SPARK_RUNTIME_STATUS = "import_ok"
except ImportError:
    pass


def _check_spark_runtime() -> bool:
    """ตรวจว่า PySpark เปิด session ได้จริงหรือไม่ ก่อน fallback เป็น Pandas."""
    global SPARK_RUNTIME_STATUS
    if not USE_SPARK:
        return False
    try:
        spark = (
            SparkSession.builder.appName("GoldSafeHavenTransformCheck")
            .master("local[1]")
            .config("spark.sql.shuffle.partitions", "4")
            .getOrCreate()
        )
        spark.range(1).count()
        spark.stop()
        SPARK_RUNTIME_STATUS = "runtime_ok"
        return True
    except Exception as exc:
        SPARK_RUNTIME_STATUS = f"runtime_failed: {exc}"
        return False


def _load_labeled() -> pd.DataFrame:
    """โหลด labeled_dataset (output จาก crisis_labeling)"""
    pq = PATH_DATA_INTEGRATED / "labeled_dataset.parquet"
    csv = PATH_DATA_INTEGRATED / "labeled_dataset.csv"
    if pq.exists():
        df = pd.read_parquet(pq)
    elif csv.exists():
        df = pd.read_csv(csv)
    else:
        raise FileNotFoundError("ไม่พบ labeled_dataset — รัน crisis_labeling ก่อน")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _load_feature() -> pd.DataFrame:
    """โหลด feature_dataset"""
    pq = PATH_DATA_INTEGRATED / "feature_dataset.parquet"
    csv = PATH_DATA_INTEGRATED / "feature_dataset.csv"
    if pq.exists():
        df = pd.read_parquet(pq)
    elif csv.exists():
        df = pd.read_csv(csv)
    else:
        raise FileNotFoundError("ไม่พบ feature_dataset — รัน feature_engineering ก่อน")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _save(df: pd.DataFrame, name: str) -> None:
    """บันทึก CSV ลง spark_output"""
    out = PATH_DATA_SPARK_OUTPUT / name
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"  [spark_transform] -> {out} ({len(df)} rows)")


# ============================================================
# 1) สถิติสรุป per asset (ทั้ง full period)
# ============================================================
def compute_stats_per_asset(lab: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ mean/median/std/min/max/drawdown/volatility/hit_rate ต่อ asset"""
    print("[spark_transform] 1) stats_per_asset ...")
    records = []
    for asset, g in lab.groupby("asset"):
        ret = g["daily_return"].dropna()
        records.append({
            "asset": asset,
            "count": len(g),
            "mean_return": ret.mean() if len(ret) else np.nan,
            "median_return": ret.median() if len(ret) else np.nan,
            "std_return": ret.std() if len(ret) else np.nan,
            "min_return": ret.min() if len(ret) else np.nan,
            "max_return": ret.max() if len(ret) else np.nan,
            "mean_drawdown": g["drawdown"].mean() if "drawdown" in g.columns else np.nan,
            "max_drawdown": g["drawdown"].min() if "drawdown" in g.columns else np.nan,
            "mean_volatility_21d": g["rolling_volatility_21d"].mean() if "rolling_volatility_21d" in g.columns else np.nan,
            "hit_rate": (ret > 0).mean() if len(ret) else np.nan,
        })
    out = pd.DataFrame(records).sort_values("mean_return", ascending=False)
    _save(out, "stats_per_asset.csv")
    return out


# ============================================================
# 2) สถิติ per named crisis event
# ============================================================
def compute_stats_per_crisis(lab: pd.DataFrame) -> pd.DataFrame:
    """คำนวณสถิติแยกตาม named crisis event"""
    print("[spark_transform] 2) stats_per_crisis ...")
    records = []
    for event in NAMED_CRISIS_EVENTS:
        s = pd.Timestamp(event["start_date"])
        e = pd.Timestamp(event["end_date"])
        mask = (lab["date"] >= s) & (lab["date"] <= e)
        sub = lab[mask]
        for asset, g in sub.groupby("asset"):
            ret = g["daily_return"].dropna()
            if len(ret) == 0:
                continue
            # คำนวณ total return ของช่วง crisis
            px_col = "adj_close" if "adj_close" in g.columns else "close"
            px = pd.to_numeric(g[px_col], errors="coerce").dropna()
            total_ret = (px.iloc[-1] / px.iloc[0] - 1) if len(px) >= 2 else np.nan
            records.append({
                "crisis_name": event["name"],
                "start_date": event["start_date"],
                "end_date": event["end_date"],
                "asset": asset,
                "trading_days": len(ret),
                "mean_daily_return": ret.mean(),
                "total_return": total_ret,
                "std_return": ret.std(),
                "max_drawdown": g["drawdown"].min() if "drawdown" in g.columns else np.nan,
                "hit_rate": (ret > 0).mean(),
            })
    out = pd.DataFrame(records)
    _save(out, "stats_per_crisis.csv")
    return out


# ============================================================
# 3) สถิติ crisis vs normal
# ============================================================
def compute_crisis_vs_normal(lab: pd.DataFrame) -> pd.DataFrame:
    """เปรียบเทียบ regime: crisis vs normal per asset"""
    print("[spark_transform] 3) stats_crisis_vs_normal ...")
    lab["regime"] = np.where(lab["final_crisis_label"] == 1, "crisis", "normal")
    records = []
    for (asset, regime), g in lab.groupby(["asset", "regime"]):
        ret = g["daily_return"].dropna()
        records.append({
            "asset": asset,
            "regime": regime,
            "count": len(g),
            "mean_return": ret.mean() if len(ret) else np.nan,
            "std_return": ret.std() if len(ret) else np.nan,
            "mean_volatility_21d": g["rolling_volatility_21d"].mean() if "rolling_volatility_21d" in g.columns else np.nan,
            "max_drawdown": g["drawdown"].min() if "drawdown" in g.columns else np.nan,
            "hit_rate": (ret > 0).mean() if len(ret) else np.nan,
        })
    out = pd.DataFrame(records)
    _save(out, "stats_crisis_vs_normal.csv")
    return out


# ============================================================
# 4) Return Ranking (mean daily return ช่วง crisis)
# ============================================================
def compute_return_ranking(lab: pd.DataFrame) -> pd.DataFrame:
    """จัดอันดับจาก mean daily return ในช่วง crisis — ชื่อชัดว่าเป็น Return Ranking"""
    print("[spark_transform] 4) return_ranking ...")
    c = lab[lab["final_crisis_label"] == 1]
    rank = c.groupby("asset")["daily_return"].agg(["mean", "std", "count"]).reset_index()
    rank = rank.sort_values("mean", ascending=False).reset_index(drop=True)
    rank["rank"] = range(1, len(rank) + 1)
    _save(rank, "return_ranking.csv")
    return rank


# ============================================================
# 5) Safe Haven Score (6 มิติ)
# ============================================================
def compute_safe_haven_score(lab: pd.DataFrame) -> pd.DataFrame:
    """
    Safe Haven Score = weighted sum ของ z-scores 6 มิติ:
    1. mean_crisis_return
    2. outperform_spy_rate (% วันที่ return > SPY ช่วง crisis)
    3. low_max_drawdown (ยิ่ง drawdown ตื้นยิ่งดี)
    4. low_crisis_volatility (ยิ่ง vol ต่ำยิ่งดี)
    5. neg_corr_with_spy (ยิ่ง corr ลบยิ่งดี)
    6. hit_rate (% วันที่ return > 0 ช่วง crisis)
    """
    print("[spark_transform] 5) safe_haven_score ...")
    c = lab[lab["final_crisis_label"] == 1].copy()
    if c.empty:
        print("  [WARN] ไม่มีข้อมูล crisis — ข้ามการคำนวณ Safe Haven Score")
        return pd.DataFrame()

    # ดึง SPY return รายวัน
    spy_ret = c[c["asset"] == "SPY"][["date", "daily_return"]].drop_duplicates("date")
    spy_ret = spy_ret.rename(columns={"daily_return": "spy_ret"})

    records = []
    for asset, g in c.groupby("asset"):
        ret = g["daily_return"].dropna()
        if len(ret) < 5:
            continue

        # merge กับ SPY เพื่อหา outperform rate
        merged = g[["date", "daily_return"]].merge(spy_ret, on="date", how="inner")

        mean_cr = ret.mean()
        outperform = (merged["daily_return"] > merged["spy_ret"]).mean() if len(merged) else 0
        max_dd = g["drawdown"].min() if "drawdown" in g.columns else 0
        vol = ret.std()
        hit = (ret > 0).mean()

        # correlation กับ SPY ในช่วง crisis
        corr_col = "rolling_corr_gold_spy_90d"
        if corr_col in g.columns and asset == PRIMARY_GOLD_TICKER:
            corr_val = g[corr_col].dropna().mean()
        elif len(merged) >= 10:
            corr_val = merged["daily_return"].corr(merged["spy_ret"])
        else:
            corr_val = 0

        records.append({
            "asset": asset,
            "mean_crisis_return": mean_cr,
            "outperform_spy_rate": outperform,
            "max_drawdown_crisis": max_dd,
            "crisis_volatility": vol,
            "corr_with_spy": corr_val if not np.isnan(corr_val) else 0,
            "hit_rate": hit,
            "crisis_days": len(ret),
        })

    raw = pd.DataFrame(records)
    if raw.empty:
        return raw

    # Z-score normalization
    def zscore(s: pd.Series) -> pd.Series:
        std = s.std()
        if std == 0 or np.isnan(std):
            return pd.Series(0, index=s.index)
        return (s - s.mean()) / std

    w = SAFE_HAVEN_WEIGHTS
    raw["z_return"] = zscore(raw["mean_crisis_return"])
    raw["z_outperform"] = zscore(raw["outperform_spy_rate"])
    raw["z_drawdown"] = zscore(-raw["max_drawdown_crisis"].abs())  # ตื้น = ดี
    raw["z_vol"] = zscore(-raw["crisis_volatility"])                # ต่ำ = ดี
    raw["z_corr"] = zscore(-raw["corr_with_spy"])                   # ลบ = ดี
    raw["z_hit"] = zscore(raw["hit_rate"])

    raw["safe_haven_score"] = (
        w["mean_crisis_return"] * raw["z_return"]
        + w["outperform_spy_rate"] * raw["z_outperform"]
        + w["low_max_drawdown"] * raw["z_drawdown"]
        + w["low_crisis_volatility"] * raw["z_vol"]
        + w["neg_corr_with_spy"] * raw["z_corr"]
        + w["hit_rate"] * raw["z_hit"]
    )

    raw = raw.sort_values("safe_haven_score", ascending=False).reset_index(drop=True)
    raw["rank"] = range(1, len(raw) + 1)
    _save(raw, "safe_haven_score.csv")
    _save(raw, "safe_haven_ranking.csv")
    return raw


# ============================================================
# 6) Market Breadth
# ============================================================
def compute_market_breadth(lab: pd.DataFrame) -> pd.DataFrame:
    """% positive, % outperform SPY, advance/decline ฯลฯ"""
    print("[spark_transform] 6) market_breadth ...")
    c = lab[lab["final_crisis_label"] == 1].copy()
    if c.empty:
        return pd.DataFrame()

    spy_mean = c[c["asset"] == "SPY"]["daily_return"].mean()
    spy_dd = c[c["asset"] == "SPY"]["drawdown"].min() if "drawdown" in c.columns else -1

    asset_stats = c.groupby("asset").agg(
        mean_return=("daily_return", "mean"),
        max_drawdown=("drawdown", "min") if "drawdown" in c.columns else ("daily_return", "min"),
        group=("group", "first"),
    ).reset_index()

    n = len(asset_stats)
    n_pos = (asset_stats["mean_return"] > 0).sum()
    n_outperform = (asset_stats["mean_return"] > spy_mean).sum()
    n_low_dd = (asset_stats["max_drawdown"] > spy_dd).sum() if "drawdown" in c.columns else 0

    summary = pd.DataFrame([{
        "total_assets": n,
        "advance_count": int(n_pos),
        "decline_count": int(n - n_pos),
        "pct_positive_crisis": round(n_pos / n * 100, 1) if n else 0,
        "pct_outperform_spy": round(n_outperform / n * 100, 1) if n else 0,
        "pct_low_drawdown": round(n_low_dd / n * 100, 1) if n else 0,
        "spy_mean_crisis_return": spy_mean,
        "spy_max_drawdown": spy_dd,
    }])
    _save(summary, "market_breadth.csv")

    # breadth by group
    group_records = []
    for grp, g in asset_stats.groupby("group"):
        ng = len(g)
        group_records.append({
            "group": grp,
            "total": ng,
            "advance": int((g["mean_return"] > 0).sum()),
            "decline": int((g["mean_return"] <= 0).sum()),
            "pct_positive": round((g["mean_return"] > 0).mean() * 100, 1),
        })
    group_df = pd.DataFrame(group_records)
    _save(group_df, "market_breadth_by_group.csv")

    return summary


# ============================================================
# 7) Rolling Correlation (multi-window)
# ============================================================
def compute_rolling_corr_multi(feat: pd.DataFrame) -> pd.DataFrame:
    """Rolling correlation ทองกับ SPY/TLT/UUP/BTC หลาย window"""
    print("[spark_transform] 7) rolling_corr_multi ...")
    tmp = feat[["date", "asset", "daily_return"]].dropna()
    wide = tmp.pivot_table(index="date", columns="asset", values="daily_return", aggfunc="first")
    wide = wide.sort_index()

    gold = PRIMARY_GOLD_TICKER
    if gold not in wide.columns:
        print("  [WARN] ไม่พบ gold ticker ใน data — ข้ามการคำนวณ rolling corr")
        return pd.DataFrame()

    pairs = {"SPY": "spy", "TLT": "tlt", "UUP": "uup", "BTC-USD": "btc"}
    result = pd.DataFrame({"date": wide.index})

    for window in ROLLING_CORR_WINDOWS:
        for ticker, label in pairs.items():
            col_name = f"corr_gold_{label}_{window}d"
            if ticker in wide.columns:
                result[col_name] = wide[gold].rolling(window).corr(wide[ticker]).values
            else:
                result[col_name] = np.nan

    _save(result, "rolling_corr_multi.csv")
    return result


# ============================================================
# 8) Risk Detail (crisis vs normal volatility)
# ============================================================
def compute_risk_detail(lab: pd.DataFrame) -> pd.DataFrame:
    """Rolling vol, max drawdown, crisis vs normal risk"""
    print("[spark_transform] 8) risk_detail ...")
    lab["regime"] = np.where(lab["final_crisis_label"] == 1, "crisis", "normal")
    records = []
    for (asset, regime), g in lab.groupby(["asset", "regime"]):
        ret = g["daily_return"].dropna()
        records.append({
            "asset": asset,
            "regime": regime,
            "mean_volatility_21d": g["rolling_volatility_21d"].mean() if "rolling_volatility_21d" in g.columns else np.nan,
            "mean_volatility_63d": g["rolling_volatility_63d"].mean() if "rolling_volatility_63d" in g.columns else np.nan,
            "max_drawdown": g["drawdown"].min() if "drawdown" in g.columns else np.nan,
            "mean_return": ret.mean() if len(ret) else np.nan,
            "annualized_vol": ret.std() * np.sqrt(252) if len(ret) else np.nan,
        })
    out = pd.DataFrame(records)
    _save(out, "risk_detail.csv")
    return out


# ============================================================
# 9) Bottom Line (สรุปภาษาคน)
# ============================================================
def compute_bottom_line(lab: pd.DataFrame, sh_score: pd.DataFrame) -> pd.DataFrame:
    """สร้าง insight records สำหรับ Bottom Line page"""
    print("[spark_transform] 9) bottom_line ...")
    insights = []

    # Insight 1: Gold ในช่วง crisis โดยรวม
    c = lab[(lab["final_crisis_label"] == 1) & (lab["asset"] == PRIMARY_GOLD_TICKER)]
    if not c.empty:
        gold_cr = c["daily_return"].mean()
        spy_cr_data = lab[(lab["final_crisis_label"] == 1) & (lab["asset"] == "SPY")]
        spy_cr = spy_cr_data["daily_return"].mean() if not spy_cr_data.empty else 0
        status = "ดี" if gold_cr > 0 and gold_cr > spy_cr else "ปานกลาง" if gold_cr > spy_cr else "ล้มเหลว"
        insights.append({
            "category": "gold_overall",
            "icon": "🥇",
            "title": "ทองคำในช่วงวิกฤตโดยรวม",
            "body": f"Mean daily return = {gold_cr*100:.4f}% (SPY = {spy_cr*100:.4f}%) — สถานะ: {status}",
            "status": status,
        })

    # Insight 2-N: per crisis event
    for event in NAMED_CRISIS_EVENTS:
        s = pd.Timestamp(event["start_date"])
        e = pd.Timestamp(event["end_date"])
        mask = (lab["date"] >= s) & (lab["date"] <= e)
        gold_ev = lab[mask & (lab["asset"] == PRIMARY_GOLD_TICKER)]
        spy_ev = lab[mask & (lab["asset"] == "SPY")]
        if gold_ev.empty:
            continue
        gr = gold_ev["daily_return"].mean()
        sr = spy_ev["daily_return"].mean() if not spy_ev.empty else 0
        if gr > 0 and sr < 0:
            status = "safe_haven"
            body = f"ทองให้ผลบวก +{gr*100:.4f}% ขณะ SPY ขาดทุน {sr*100:.4f}% → Safe Haven ชัดเจน"
        elif gr > sr:
            status = "partial"
            body = f"ทอง ({gr*100:.4f}%) เสียหายน้อยกว่า SPY ({sr*100:.4f}%) → มีคุณสมบัติ partial safe haven"
        else:
            status = "failed"
            body = f"ทอง ({gr*100:.4f}%) ไม่ได้ช่วยปกป้องเมื่อเทียบ SPY ({sr*100:.4f}%) → ล้มเหลว"
        insights.append({
            "category": "crisis_event",
            "icon": "📅",
            "title": event["name"],
            "body": body,
            "status": status,
        })

    # Insight: Safe Haven Score rank
    if not sh_score.empty:
        gold_sh = sh_score[sh_score["asset"] == PRIMARY_GOLD_TICKER]
        if not gold_sh.empty:
            rank = int(gold_sh.iloc[0]["rank"])
            score = gold_sh.iloc[0]["safe_haven_score"]
            insights.append({
                "category": "safe_haven_rank",
                "icon": "🛡️",
                "title": "Safe Haven Score (Composite 6 มิติ)",
                "body": f"ทองอยู่อันดับ #{rank} จาก {len(sh_score)} สินทรัพย์ (score = {score:.3f})",
                "status": "ดี" if rank <= 5 else "ปานกลาง",
            })

    # Insight: Conditional conclusion
    insights.append({
        "category": "conclusion",
        "icon": "💎",
        "title": "สรุป: ทองคำเป็น Conditional Safe Haven",
        "body": "ทองคำเป็น safe haven ในบางช่วงวิกฤต (เช่น GFC, COVID) แต่ล้มเหลวในบางช่วง (เช่น 2022 rate hike) — ประสิทธิภาพขึ้นกับ VIX, USD, real yield",
        "status": "conditional",
    })

    out = pd.DataFrame(insights)
    _save(out, "bottom_line.csv")
    return out


# ============================================================
# 10) Transformation Metadata
# ============================================================
def compute_transformation_meta(lab: pd.DataFrame) -> pd.DataFrame:
    """บันทึก metadata ของ pipeline: row counts, file sizes, etc."""
    print("[spark_transform] 10) transformation_meta ...")

    # นับไฟล์ raw
    from src.config import PATH_DATA_RAW_YAHOO, PATH_DATA_RAW_FRED
    n_yahoo = len(list(PATH_DATA_RAW_YAHOO.glob("*.csv")))
    n_fred = len(list(PATH_DATA_RAW_FRED.glob("*.csv")))

    # นับ rows
    n_labeled = len(lab)
    n_crisis = int((lab.drop_duplicates("date")["final_crisis_label"] == 1).sum())
    n_normal = int((lab.drop_duplicates("date")["final_crisis_label"] == 0).sum())
    n_assets = lab["asset"].nunique()

    # ขนาดไฟล์
    def _dir_mb(p: Path) -> float:
        total = 0
        if not p.exists():
            return 0
        for f in p.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return round(total / 1024 / 1024, 2)

    master_csv = PATH_DATA_INTEGRATED / "master_asset_panel.csv"
    master_pq = PATH_DATA_INTEGRATED / "master_asset_panel.parquet"
    csv_mb = round(master_csv.stat().st_size / 1024 / 1024, 2) if master_csv.exists() else 0
    pq_mb = round(master_pq.stat().st_size / 1024 / 1024, 2) if master_pq.exists() else 0

    # missing values
    n_missing_before = int(lab.isna().sum().sum())

    # benchmark
    bench_path = PATH_REPORTS / "storage_benchmark.csv"
    csv_read_sec = 0
    pq_read_sec = 0
    spark_process_status = "not_found"
    if bench_path.exists():
        bench = pd.read_csv(bench_path)
        for _, r in bench.iterrows():
            if r["metric"] == "pandas_read_csv_sec":
                csv_read_sec = r["value"]
            elif r["metric"] == "pandas_read_parquet_sec":
                pq_read_sec = r["value"]
            elif r["metric"] == "spark_status":
                spark_process_status = r["value"]

    records = [
        {"metric": "yahoo_raw_files", "value": n_yahoo},
        {"metric": "fred_raw_files", "value": n_fred},
        {"metric": "total_raw_files", "value": n_yahoo + n_fred},
        {"metric": "total_assets_tracked", "value": n_assets},
        {"metric": "labeled_dataset_rows", "value": n_labeled},
        {"metric": "crisis_days", "value": n_crisis},
        {"metric": "normal_days", "value": n_normal},
        {"metric": "master_csv_size_mb", "value": csv_mb},
        {"metric": "master_parquet_size_mb", "value": pq_mb},
        {"metric": "compression_ratio", "value": round(csv_mb / pq_mb, 2) if pq_mb > 0 else 0},
        {"metric": "csv_read_seconds", "value": csv_read_sec},
        {"metric": "parquet_read_seconds", "value": pq_read_sec},
        {"metric": "missing_cells_in_labeled", "value": n_missing_before},
        {"metric": "spark_output_files", "value": len(list(PATH_DATA_SPARK_OUTPUT.glob("*.csv")))},
        {"metric": "spark_process_status", "value": spark_process_status},
        {"metric": "spark_transform_runtime_status", "value": SPARK_RUNTIME_STATUS},
    ]
    out = pd.DataFrame(records)
    _save(out, "transformation_meta.csv")
    return out


# ============================================================
# 11) Crisis Events CSV (สำหรับ deep-dive page)
# ============================================================
def save_crisis_events() -> None:
    """บันทึก named crisis events เป็น CSV"""
    print("[spark_transform] 11) crisis_events ...")
    df = pd.DataFrame(NAMED_CRISIS_EVENTS)
    _save(df, "crisis_events.csv")


# ============================================================
# MAIN RUNNER
# ============================================================
def run_spark_transform() -> None:
    """รัน Transformation/Statistics Layer ทั้งหมด"""
    ensure_all_directories()
    PATH_DATA_SPARK_OUTPUT.mkdir(parents=True, exist_ok=True)
    spark_runtime_ok = _check_spark_runtime()

    t0 = time.perf_counter()
    print("=" * 70)
    print("[spark_transform] เริ่ม PySpark Transformation Layer ...")
    print(f"  Spark import available: {USE_SPARK}")
    print(f"  Spark runtime usable: {spark_runtime_ok} ({SPARK_RUNTIME_STATUS})")
    if not spark_runtime_ok:
        print("  ใช้ Pandas fallback สำหรับ transformation เพื่อให้ pipeline รันต่อได้")
    print("=" * 70)

    # โหลดข้อมูล
    lab = _load_labeled()
    feat = _load_feature()

    # รันทุก transformation
    compute_stats_per_asset(lab)
    compute_stats_per_crisis(lab)
    compute_crisis_vs_normal(lab)
    compute_return_ranking(lab)
    sh_score = compute_safe_haven_score(lab)
    compute_market_breadth(lab)
    compute_rolling_corr_multi(feat)
    compute_risk_detail(lab)
    compute_bottom_line(lab, sh_score)
    compute_transformation_meta(lab)
    save_crisis_events()

    elapsed = time.perf_counter() - t0
    print("=" * 70)
    print(f"[spark_transform] เสร็จสมบูรณ์ใน {elapsed:.2f} วินาที")
    print(f"  Output: {PATH_DATA_SPARK_OUTPUT}")
    print("=" * 70)


if __name__ == "__main__":
    run_spark_transform()
