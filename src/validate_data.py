"""
Data Validation — ตรวจสอบไฟล์ raw Yahoo / FRED
สรุปคุณภาพข้อมูลและขนาดรวม (MB) บันทึก reports/data_quality_summary.csv
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from src.config import (
    PATH_DATA_RAW_FRED,
    PATH_DATA_RAW_YAHOO,
    PATH_REPORTS,
    ensure_all_directories,
)


def _file_size_mb(p: Path) -> float:
    return p.stat().st_size / (1024 * 1024)


def _validate_yahoo_file(path: Path) -> dict:
    """ตรวจไฟล์ Yahoo รายไฟล์"""
    try:
        df = pd.read_csv(path, nrows=None)
    except Exception as e:
        return {"file": str(path), "type": "yahoo", "ok": False, "error": str(e)}

    required = {"Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"}
    cols = set(df.columns)
    missing_cols = required - cols
    rows = len(df)
    dup = int(df.duplicated(subset=["Date"]).sum()) if "Date" in df.columns else 0
    na_counts = df[list(required & cols)].isna().sum().sum() if cols else 0

    dr = ""
    if "Date" in df.columns:
        d = pd.to_datetime(df["Date"], errors="coerce")
        dr = f"{d.min()} -> {d.max()}"

    return {
        "file": str(path),
        "type": "yahoo",
        "ok": len(missing_cols) == 0,
        "rows": rows,
        "missing_required_cols": ",".join(sorted(missing_cols)) if missing_cols else "",
        "duplicate_rows": dup,
        "na_cell_count": int(na_counts),
        "date_range": dr,
        "size_mb": round(_file_size_mb(path), 4),
    }


def _validate_fred_file(path: Path) -> dict:
    """ตรวจไฟล์ FRED รายไฟล์"""
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return {"file": str(path), "type": "fred", "ok": False, "error": str(e)}

    required = {"Date", "Value", "variable", "source"}
    cols = set(df.columns)
    missing_cols = required - cols
    rows = len(df)
    dup = int(df.duplicated(subset=["Date", "variable"]).sum()) if "Date" in df.columns else 0
    na_counts = df[["Date", "Value"]].isna().sum().sum() if {"Date", "Value"} <= cols else 0

    dr = ""
    if "Date" in df.columns:
        d = pd.to_datetime(df["Date"], errors="coerce")
        dr = f"{d.min()} -> {d.max()}"

    return {
        "file": str(path),
        "type": "fred",
        "ok": len(missing_cols) == 0,
        "rows": rows,
        "missing_required_cols": ",".join(sorted(missing_cols)) if missing_cols else "",
        "duplicate_rows": dup,
        "na_cell_count": int(na_counts),
        "date_range": dr,
        "size_mb": round(_file_size_mb(path), 4),
    }


def validate_raw_data() -> pd.DataFrame:
    ensure_all_directories()
    PATH_REPORTS.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    total_mb = 0.0
    total_files = 0
    total_rows = 0
    total_dup = 0
    total_na = 0

    for p in sorted(PATH_DATA_RAW_YAHOO.glob("*.csv")):
        r = _validate_yahoo_file(p)
        rows.append(r)
        total_files += 1
        if r.get("ok") and "size_mb" in r:
            total_mb += r["size_mb"]
            total_rows += r.get("rows", 0)
            total_dup += r.get("duplicate_rows", 0)
            total_na += r.get("na_cell_count", 0)

    for p in sorted(PATH_DATA_RAW_FRED.glob("*.csv")):
        r = _validate_fred_file(p)
        rows.append(r)
        total_files += 1
        if r.get("ok") and "size_mb" in r:
            total_mb += r["size_mb"]
            total_rows += r.get("rows", 0)
            total_dup += r.get("duplicate_rows", 0)
            total_na += r.get("na_cell_count", 0)

    summary_df = pd.DataFrame(rows)
    out_path = PATH_REPORTS / "data_quality_summary.csv"
    summary_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # สรุปโปรเจกต์
    pass_size = total_mb >= 200
    print("=" * 60)
    print("[validate_data] สรุปคุณภาพข้อมูล (raw)")
    print(f"  จำนวนไฟล์รวม     : {total_files}")
    print(f"  จำนวนแถวรวม (ประมาณจากไฟล์ที่อ่านได้): {total_rows}")
    print(f"  ขนาดรวม (MB)    : {total_mb:.2f}")
    print(f"  duplicate รวม  : {total_dup}")
    print(f"  missing cells   : {total_na}")
    print(f"  เกณฑ์ >= 200 MB : {'PASS' if pass_size else 'FAIL (ข้อมูลยังเล็ก — เพิ่ม ticker หรือช่วงปี)'}")
    print(f"  รายละเอียดไฟล์ : {out_path}")
    print("=" * 60)

    return summary_df


if __name__ == "__main__":
    validate_raw_data()
