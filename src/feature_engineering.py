"""
Feature Engineering — สร้างฟีเจอร์สำหรับวิเคราะห์ Safe Haven / WHY
อ่าน master_asset_panel แล้วบันทึก feature_dataset
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from src.config import PATH_DATA_INTEGRATED, PRIMARY_GOLD_TICKER, ROLLING_WINDOWS, ensure_all_directories


def compute_asset_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    คำนวณฟีเจอร์ต่อ asset จาก long panel
    """
    out = df.copy().sort_values(["asset", "date"])
    # ราคาปรับสิทธิ์ก่อน ถ้าไม่มีใช้ close
    out["_px"] = out["adj_close"].fillna(out["close"])

    out["daily_return"] = out.groupby("asset")["_px"].pct_change()
    out["log_return"] = np.log1p(out["daily_return"].replace(-1, np.nan))
    out["daily_change"] = out["close"] - out["open"]
    out["cumulative_return"] = out.groupby("asset")["daily_return"].transform(lambda s: (1 + s.fillna(0)).cumprod() - 1)

    w21 = ROLLING_WINDOWS["short"]
    w63 = ROLLING_WINDOWS["medium"]
    out["rolling_mean_21d"] = out.groupby("asset")["_px"].transform(lambda s: s.rolling(w21).mean())
    out["rolling_volatility_21d"] = out.groupby("asset")["daily_return"].transform(lambda s: s.rolling(w21).std())
    out["rolling_volatility_63d"] = out.groupby("asset")["daily_return"].transform(lambda s: s.rolling(w63).std())

    peak = out.groupby("asset")["_px"].cummax()
    out["drawdown"] = (out["_px"] / peak) - 1.0
    out["rolling_high"] = out.groupby("asset")["_px"].transform(lambda s: s.rolling(w63).max())
    out["max_drawdown"] = out.groupby("asset")["drawdown"].transform("min")

    out["ma_20"] = out.groupby("asset")["_px"].transform(lambda s: s.rolling(20).mean())
    out["ma_50"] = out.groupby("asset")["_px"].transform(lambda s: s.rolling(50).mean())
    out["ma_200"] = out.groupby("asset")["_px"].transform(lambda s: s.rolling(200).mean())
    out["return_5d"] = out.groupby("asset")["_px"].pct_change(5)
    out["return_21d"] = out.groupby("asset")["_px"].pct_change(w21)
    out["return_63d"] = out.groupby("asset")["_px"].pct_change(w63)

    # ลบคอลัมน์ชั่วคราว
    out = out.drop(columns=["_px"], errors="ignore")
    return out


def add_relationship_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rolling correlation ระหว่างทองกับสินทรัพย์อื่น (ใช้ pivot return รายวัน)
    """
    tmp = df[["date", "asset", "daily_return"]].dropna()
    wide = tmp.pivot_table(index="date", columns="asset", values="daily_return", aggfunc="first")
    wide = wide.sort_index()

    gold = PRIMARY_GOLD_TICKER
    c30 = ROLLING_WINDOWS["corr_short"]
    c90 = ROLLING_WINDOWS["corr_long"]

    out = df.copy()
    if gold not in wide.columns:
        out["rolling_corr_gold_spy_30d"] = np.nan
        out["rolling_corr_gold_spy_90d"] = np.nan
        out["rolling_corr_gold_tlt_90d"] = np.nan
        out["rolling_corr_gold_uup_90d"] = np.nan
        out["rolling_corr_gold_btc_90d"] = np.nan
        return out

    def add_corr(col_name: str, other: str, window: int):
        if other in wide.columns:
            return wide[gold].rolling(window).corr(wide[other])
        return pd.Series(np.nan, index=wide.index)

    corr_spy_30 = add_corr("spy30", "SPY", c30)
    corr_spy_90 = add_corr("spy90", "SPY", c90)
    corr_tlt_90 = add_corr("tlt90", "TLT", c90)
    corr_uup_90 = add_corr("uup90", "UUP", c90)
    corr_btc_90 = add_corr("btc90", "BTC-USD", c90)

    corr_df = pd.DataFrame(
        {
            "date": pd.to_datetime(wide.index),
            "rolling_corr_gold_spy_30d": corr_spy_30.values,
            "rolling_corr_gold_spy_90d": corr_spy_90.values,
            "rolling_corr_gold_tlt_90d": corr_tlt_90.values,
            "rolling_corr_gold_uup_90d": corr_uup_90.values,
            "rolling_corr_gold_btc_90d": corr_btc_90.values,
        }
    )
    return out.merge(corr_df, on="date", how="left")


def add_macro_feature_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """
    ตั้งชื่อฟีเจอร์มหภาคให้อ่านง่าย (อ้างอิงคอลัมน์จาก FRED ที่ merge แล้ว)
    """
    out = df.copy()
    rename_pairs = [
        ("VIXCLS", "vix_level"),
        ("USREC", "recession_flag"),
        ("CPIAUCSL", "cpi_level"),
        ("FEDFUNDS", "fed_rate"),
        ("EFFR", "effr"),
        ("DGS10", "treasury_10y"),
        ("DFII10", "real_yield"),
        ("T10YIE", "breakeven_inflation"),
        ("DTWEXBGS", "dollar_index"),
    ]
    for src, dst in rename_pairs:
        if src in out.columns:
            out[dst] = out[src]

    # inflation_yoy จาก CPI รายเดือน — คำนวณตาม timeline ของวันที่ (ไม่แยก asset)
    if "cpi_level" in out.columns:
        u = out[["date", "cpi_level"]].drop_duplicates("date").sort_values("date")
        u["inflation_yoy"] = u["cpi_level"].pct_change(252)
        out = out.merge(u[["date", "inflation_yoy"]], on="date", how="left")
    return out


def run_feature_engineering() -> None:
    ensure_all_directories()
    path_in = PATH_DATA_INTEGRATED / "master_asset_panel.parquet"
    if not path_in.exists():
        path_in = PATH_DATA_INTEGRATED / "master_asset_panel.csv"
    if not path_in.exists():
        raise FileNotFoundError("ไม่พบ master_asset_panel — รัน clean_integrate ก่อน")

    df = pd.read_parquet(path_in) if path_in.suffix == ".parquet" else pd.read_csv(path_in)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    feat = compute_asset_features(df)
    feat = add_relationship_features(feat)
    feat = add_macro_feature_aliases(feat)

    out_csv = PATH_DATA_INTEGRATED / "feature_dataset.csv"
    out_pq = PATH_DATA_INTEGRATED / "feature_dataset.parquet"
    feat.to_csv(out_csv, index=False, encoding="utf-8-sig")
    feat.to_parquet(out_pq, index=False, engine="pyarrow")
    print(f"[feature_engineering] บันทึก {out_pq} ({len(feat)} rows)")


if __name__ == "__main__":
    run_feature_engineering()
