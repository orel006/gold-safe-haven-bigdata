"""
Data Ingestion — FRED
ดึง time series จาก FRED CSV endpoint แล้วเซฟ CSV + log
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from src.config import (
    FRED_SERIES_LIST,
    PATH_DATA_DASHBOARD,
    PATH_DATA_RAW_FRED,
    ensure_all_directories,
    resolve_date_range,
)
from src.utils import sanitize_filename


def ingest_all_fred() -> pd.DataFrame:
    ensure_all_directories()
    start_date, end_date = resolve_date_range()
    logs: list[dict] = []

    print(f"[ingest_fred] ช่วงวันที่: {start_date} -> {end_date}")

    for series_id in FRED_SERIES_LIST:
        safe = sanitize_filename(series_id)
        out_path = PATH_DATA_RAW_FRED / f"{safe}.csv"
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            raw = pd.read_csv(url)
            if raw.empty:
                raise ValueError("ไม่มีข้อมูลจาก FRED")

            df = raw.rename(columns={raw.columns[0]: "Date", raw.columns[1]: "Value"})
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df["Value"] = pd.to_numeric(df["Value"].replace(".", pd.NA), errors="coerce")
            df = df[(df["Date"] >= pd.Timestamp(start_date)) & (df["Date"] <= pd.Timestamp(end_date))]
            df["variable"] = series_id
            df["source"] = "FRED"
            df = df[["Date", "Value", "variable", "source"]]

            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            logs.append(
                {
                    "variable": series_id,
                    "status": "SUCCESS",
                    "rows": len(df),
                    "path": str(out_path),
                }
            )
            print(f"  OK  {series_id} -> {len(df)} rows")
        except Exception as e:
            cached_rows = 0
            if out_path.exists():
                try:
                    cached_rows = len(pd.read_csv(out_path))
                except Exception:
                    cached_rows = 0
            if cached_rows > 0:
                logs.append(
                    {
                        "variable": series_id,
                        "status": f"USING_CACHED: {e}",
                        "rows": cached_rows,
                        "path": str(out_path),
                    }
                )
                print(f"  CACHE {series_id}: ใช้ไฟล์เดิม {cached_rows} rows ({e})")
                continue

            logs.append(
                {
                    "variable": series_id,
                    "status": f"FAILED: {e}",
                    "rows": 0,
                    "path": "",
                }
            )
            print(f"  FAIL {series_id}: {e}")

    log_df = pd.DataFrame(logs)
    PATH_DATA_DASHBOARD.mkdir(parents=True, exist_ok=True)
    log_csv = PATH_DATA_DASHBOARD / "download_fred_log.csv"
    log_df.to_csv(log_csv, index=False, encoding="utf-8-sig")
    print(f"[ingest_fred] บันทึก log: {log_csv}")
    return log_df


if __name__ == "__main__":
    ingest_all_fred()
