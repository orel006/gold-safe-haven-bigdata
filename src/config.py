"""
การตั้งค่ารวมของโปรเจกต์ Gold Safe Haven Big Data
แก้ไขได้จากไฟล์เดียว — ใช้ pathlib รองรับ Windows
"""
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# รากโปรเจกต์ (โฟลเดอร์ที่มี src/, data/, app/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# ช่วงเวลา
# ---------------------------------------------------------------------------
START_DATE: str | None = None  # ถ้า None จะใช้ร่วมกับ USE_AUTO_LOOKBACK
END_DATE: str | None = None  # ถ้า None = วันนี้
USE_AUTO_LOOKBACK: bool = True
LOOKBACK_YEARS: int = 30

# ถ้า USE_AUTO_LOOKBACK = False ให้กำหนด START_DATE / END_DATE เป็น string "YYYY-MM-DD"
FIXED_START_DATE: str = "2010-01-01"
FIXED_END_DATE: str | None = None

# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------
YAHOO_INTERVAL: str = "1d"  # daily

# จัดกลุ่มเพื่อคอลัมน์ group ใน raw data
YAHOO_TICKER_GROUPS: Dict[str, List[str]] = {
    "gold": ["GC=F", "XAUUSD=X", "GLD", "IAU"],
    "stock_etf": ["SPY", "QQQ", "DIA", "IWM"],
    "bonds": ["TLT", "IEF", "SHY"],
    "usd": ["UUP"],
    "crypto": ["BTC-USD", "ETH-USD"],
    "commodities": ["SI=F", "SLV", "USO", "DBC"],
    "sector_etf": ["XLF", "XLK", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE"],
    "magnificent_7": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
}

# ทองหลักสำหรับการวิเคราะห์ (ใช้ในหลายโมดูล)
PRIMARY_GOLD_TICKER: str = "GC=F"

# ---------------------------------------------------------------------------
# FRED — รายการ series ที่ต้องดึง
# ---------------------------------------------------------------------------
FRED_SERIES_LIST: List[str] = [
    "SP500",
    "VIXCLS",
    "USREC",
    "FEDFUNDS",
    "EFFR",
    "CPIAUCSL",
    "DGS10",
    "DFII10",
    "T10YIE",
    "T10Y3M",
    "DTWEXBGS",
]

# ---------------------------------------------------------------------------
# Crisis / rolling / ML
# ---------------------------------------------------------------------------
VIX_CRISIS_THRESHOLD: float = 30.0
SPY_DRAWDOWN_CRISIS_THRESHOLD: float = -0.10  # -10%

ROLLING_WINDOWS: Dict[str, int] = {
    "short": 21,
    "medium": 63,
    "corr_short": 30,
    "corr_long": 90,
}

# Rolling correlation windows สำหรับ multi-window analysis
ROLLING_CORR_WINDOWS: List[int] = [30, 90, 180]

MODEL_RANDOM_SEED: int = 42

# ---------------------------------------------------------------------------
# Safe Haven Score — weights (รวมเป็น 1.0)
# ใช้ z-score normalization แต่ละมิติ แล้วถ่วง weighted sum
# ---------------------------------------------------------------------------
SAFE_HAVEN_WEIGHTS: Dict[str, float] = {
    "mean_crisis_return": 0.25,      # ผลตอบแทนเฉลี่ยช่วง crisis
    "outperform_spy_rate": 0.20,     # % วันที่ return > SPY ในช่วง crisis
    "low_max_drawdown": 0.15,        # max drawdown ตื้น = ดี
    "low_crisis_volatility": 0.10,   # volatility ต่ำช่วง crisis = ดี
    "neg_corr_with_spy": 0.15,       # correlation กับ SPY ลบ = safe haven
    "hit_rate": 0.15,                # % วันที่ return > 0 ช่วง crisis
}

# ---------------------------------------------------------------------------
# Named Crisis Events — ใช้ใน deep-dive analysis + per-crisis stats
# ---------------------------------------------------------------------------
NAMED_CRISIS_EVENTS: List[Dict] = [
    {
        "name": "Dotcom Bubble Burst",
        "start_date": "2000-03-10",
        "end_date": "2002-10-09",
        "description": "ฟองสบู่ดอทคอมแตก — Nasdaq ร่วง ~78% จากจุดสูงสุด",
    },
    {
        "name": "Global Financial Crisis (GFC)",
        "start_date": "2007-10-09",
        "end_date": "2009-03-09",
        "description": "วิกฤตซับไพรม์ → ล่มสลายของ Lehman Brothers → ตลาดทั่วโลกร่วงหนัก",
    },
    {
        "name": "European Debt Crisis",
        "start_date": "2010-04-23",
        "end_date": "2012-07-24",
        "description": "วิกฤตหนี้สาธารณะยุโรป — กรีซ ไอร์แลนด์ โปรตุเกส สเปน",
    },
    {
        "name": "China Crash / Oil Crash",
        "start_date": "2015-06-12",
        "end_date": "2016-02-11",
        "description": "ตลาดหุ้นจีนร่วง + ราคาน้ำมันดิบตกต่ำสุดในรอบสิบปี",
    },
    {
        "name": "COVID-19 Pandemic Crash",
        "start_date": "2020-02-19",
        "end_date": "2020-03-23",
        "description": "ตลาดร่วงเร็วที่สุดในประวัติศาสตร์จากการระบาดของ COVID-19",
    },
    {
        "name": "2022 Rate Hike / Inflation Shock",
        "start_date": "2022-01-03",
        "end_date": "2022-10-12",
        "description": "Fed ขึ้นดอกเบี้ยเร็วที่สุดในรอบ 40 ปี — หุ้นและพันธบัตรร่วงพร้อมกัน",
    },
]

# ---------------------------------------------------------------------------
# Path ทั้งหมด (ไม่ hardcode drive เฉพาะเครื่อง)
# ---------------------------------------------------------------------------
PATH_DATA_RAW_YAHOO = PROJECT_ROOT / "data" / "raw" / "yahoo"
PATH_DATA_RAW_FRED = PROJECT_ROOT / "data" / "raw" / "fred"
PATH_DATA_CLEANED = PROJECT_ROOT / "data" / "cleaned"
PATH_DATA_INTEGRATED = PROJECT_ROOT / "data" / "integrated"
PATH_DATA_PARQUET = PROJECT_ROOT / "data" / "parquet"
PATH_DATA_SPARK_OUTPUT = PROJECT_ROOT / "data" / "spark_output"
PATH_DATA_DASHBOARD = PROJECT_ROOT / "data" / "dashboard"
PATH_REPORTS = PROJECT_ROOT / "reports"
PATH_NOTEBOOKS = PROJECT_ROOT / "notebooks"

# โฟลเดอร์ legacy จาก Gold.py (junction ชี้ไป output เดิม)
PATH_LEGACY_OUTPUT = PROJECT_ROOT / "safe_haven_bigdata_output"


def ensure_all_directories() -> None:
    """สร้างโฟลเดอร์ที่จำเป็นทั้งหมด"""
    for p in [
        PATH_DATA_RAW_YAHOO,
        PATH_DATA_RAW_FRED,
        PATH_DATA_CLEANED,
        PATH_DATA_INTEGRATED,
        PATH_DATA_PARQUET,
        PATH_DATA_PARQUET / "asset_prices",
        PATH_DATA_SPARK_OUTPUT,
        PATH_DATA_DASHBOARD,
        PATH_REPORTS,
        PATH_NOTEBOOKS,
    ]:
        p.mkdir(parents=True, exist_ok=True)


def flatten_yahoo_tickers() -> List[tuple]:
    """คืน list ของ (group, ticker) ไม่ซ้ำ ticker"""
    seen = set()
    out: List[tuple] = []
    for group, tickers in YAHOO_TICKER_GROUPS.items():
        for t in tickers:
            if t not in seen:
                seen.add(t)
                out.append((group, t))
    return out


def resolve_date_range() -> tuple[str, str]:
    """
    คืน (start_date, end_date) เป็น string YYYY-MM-DD
    """
    import pandas as pd

    if USE_AUTO_LOOKBACK:
        end_ts = pd.Timestamp.today().normalize()
        start_ts = end_ts - pd.DateOffset(years=LOOKBACK_YEARS)
        return start_ts.strftime("%Y-%m-%d"), end_ts.strftime("%Y-%m-%d")

    end = FIXED_END_DATE or pd.Timestamp.today().strftime("%Y-%m-%d")
    start = START_DATE or FIXED_START_DATE
    return str(start), str(end)
