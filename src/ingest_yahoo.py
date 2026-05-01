"""
Data Ingestion — Yahoo Finance
ดึงราคา daily ตาม ticker ใน config แล้วเซฟ CSV รายตัว + log
"""
import sys
import logging
from pathlib import Path

# ให้รันได้ทั้ง `python -m src.ingest_yahoo` และ `python src/ingest_yahoo.py` จากรากโปรเจกต์
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from src.config import (
    PATH_DATA_DASHBOARD,
    PATH_DATA_RAW_YAHOO,
    YAHOO_INTERVAL,
    ensure_all_directories,
    flatten_yahoo_tickers,
    resolve_date_range,
)
from src.utils import normalize_yahoo_columns, sanitize_filename


def ingest_all_yahoo() -> pd.DataFrame:
    """
    วนลูปดึงข้อมูล Yahoo ทุก ticker
    คืน DataFrame log (status ต่อ ticker)
    """
    ensure_all_directories()
    cache_dir = _ROOT / "data" / "cache" / "yfinance"
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        yf.set_tz_cache_location(str(cache_dir))
        yf.cache.set_cache_location(str(cache_dir))
    except Exception as e:
        print(f"[ingest_yahoo] WARN: ตั้งค่า yfinance cache ไม่สำเร็จ: {e}")

    start_date, end_date = resolve_date_range()
    logs: list[dict] = []

    print(f"[ingest_yahoo] ช่วงวันที่: {start_date} -> {end_date}, interval={YAHOO_INTERVAL}")

    for group, ticker in flatten_yahoo_tickers():
        safe = sanitize_filename(ticker)
        out_path = PATH_DATA_RAW_YAHOO / f"{safe}.csv"
        try:
            raw = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=YAHOO_INTERVAL,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            df = normalize_yahoo_columns(raw)
            if df.empty:
                raise ValueError("ไม่มีข้อมูลจาก Yahoo")

            # metadata ตามสเปก
            df["asset"] = ticker
            df["group"] = group
            df["source"] = "Yahoo Finance"

            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            logs.append(
                {
                    "asset": ticker,
                    "group": group,
                    "status": "SUCCESS",
                    "rows": len(df),
                    "path": str(out_path),
                }
            )
            print(f"  OK  {ticker} ({group}) -> {len(df)} rows")
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
                        "asset": ticker,
                        "group": group,
                        "status": f"USING_CACHED: {e}",
                        "rows": cached_rows,
                        "path": str(out_path),
                    }
                )
                print(f"  CACHE {ticker}: ใช้ไฟล์เดิม {cached_rows} rows ({e})")
                continue

            status = f"FAILED: {e}"
            if ticker == "XAUUSD=X":
                status = f"OPTIONAL_FAILED: {e}"
            logs.append(
                {
                    "asset": ticker,
                    "group": group,
                    "status": status,
                    "rows": 0,
                    "path": "",
                }
            )
            label = "OPTIONAL" if ticker == "XAUUSD=X" else "FAIL"
            print(f"  {label} {ticker}: {e}")

    log_df = pd.DataFrame(logs)
    PATH_DATA_DASHBOARD.mkdir(parents=True, exist_ok=True)
    log_csv = PATH_DATA_DASHBOARD / "download_yahoo_log.csv"
    log_df.to_csv(log_csv, index=False, encoding="utf-8-sig")
    print(f"[ingest_yahoo] บันทึก log: {log_csv}")
    return log_df


if __name__ == "__main__":
    ingest_all_yahoo()
