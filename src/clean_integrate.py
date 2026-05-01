"""
Data Cleaning + Integration
1) รวม Yahoo raw -> yahoo_cleaned.csv
2) รวม FRED raw -> fred_cleaned.csv
3) macro_wide (pivot ตัวแปรเป็น column)
4) master_asset_panel + merge macro (forward-fill สำหรับข้อมูลไม่ใช่รายวัน)
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from src.config import (
    PATH_DATA_CLEANED,
    PATH_DATA_INTEGRATED,
    PATH_DATA_RAW_FRED,
    PATH_DATA_RAW_YAHOO,
    ensure_all_directories,
)


def _read_all_yahoo_raw() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for p in sorted(PATH_DATA_RAW_YAHOO.glob("*.csv")):
        try:
            df = pd.read_csv(p)
            frames.append(df)
        except Exception as e:
            print(f"[clean] ข้ามไฟล์ Yahoo {p.name}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _read_all_fred_raw() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for p in sorted(PATH_DATA_RAW_FRED.glob("*.csv")):
        try:
            df = pd.read_csv(p)
            frames.append(df)
        except Exception as e:
            print(f"[clean] ข้ามไฟล์ FRED {p.name}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def clean_yahoo(df: pd.DataFrame) -> pd.DataFrame:
    """
    ทำความสะอาด Yahoo: rename เป็น snake_case, เรียงลำดับ, ลบซ้ำ, เติมราคาขาดในแต่ละ asset
    """
    if df.empty:
        return df

    rename_map = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
        "asset": "asset",
        "group": "group",
        "source": "source",
    }
    out = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date", "asset"])
    out = out.sort_values(["asset", "date"])
    out = out.drop_duplicates(subset=["asset", "date"], keep="last")

    price_cols = ["open", "high", "low", "close", "adj_close"]
    for c in price_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if "volume" in out.columns:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0)

    # forward fill ราคาภายในแต่ละ asset (เหมาะกับช่องว่างสั้น ๆ จากตลาดปิด)
    out[price_cols] = out.groupby("asset")[price_cols].ffill()
    out["volume"] = out.groupby("asset")["volume"].ffill().fillna(0)
    return out.reset_index(drop=True)


def clean_fred(df: pd.DataFrame) -> pd.DataFrame:
    """ทำความสะอาด FRED"""
    if df.empty:
        return df
    out = df.copy()
    out = out.rename(columns={"Date": "date", "Value": "value", "variable": "variable", "source": "source"})
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["date", "variable"])
    out = out.sort_values(["variable", "date"])
    out = out.drop_duplicates(subset=["variable", "date"], keep="last")
    out["value"] = out.groupby("variable")["value"].ffill()
    return out.reset_index(drop=True)


def build_macro_wide(fred_clean: pd.DataFrame) -> pd.DataFrame:
    """
    แปลง FRED long -> wide (แต่ละ variable เป็นคอลัมน์)
    """
    if fred_clean.empty:
        return pd.DataFrame()
    wide = fred_clean.pivot_table(index="date", columns="variable", values="value", aggfunc="last")
    wide = wide.sort_index().reset_index()
    return wide


def merge_macro_to_panel(panel: pd.DataFrame, macro_wide: pd.DataFrame) -> pd.DataFrame:
    """
    merge macro เข้ากับ asset panel ตามวันที่ แล้ว forward-fill
    เหตุผล: CPI / FEDFUNDS บางตัวเป็นรายเดือน — ใช้ค่าล่าสุดที่ทราบจนถึงวันนั้น (as-of / ffill)
    """
    if panel.empty:
        return panel
    if macro_wide.empty:
        return panel

    merged = panel.merge(macro_wide, on="date", how="left")
    merged = merged.sort_values("date")
    macro_cols = [c for c in macro_wide.columns if c != "date"]
    merged[macro_cols] = merged[macro_cols].ffill()
    return merged.reset_index(drop=True)


def run_clean_integrate() -> None:
    ensure_all_directories()
    PATH_DATA_CLEANED.mkdir(parents=True, exist_ok=True)
    PATH_DATA_INTEGRATED.mkdir(parents=True, exist_ok=True)

    raw_y = _read_all_yahoo_raw()
    raw_f = _read_all_fred_raw()

    y_clean = clean_yahoo(raw_y)
    f_clean = clean_fred(raw_f)

    y_path = PATH_DATA_CLEANED / "yahoo_cleaned.csv"
    f_path = PATH_DATA_CLEANED / "fred_cleaned.csv"
    y_clean.to_csv(y_path, index=False, encoding="utf-8-sig")
    f_clean.to_csv(f_path, index=False, encoding="utf-8-sig")
    print(f"[clean_integrate] Yahoo cleaned -> {y_path} ({len(y_clean)} rows)")
    print(f"[clean_integrate] FRED cleaned  -> {f_path} ({len(f_clean)} rows)")

    macro_wide = build_macro_wide(f_clean)
    macro_wide.to_csv(PATH_DATA_INTEGRATED / "macro_wide.csv", index=False, encoding="utf-8-sig")
    macro_wide.to_parquet(PATH_DATA_INTEGRATED / "macro_wide.parquet", index=False, engine="pyarrow")
    print(f"[clean_integrate] macro_wide -> {len(macro_wide)} dates")

    # master asset panel = เฉพาะ Yahoo (ราคา)
    master = y_clean.copy()
    master = merge_macro_to_panel(master, macro_wide)

    master.to_csv(PATH_DATA_INTEGRATED / "master_asset_panel.csv", index=False, encoding="utf-8-sig")
    master.to_parquet(PATH_DATA_INTEGRATED / "master_asset_panel.parquet", index=False, engine="pyarrow")
    print(f"[clean_integrate] master_asset_panel -> {len(master)} rows")


if __name__ == "__main__":
    run_clean_integrate()
