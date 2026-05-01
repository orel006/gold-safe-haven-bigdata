"""
ฟังก์ชันช่วยใช้ร่วมกันทั้งโปรเจกต์
"""
from pathlib import Path

import pandas as pd


def sanitize_filename(name: str) -> str:
    """แปลงชื่อ ticker/series ให้ใช้เป็นชื่อไฟล์ได้บน Windows"""
    bad = ["^", "=", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    out = str(name)
    for c in bad:
        out = out.replace(c, "_")
    return out


def normalize_yahoo_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    แปลงผล yfinance ให้มีคอลัมน์มาตรฐานก่อนเซฟ raw
    """
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = [c[0] if isinstance(c, tuple) else c for c in x.columns]
    x.columns = [str(c).strip() for c in x.columns]
    x.index = pd.to_datetime(x.index, errors="coerce")
    for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        if col not in x.columns:
            x[col] = pd.NA
    x = x[["Open", "High", "Low", "Close", "Adj Close", "Volume"]].copy()
    x = x.reset_index().rename(columns={"index": "Date"})
    x["Date"] = pd.to_datetime(x["Date"], errors="coerce")
    return x
