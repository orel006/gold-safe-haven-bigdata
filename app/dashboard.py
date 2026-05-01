"""
Gold Safe Haven Analytics — Premium Dashboard
===============================================
Streamlit + Plotly  ·  Yahoo Finance + FRED
รัน:  py -m streamlit run app/dashboard.py
"""

import base64
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

# ── paths ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "data" / "dashboard"
REPORTS = ROOT / "reports"

# ── design tokens ──────────────────────────────────────
GOLD      = "#D4A528"
GOLD_L    = "#FDE047"
GOLD_D    = "#B45309"
NAVY      = "#0B1120"
NAVY_L    = "#1E293B"
SLATE     = "#334155"
BG        = "#020617"
CARD      = "rgba(15, 23, 42, 0.6)"
BORDER    = "rgba(212, 165, 40, 0.15)"
TXT       = "#F8FAFC"
TXT2      = "#94A3B8"
TXT3      = "#64748B"
GREEN     = "#10B981"
RED       = "#EF4444"
BLUE      = "#3B82F6"
PURPLE    = "#8B5CF6"
CYAN      = "#06B6D4"
ORANGE    = "#F97316"
PINK      = "#EC4899"
CW        = [GOLD_L, CYAN, GREEN, PURPLE, RED, BLUE, ORANGE, PINK, "#6366F1", "#14B8A6"]

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    font=dict(family="'Inter','Sarabun',sans-serif", color=TXT, size=13),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=CW,
    hoverlabel=dict(bgcolor="rgba(15,23,42,0.9)", font_size=13, bordercolor=GOLD),
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", gridwidth=1, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", gridwidth=1, zeroline=False),
    margin=dict(l=48, r=24, t=60, b=48),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12, color=TXT)),
)

# ── page config (MUST be first st.* call) ─────────────
st.set_page_config(
    page_title="Gold Safe Haven · Big Data Analytics",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════
# CSS  – premium theme with animations
# ═══════════════════════════════════════════════════════
def inject_css() -> None:
    _css = '''
<style>
/* animations */
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes fadeUp {
  from { opacity:0; transform:translateY(12px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes pulseGold {
  0%,100% { opacity:.45; transform:scale(1); }
  50%     { opacity:.85; transform:scale(1.06); }
}

/* global */
html, body, div, span, p, h1, h2, h3, label, input, button, select {
  font-family:'Sarabun','Inter',sans-serif !important;
  color: __TXT__;
}
.stApp {
  background-color: __BG__ !important;
  background-image: radial-gradient(circle at 10% 20%, rgba(15, 23, 42, 0.8) 0%, __BG__ 90%);
}
.main .block-container {
  padding-top:.4rem; padding-bottom:2rem; max-width:1300px;
}
h1,h2,h3 { letter-spacing:-0.02em; color: __TXT__ !important; }

/* sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #020617 0%, #0B1120 100%) !important;
  border-right: 1px solid rgba(212, 165, 40, 0.2) !important;
  box-shadow: 4px 0 24px rgba(0,0,0,0.5);
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small {
  color:#CBD5E1 !important;
}

/* style radio group as a nav menu */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
  gap: 12px;
  padding-top: 5px;
}
[data-testid="stSidebar"] .stRadio label {
  font-weight:600 !important;
  font-size:15.5px !important;
  padding:14px 18px !important;
  margin:0 !important;
  border-radius:12px;
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  transition: all .3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  display: flex !important;
  align-items: center;
}
/* hide the default radio circle */
[data-testid="stSidebar"] .stRadio label > div:first-child {
  display:none !important;
}
[data-testid="stSidebar"] .stRadio label div[data-testid="stMarkdownContainer"] {
  width: 100%;
}

/* hover state */
[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(212, 165, 40, 0.15) !important;
  border-color: rgba(212, 165, 40, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.4);
}
[data-testid="stSidebar"] .stRadio label:hover p {
  color:__GOLDL__ !important;
  text-shadow: 0 0 12px rgba(253,224,71,0.6);
}

/* active/checked state */
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: linear-gradient(90deg, rgba(212, 165, 40, 0.25) 0%, rgba(15, 23, 42, 0.4) 100%) !important;
  border-left: 4px solid __GOLDL__ !important;
  border-top: 1px solid rgba(212, 165, 40, 0.4) !important;
  border-bottom: 1px solid rgba(212, 165, 40, 0.4) !important;
  border-right: 1px solid rgba(212, 165, 40, 0.1) !important;
  border-radius: 6px 14px 14px 6px;
  box-shadow: 0 8px 20px rgba(0,0,0,0.5), inset 0 0 10px rgba(212, 165, 40, 0.1);
  transform: scale(1.02);
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) p {
  color:__GOLDL__ !important;
  font-weight: 800 !important;
  text-shadow: 0 0 15px rgba(212, 165, 40, 0.8);
  letter-spacing: 0.02em;
}

[data-testid="stSidebar"] code {
  background:rgba(255,255,255,.05) !important;
  color:__GOLDL__ !important;
  border-radius:6px; padding:2px 8px;
}

/* metric cards (GLASSMORPHISM) */
[data-testid="stMetric"], .kpi-box {
  background: rgba(15, 23, 42, 0.4) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border:1px solid __BORDER__ !important;
  border-left:4px solid __GOLD__ !important;
  border-radius:14px !important;
  padding:16px 18px !important;
  box-shadow:0 8px 32px rgba(0,0,0,0.3) !important;
  animation: fadeUp .5s ease both !important;
}
[data-testid="stMetricLabel"] {
  color:__TXT2__ !important; font-size:13px !important;
}
[data-testid="stMetricValue"] {
  color:__TXT__ !important; font-weight:800 !important; font-size:24px !important;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5) !important;
}
[data-testid="stMetricDelta"] > div {
  font-weight:600 !important;
}

/* plotly charts */
div[data-testid="stPlotlyChart"] {
  border:1px solid __BORDER__;
  border-radius:16px;
  overflow:hidden;
  box-shadow:0 8px 32px rgba(0,0,0,0.25);
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(16px);
  transition: box-shadow .3s ease, transform .3s ease, border-color .3s ease;
  animation: fadeUp .6s ease both;
}
div[data-testid="stPlotlyChart"]:hover {
  box-shadow:0 12px 48px rgba(0,0,0,0.4);
  transform:translateY(-2px);
  border-color: rgba(212, 165, 40, 0.4);
}

/* dataframes */
div[data-testid="stDataFrame"] {
  border-radius:14px;
  overflow:hidden;
  border:1px solid __BORDER__;
  box-shadow:0 8px 24px rgba(0,0,0,0.3);
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(8px);
  animation: fadeUp .5s ease both;
}

/* expanders */
div[data-testid="stExpander"] {
  border:1px solid __BORDER__;
  border-radius:14px;
  background:rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(8px);
}
div[data-testid="stExpander"] summary p {
    color: __TXT__ !important;
    font-weight: 600;
}

/* alerts */
div[data-testid="stAlert"] { border-radius:14px !important; }

/* section header */
.gh-section {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.7) 0%, rgba(2, 6, 23, 0.8) 100%);
  backdrop-filter: blur(12px);
  border:1px solid __BORDER__;
  border-radius:16px;
  padding:16px 22px 12px;
  margin:8px 0 22px;
  box-shadow:0 8px 32px rgba(0,0,0,0.3);
  animation: fadeUp .45s ease both;
  position:relative; overflow:hidden;
}
.gh-section::before {
  content:""; display:block; width:56px; height:4px;
  border-radius:999px;
  background:linear-gradient(90deg,__GOLD__,__GOLDL__);
  margin-bottom:10px;
  box-shadow: 0 0 10px rgba(212, 165, 40, 0.6);
}
.gh-section h3 {
  margin:0 0 2px !important; font-size:1.25rem !important;
  font-weight:700 !important; color:__TXT__ !important;
}
.gh-section p {
  margin:0; color:__TXT2__; font-size:.92rem;
}

/* KPI grid */
.kpi-grid {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px; margin:8px 0 20px;
}
.kpi-box .kpi-label {
  font-size:12px; color:__TXT3__; text-transform:uppercase;
  letter-spacing:.06em; font-weight:600; margin-bottom:4px;
}
.kpi-box .kpi-value {
  font-size:26px; font-weight:800; color:__TXT__;
  font-family:'Inter','Sarabun',sans-serif;
  line-height:1.15; text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}
.kpi-box .kpi-sub {
  font-size:12px; color:__TXT2__; margin-top:2px;
}

/* insight cards */
.insight-card {
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(12px);
  border:1px solid __BORDER__;
  border-radius:16px;
  padding:18px 20px;
  margin-bottom:14px;
  box-shadow:0 8px 32px rgba(0,0,0,0.25);
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
  animation: fadeUp .5s ease both;
}
.insight-card:hover {
  transform:translateY(-3px);
  box-shadow:0 12px 40px rgba(0,0,0,0.4);
  border-color: rgba(212, 165, 40, 0.4);
}
.insight-card .ic-icon {
  font-size:28px; margin-bottom:6px;
  text-shadow: 0 0 15px rgba(255,255,255,0.2);
}
.insight-card .ic-title {
  font-size:15px; font-weight:700; color:__GOLDL__; margin-bottom:4px;
}
.insight-card .ic-body {
  font-size:13px; color:__TXT__; line-height:1.55; opacity: 0.9;
}

/* medal row */
.medal-row {
  display:flex; align-items:center; gap:10px;
  background:linear-gradient(135deg, rgba(30,41,59,0.7), rgba(15,23,42,0.9));
  backdrop-filter: blur(10px);
  border:1px solid rgba(212, 165, 40, 0.3);
  border-radius:14px;
  padding:14px 18px;
  margin-bottom:10px;
  animation: fadeUp .45s ease both;
  box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.medal-row .medal {
  font-size:32px; line-height:1; filter: drop-shadow(0 0 8px rgba(255,255,255,0.2));
}
.medal-row .medal-info {
  flex:1;
}
.medal-row .medal-name {
  font-weight:700; font-size:16px; color:__GOLDL__;
}
.medal-row .medal-stat {
  font-size:13px; color:__TXT2__;
}
.medal-silver { border-color: rgba(148, 163, 184, 0.3); }
.medal-bronze { border-color: rgba(180, 83, 9, 0.3); }

/* divider */
hr {
  border:none; border-top:1px solid rgba(255,255,255,0.08); margin:1.2rem 0;
}

/* hide defaults */
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
</style>
'''
    # Replace color placeholders with actual values
    _css = (_css
        .replace("__GOLD__", GOLD).replace("__GOLDL__", GOLD_L)
        .replace("__NAVY__", NAVY).replace("__NAVYL__", NAVY_L)
        .replace("__BORDER__", BORDER).replace("__BG__", BG)
        .replace("__TXT__", TXT).replace("__TXT2__", TXT2).replace("__TXT3__", TXT3)
    )
    # Google Fonts
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sarabun:wght@400;500;600;700&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    
    style_start = _css.find("<style>")
    style_end = _css.find("</style>") + len("</style>")
    if style_start >= 0 and style_end > style_start:
        style_block = _css[style_start:style_end]
        try:
            st.html(style_block)
        except AttributeError:
            components.html(style_block, height=0, scrolling=False)



# ═══════════════════════════════════════════════════════
# BANNER  – animated HTML component
# ═══════════════════════════════════════════════════════
def render_banner() -> None:
    logo_path = Path(__file__).parent / "logo.png"
    img_tag = ""
    if logo_path.exists():
        import base64
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        img_tag = f'<img src="data:image/png;base64,{b64}" class="logo-img" alt="Logo"/>'

    html_str = f"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@600;800&family=Sarabun:wght@600;700&display=swap');
*{{box-sizing:border-box;margin:0}}
body{{margin:0;font-family:'Inter','Sarabun',sans-serif; background: transparent;}}
.wrap{{
  height:140px;border-radius:18px;position:relative;overflow:hidden;color:#f8fafc;
  padding:16px 22px;
  background:linear-gradient(125deg,#0B1120 0%,#0F172A 40%,#9A7B1A 140%);
  box-shadow:0 16px 48px rgba(0,0,0,0.5);
  border: 1px solid rgba(212,165,40,0.2);
  display: flex; align-items: center; gap: 20px;
}}
.glow{{position:absolute;top:-60%;right:-15%;width:260px;height:260px;
  background:radial-gradient(circle,rgba(212,165,40,0.25) 0%,rgba(212,165,40,0) 70%);
  animation:pulse 5s ease-in-out infinite; pointer-events: none;
}}
@keyframes pulse{{0%,100%{{opacity:.4;transform:scale(1)}}50%{{opacity:.85;transform:scale(1.08)}}}}
.shimmer{{position:absolute;top:0;left:0;right:0;bottom:0;
  background:linear-gradient(90deg,transparent 30%,rgba(212,165,40,0.08) 50%,transparent 70%);
  background-size:200% 100%;animation:shm 3s linear infinite; pointer-events: none;
}}
@keyframes shm{{0%{{background-position:-200% 0}}100%{{background-position:200% 0}}}}
.logo-img{{
  width: 90px; height: 90px; border-radius: 16px; object-fit: cover;
  box-shadow: 0 0 20px rgba(212,165,40,0.4);
  border: 1px solid rgba(212,165,40,0.5);
  animation: float 4s ease-in-out infinite;
}}
@keyframes float {{
  0%, 100% {{ transform: translateY(0px); }}
  50% {{ transform: translateY(-5px); box-shadow: 0 5px 25px rgba(212,165,40,0.6); }}
}}
.content {{ z-index: 2; position: relative; flex: 1; }}
.tag{{display:inline-block;font-size:10px;letter-spacing:.18em;text-transform:uppercase;
  opacity:.8;background:rgba(255,255,255,0.05);padding:3px 10px;border-radius:999px;
  border:1px solid rgba(212,165,40,0.3);margin-bottom:8px; color: #FDE047;}}
.title{{
  font-size:26px;font-weight:800;text-shadow:0 2px 16px rgba(0,0,0,0.8);
  line-height:1.15; background: -webkit-linear-gradient(0deg, #FFFFFF, #FDE047);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.sub{{margin-top:5px;font-size:13px;opacity:.88;max-width:90%; color:#CBD5E1;}}
.pills{{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}}
.pill{{font-size:10px;padding:3px 10px;border-radius:999px;
  background:rgba(15,23,42,0.6);border:1px solid rgba(255,255,255,0.15);color:#e2e8f0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);}}
</style></head><body>
<div class="wrap">
  <div class="glow"></div><div class="shimmer"></div>
  {img_tag}
  <div class="content">
      <div class="tag">University Big Data Project · Safe Haven Analysis</div>
      <div class="title">Gold Safe Haven Analytics</div>
      <div class="sub">วิเคราะห์ทองคำในฐานะสินทรัพย์ปลอดภัยด้วย Big Data Pipeline — Yahoo Finance + FRED + ML</div>
      <div class="pills">
        <span class="pill">Streamlit Premium</span>
        <span class="pill">Plotly Dark</span>
        <span class="pill">30 ปีข้อมูล</span>
        <span class="pill">35 สินทรัพย์</span>
      </div>
  </div>
</div>
</body></html>"""
    try:
        components.html(html_str, height=145, scrolling=False)
    except Exception:
        st.markdown("### 🏆 Gold Safe Haven Analytics")


# ═══════════════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════════════

ASSET_MAP = {
    "GC=F": "XAUUSD GOLD",
    "GLD": "GLD (Gold ETF)",
    "SI=F": "XAGUSD (Silver)",
    "SPY": "SPY (S&P 500)",
    "TLT": "TLT (20Y Bond)",
    "BTC-USD": "BTC (Bitcoin)",
    "ETH-USD": "ETH (Ethereum)",
    "UUP": "UUP (US Dollar)",
}

def map_assets(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty and "asset" in df.columns:
        df["asset"] = df["asset"].apply(lambda x: ASSET_MAP.get(x, x))
    return df

@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    p = DASH / name
    return map_assets(pd.read_csv(p)) if p.exists() else pd.DataFrame()


@st.cache_data
def load_parquet(name: str) -> pd.DataFrame:
    p = DASH / name
    return map_assets(pd.read_parquet(p)) if p.exists() else pd.DataFrame()


def apply_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=TXT), x=0, xanchor="left"),
        **PLOTLY_LAYOUT,
    )
    return fig


def section(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="gh-section"><h3>{icon}  {title}</h3><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def kpi_html(items: list) -> None:
    """Render a grid of KPI cards. Each item = (label, value, sub)."""
    cards = ""
    for label, value, sub in items:
        cards += f"""
        <div class="kpi-box">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>"""
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def insight_card(icon: str, title: str, body: str) -> str:
    return f"""
    <div class="insight-card">
        <div class="ic-icon">{icon}</div>
        <div class="ic-title">{title}</div>
        <div class="ic-body">{body}</div>
    </div>"""


def empty_state(msg: str, hint: str) -> None:
    st.info(msg)
    st.caption(hint)


def classify_asset(name: str) -> str:
    gold = {"GC=F", "GLD", "IAU", "XAUUSD=X", "XAUUSD GOLD", "GLD (Gold ETF)"}
    bond = {"TLT", "IEF", "SHY", "TLT (20Y Bond)"}
    crypto = {"BTC-USD", "ETH-USD", "BTC (Bitcoin)", "ETH (Ethereum)"}
    commodity = {"SI=F", "SLV", "USO", "DBC", "XAGUSD (Silver)"}
    usd = {"UUP", "UUP (US Dollar)"}
    if name in gold:
        return "🥇 ทอง"
    if name in bond:
        return "📜 พันธบัตร"
    if name in crypto:
        return "₿ Crypto"
    if name in commodity:
        return "🛢️ สินค้าโภคภัณฑ์"
    if name in usd:
        return "💵 ดอลลาร์"
    return "📈 หุ้น/ETF"


PERIOD_PRESETS = {
    "All Data": None,
    "Dot-com Crash": ("2000-03-10", "2002-10-09"),
    "2008 Global Financial Crisis": ("2007-10-09", "2009-03-09"),
    "COVID Crash": ("2020-02-19", "2020-03-23"),
    "2022 Inflation / Rate Shock": ("2022-01-03", "2022-10-12"),
    "Custom Range": None,
}

CORE_ASSETS = ["XAUUSD GOLD", "SPY (S&P 500)", "TLT (20Y Bond)", "UUP (US Dollar)", "BTC (Bitcoin)"]

SAFE_HAVEN_WEIGHTS = {
    "mean_crisis_return": 0.25,
    "outperform_spy_rate": 0.20,
    "low_max_drawdown": 0.15,
    "low_crisis_volatility": 0.10,
    "neg_corr_with_spy": 0.15,
    "hit_rate": 0.15,
}


def _date_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """หา min/max date จาก processed dashboard data เพื่อใช้เป็นกรอบ date picker"""
    if df.empty or "date" not in df.columns:
        today = pd.Timestamp.today().normalize()
        return today - pd.DateOffset(years=5), today
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        today = pd.Timestamp.today().normalize()
        return today - pd.DateOffset(years=5), today
    return dates.min().normalize(), dates.max().normalize()


def _clamp_date(ts: pd.Timestamp, min_date: pd.Timestamp, max_date: pd.Timestamp) -> pd.Timestamp:
    """บังคับวันที่ไม่ให้ออกนอกช่วงข้อมูลจริง"""
    return max(min_date, min(max_date, pd.Timestamp(ts).normalize()))


def filter_date(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """กรองข้อมูล processed ตามช่วงเวลาที่ผู้ใช้เลือก"""
    if df.empty or "date" not in df.columns:
        return df.copy()
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    return out[(out["date"] >= start) & (out["date"] <= end)].copy()


def filter_assets(df: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    """กรองข้อมูลตาม asset selector กลาง"""
    if df.empty or "asset" not in df.columns or not assets:
        return df.iloc[0:0].copy() if "asset" in df.columns else df.copy()
    return df[df["asset"].isin(assets)].copy()


def prepare_period_panel(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    rolling_window: int,
) -> pd.DataFrame:
    """
    สร้าง metrics ใหม่ตามช่วงเวลาที่ผู้ใช้เลือก
    ใช้ processed data จาก data/dashboard/analysis_panel.parquet เท่านั้น
    """
    out = filter_date(df, start, end)
    if out.empty or "asset" not in out.columns:
        return out
    out = out.sort_values(["asset", "date"]).copy()
    px_col = "adj_close" if "adj_close" in out.columns else "close"
    out["_px"] = pd.to_numeric(out[px_col], errors="coerce")
    out["period_return"] = out.groupby("asset")["_px"].pct_change()

    def _cum_from_first(s: pd.Series) -> pd.Series:
        valid = pd.to_numeric(s, errors="coerce").dropna()
        if valid.empty or valid.iloc[0] == 0:
            return pd.Series(np.nan, index=s.index)
        return s / valid.iloc[0] - 1

    out["period_cum"] = out.groupby("asset")["_px"].transform(_cum_from_first)
    out["period_drawdown"] = out.groupby("asset")["_px"].transform(lambda s: s / s.cummax() - 1)
    out["period_volatility"] = out.groupby("asset")["period_return"].transform(
        lambda s: s.rolling(rolling_window, min_periods=max(5, rolling_window // 3)).std()
    )
    return out


def build_regime_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ crisis vs normal summary ใหม่ตาม global filters"""
    if panel.empty or "final_crisis_label" not in panel.columns:
        return pd.DataFrame()
    tmp = panel.dropna(subset=["period_return"]).copy()
    tmp["regime"] = np.where(tmp["final_crisis_label"] == 1, "crisis", "normal")
    return tmp.groupby(["asset", "regime"])["period_return"].mean().reset_index(name="mean")


def build_return_ranking(panel: pd.DataFrame) -> pd.DataFrame:
    """Return Ranking ตามช่วงเวลาที่เลือก ใช้เฉพาะ crisis days"""
    if panel.empty or "final_crisis_label" not in panel.columns:
        return pd.DataFrame()
    c = panel[(panel["final_crisis_label"] == 1) & panel["period_return"].notna()].copy()
    if c.empty:
        return pd.DataFrame()
    rank = c.groupby("asset")["period_return"].agg(["mean", "std", "count"]).reset_index()
    rank = rank.sort_values("mean", ascending=False).reset_index(drop=True)
    rank["rank"] = range(1, len(rank) + 1)
    return rank


def build_market_breadth(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """คำนวณ market breadth ใหม่จาก processed panel หลังกรองช่วงเวลา/asset"""
    if panel.empty or "final_crisis_label" not in panel.columns:
        return pd.DataFrame(), pd.DataFrame()
    c = panel[(panel["final_crisis_label"] == 1) & panel["period_return"].notna()].copy()
    if c.empty:
        return pd.DataFrame(), pd.DataFrame()
    asset_stats = c.groupby("asset").agg(
        mean_return=("period_return", "mean"),
        max_drawdown=("period_drawdown", "min"),
    ).reset_index()
    spy_mean = c[c["asset"] == "SPY (S&P 500)"]["period_return"].mean()
    spy_dd = c[c["asset"] == "SPY (S&P 500)"]["period_drawdown"].min()
    total = len(asset_stats)
    out = pd.DataFrame([{
        "total_assets": total,
        "advance_count": int((asset_stats["mean_return"] > 0).sum()),
        "decline_count": int((asset_stats["mean_return"] <= 0).sum()),
        "pct_positive_crisis": round((asset_stats["mean_return"] > 0).mean() * 100, 1),
        "pct_outperform_spy": round((asset_stats["mean_return"] > spy_mean).mean() * 100, 1) if pd.notna(spy_mean) else 0,
        "pct_low_drawdown": round((asset_stats["max_drawdown"] > spy_dd).mean() * 100, 1) if pd.notna(spy_dd) else 0,
        "spy_mean_crisis_return": spy_mean,
        "spy_max_drawdown": spy_dd,
    }])

    if "group" in c.columns:
        by_group = c.groupby(["group", "asset"])["period_return"].mean().reset_index()
        by_group = by_group.groupby("group").agg(
            total=("asset", "nunique"),
            advance=("period_return", lambda s: int((s > 0).sum())),
        ).reset_index()
        by_group["decline"] = by_group["total"] - by_group["advance"]
        by_group["pct_positive"] = (by_group["advance"] / by_group["total"] * 100).round(1)
    else:
        by_group = pd.DataFrame()
    return out, by_group


def build_risk_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ rolling volatility/drawdown ใหม่ตามช่วงเวลาและ rolling window"""
    if panel.empty:
        return pd.DataFrame()
    tmp = panel.dropna(subset=["period_return"]).copy()
    if tmp.empty:
        return pd.DataFrame()
    return tmp.groupby("asset").agg(
        rolling_volatility=("period_volatility", "mean"),
        drawdown=("period_drawdown", "mean"),
        max_drawdown=("period_drawdown", "min"),
        mean_return=("period_return", "mean"),
    ).reset_index()


def build_safe_haven_ranking(panel_date: pd.DataFrame, selected_assets: list[str]) -> pd.DataFrame:
    """
    คำนวณ Safe Haven Score ใหม่ตาม global date filter
    ใช้ panel_date ที่ยังมี SPY แม้ผู้ใช้ไม่ได้เลือก SPY เพื่อใช้เป็น benchmark
    """
    if panel_date.empty or "final_crisis_label" not in panel_date.columns:
        return pd.DataFrame()
    c = panel_date[(panel_date["final_crisis_label"] == 1) & panel_date["period_return"].notna()].copy()
    if c.empty:
        return pd.DataFrame()
    spy_ret = c[c["asset"] == "SPY (S&P 500)"][["date", "period_return"]].drop_duplicates("date")
    spy_ret = spy_ret.rename(columns={"period_return": "spy_ret"})
    records = []
    for asset, g in c[c["asset"].isin(selected_assets)].groupby("asset"):
        ret = g["period_return"].dropna()
        if len(ret) < 5:
            continue
        merged = g[["date", "period_return"]].merge(spy_ret, on="date", how="inner")
        corr_val = merged["period_return"].corr(merged["spy_ret"]) if len(merged) >= 10 else 0
        records.append({
            "asset": asset,
            "mean_crisis_return": ret.mean(),
            "outperform_spy_rate": (merged["period_return"] > merged["spy_ret"]).mean() if len(merged) else 0,
            "max_drawdown_crisis": g["period_drawdown"].min(),
            "crisis_volatility": ret.std(),
            "corr_with_spy": corr_val if pd.notna(corr_val) else 0,
            "hit_rate": (ret > 0).mean(),
            "crisis_days": len(ret),
        })
    raw = pd.DataFrame(records)
    if raw.empty:
        return raw

    def zscore(s: pd.Series) -> pd.Series:
        std = s.std()
        if std == 0 or pd.isna(std):
            return pd.Series(0, index=s.index)
        return (s - s.mean()) / std

    raw["z_return"] = zscore(raw["mean_crisis_return"])
    raw["z_outperform"] = zscore(raw["outperform_spy_rate"])
    raw["z_drawdown"] = zscore(-raw["max_drawdown_crisis"].abs())
    raw["z_vol"] = zscore(-raw["crisis_volatility"])
    raw["z_corr"] = zscore(-raw["corr_with_spy"])
    raw["z_hit"] = zscore(raw["hit_rate"])
    w = SAFE_HAVEN_WEIGHTS
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
    return raw


# ═══════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════
inject_css()
render_banner()

PAGES = {
    "overview":    "📊  ภาพรวม",
    "breadth":     "🌐  Market Breadth",
    "crisis":      "⚡  วิเคราะห์วิกฤต",
    "deep":        "🔍  เจาะลึกวิกฤต",
    "portfolio":   "🎮  Portfolio Simulator",
    "corr":        "🔗  Rolling Correlation",
    "return_rank": "📊  Return Ranking",
    "safe_haven":  "🛡️  Safe Haven Leaderboard",
    "risk":        "📈  Risk / Volatility",
    "ml":          "🤖  ML Leaderboard",
    "insights":    "💡  Insights",
    "bottom":      "💎  Bottom Line",
    "transform":   "⚙️  Transformation Summary",
}

PANEL_RAW = load_parquet("analysis_panel.parquet")
if PANEL_RAW.empty:
    PANEL_RAW = load_parquet("price_trends.parquet")

DATA_MIN_DATE, DATA_MAX_DATE = _date_bounds(PANEL_RAW)
ALL_ASSETS = sorted(PANEL_RAW["asset"].dropna().unique().tolist()) if not PANEL_RAW.empty and "asset" in PANEL_RAW.columns else []
DEFAULT_ASSETS = [a for a in CORE_ASSETS if a in ALL_ASSETS] or ALL_ASSETS[:5]

with st.sidebar:
    st.markdown("### 🧭 เมนู")
    page_key = st.radio(
        "เลือกหน้า",
        list(PAGES.keys()),
        format_func=lambda k: PAGES[k],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("### 🎛️ Global Controls")
    selected_period = st.selectbox("Preset Period", list(PERIOD_PRESETS.keys()), index=0)

    if selected_period in PERIOD_PRESETS and PERIOD_PRESETS[selected_period]:
        preset_start, preset_end = PERIOD_PRESETS[selected_period]
        active_start = _clamp_date(pd.Timestamp(preset_start), DATA_MIN_DATE, DATA_MAX_DATE)
        active_end = _clamp_date(pd.Timestamp(preset_end), DATA_MIN_DATE, DATA_MAX_DATE)
    else:
        active_start, active_end = DATA_MIN_DATE, DATA_MAX_DATE

    if selected_period == "Custom Range":
        picked = st.date_input(
            "Date Range",
            value=(active_start.date(), active_end.date()),
            min_value=DATA_MIN_DATE.date(),
            max_value=DATA_MAX_DATE.date(),
            help="เลือกช่วงวันที่เอง ผลลัพธ์ทุกหน้าจะคำนวณใหม่ตามช่วงนี้",
        )
        if isinstance(picked, tuple) and len(picked) == 2:
            active_start, active_end = pd.Timestamp(picked[0]), pd.Timestamp(picked[1])
    else:
        st.date_input(
            "Date Range",
            value=(active_start.date(), active_end.date()),
            min_value=DATA_MIN_DATE.date(),
            max_value=DATA_MAX_DATE.date(),
            disabled=True,
            help="เลือก Custom Range เพื่อกำหนดวันที่เอง",
        )

    if active_start > active_end:
        active_start, active_end = active_end, active_start

    rolling_window = st.selectbox(
        "Rolling Window",
        [30, 90, 180],
        index=1,
        format_func=lambda n: f"{n} วัน",
        help="ใช้กับ Rolling Correlation และ Rolling Volatility",
    )

    selected_assets = st.multiselect(
        "Assets",
        ALL_ASSETS,
        default=DEFAULT_ASSETS,
        help="เลือกได้หลายสินทรัพย์ เช่น Gold, SPY, TLT, UUP, BTC",
    )
    if not selected_assets and DEFAULT_ASSETS:
        st.warning("เลือก asset อย่างน้อย 1 ตัว")

    st.caption(f"Active range: {active_start.date()} → {active_end.date()}")
    st.divider()
    st.markdown(
        """
<small style="color:#94A3B8">
ข้อมูลจาก <code>data/dashboard/</code><br/>
แหล่งข้อมูล: Yahoo Finance · FRED<br/>
</small>
""",
        unsafe_allow_html=True,
    )

PANEL_DATE = prepare_period_panel(PANEL_RAW, active_start, active_end, rolling_window)
PANEL = filter_assets(PANEL_DATE, selected_assets)

st.info(
    "ใช้ Global Controls ใน sidebar เพื่อเลือกช่วงเวลา, rolling window และ asset ได้เอง "
    "ผลลัพธ์อาจเปลี่ยนตาม regime/ช่วงเวลา จึงไม่ควรตีความจาก full-period average เพียงอย่างเดียว"
)


# ═══════════════════════════════════════════════════════
# PAGE:  ภาพรวม
# ═══════════════════════════════════════════════════════
if page_key == "overview":
    section("📊", "ภาพรวม", "ราคาสินทรัพย์ ผลตอบแทนสะสม และ KPI หลักของการศึกษา")

    prices = PANEL.copy()
    ranking = build_safe_haven_ranking(PANEL_DATE, selected_assets)

    # ── KPI row ──
    n_assets = prices["asset"].nunique() if not prices.empty else 0
    n_rows = f"{len(prices):,}" if not prices.empty else "—"
    date_range = "—"
    if not prices.empty and "date" in prices.columns:
        d = pd.to_datetime(prices["date"], errors="coerce")
        date_range = f"{d.min().strftime('%Y-%m')}  →  {d.max().strftime('%Y-%m')}"

    gold_rank_str = "—"
    if not ranking.empty:
        score_col = "safe_haven_score" if "safe_haven_score" in ranking.columns else "mean"
        rk = ranking.sort_values(score_col, ascending=False).reset_index(drop=True)
        gr = rk.index[rk["asset"] == "XAUUSD GOLD"]
        if len(gr):
            gold_rank_str = f"#{gr[0]+1} / {len(rk)}"

    kpi_html([
        ("สินทรัพย์ที่ติดตาม", f"{n_assets}  ตัว", "Yahoo + FRED"),
        ("จุดข้อมูลทั้งหมด", n_rows, "analysis_panel.parquet"),
        ("ช่วงเวลาข้อมูล", date_range, selected_period),
        ("อันดับทอง (Safe Haven)", gold_rank_str, "จาก composite score 6 มิติ"),
    ])

    # ── price chart ──
    if prices.empty:
        empty_state("ยังไม่มี analysis_panel.parquet", "รัน pipeline ให้เสร็จก่อน")
    else:
        norm = st.checkbox("Normalize ราคา = 100", value=True)

        if selected_assets:
            sub = prices.copy()
            sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
            sub = sub.sort_values(["asset", "date"])

            if norm:
                sub["_y"] = (sub["period_cum"] + 1) * 100
                y_label = "ราคา (normalize = 100)"
            else:
                sub["_y"] = sub["_px"]
                y_label = "Adj Close (USD)"

            fig = px.line(sub, x="date", y="_y", color="asset", hover_data={"_y": ":.2f"})
            fig = apply_layout(fig, y_label)
            fig.update_xaxes(title_text="")
            fig.update_yaxes(title_text=y_label)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("เลือกสินทรัพย์อย่างน้อย 1 ตัว")

    # ── cumulative return ──
    if not prices.empty and "period_cum" in prices.columns:
        st.markdown("---")
        st.markdown("#### 📈 ผลตอบแทนสะสม (Cumulative Return)")
        cum_sub = prices.dropna(subset=["period_cum"]).copy()
        if not cum_sub.empty:
            fig2 = px.line(cum_sub, x="date", y="period_cum", color="asset")
            fig2 = apply_layout(fig2, "Cumulative Return")
            fig2.update_yaxes(title_text="Cumulative Return", tickformat=".0%")
            st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE:  Market Breadth
# ═══════════════════════════════════════════════════════
elif page_key == "breadth":
    section("🌐", "Market Breadth ช่วงวิกฤต",
            "ดูภาพรวมว่าช่วง crisis มีสินทรัพย์กี่ตัวที่ยังเป็นบวก และกลุ่มไหนช่วยป้องกันพอร์ตได้จริง")

    breadth, by_group = build_market_breadth(PANEL)

    if breadth.empty:
        empty_state("ไม่มี market_breadth.csv", "รัน spark_transform + generate_dashboard_data")
    else:
        b = breadth.iloc[0]
        kpi_html([
            ("สินทรัพย์ทั้งหมด", f"{int(b.get('total_assets', 0)):,}", "นับเฉพาะช่วง crisis"),
            ("เป็นบวก", f"{int(b.get('advance_count', 0)):,}", f"{b.get('pct_positive_crisis', 0):.1f}% ของสินทรัพย์"),
            ("ติดลบ", f"{int(b.get('decline_count', 0)):,}", "decline count"),
            ("ชนะ SPY", f"{b.get('pct_outperform_spy', 0):.1f}%", "outperform rate"),
        ])

        c1, c2 = st.columns([1, 1])
        with c1:
            adv = int(b.get("advance_count", 0))
            dec = int(b.get("decline_count", 0))
            fig = go.Figure(go.Pie(
                labels=["Positive", "Negative"],
                values=[adv, dec],
                hole=0.56,
                marker_colors=[GREEN, RED],
                textinfo="label+percent",
            ))
            fig = apply_layout(fig, "Positive vs Negative Assets During Crisis")
            fig.update_layout(height=360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            if not by_group.empty:
                group_df = by_group.sort_values("pct_positive", ascending=True)
                fig_g = go.Figure(go.Bar(
                    y=group_df["group"],
                    x=group_df["pct_positive"],
                    orientation="h",
                    marker_color=group_df["pct_positive"],
                    marker_colorscale=[[0, RED], [0.5, GOLD], [1, GREEN]],
                    hovertemplate="%{y}: %{x:.1f}% positive<extra></extra>",
                ))
                fig_g = apply_layout(fig_g, "% Positive by Asset Group")
                fig_g.update_xaxes(title_text="% positive", range=[0, 100])
                fig_g.update_yaxes(title_text="")
                fig_g.update_layout(height=360, showlegend=False)
                st.plotly_chart(fig_g, use_container_width=True)

        if not by_group.empty:
            st.markdown("#### รายละเอียดตามกลุ่มสินทรัพย์")
            st.dataframe(by_group.sort_values("pct_positive", ascending=False), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════
# PAGE:  วิเคราะห์วิกฤต
# ═══════════════════════════════════════════════════════
elif page_key == "crisis":
    section("⚡", "วิเคราะห์ช่วงวิกฤต vs ปกติ",
            "เปรียบเทียบ daily return เฉลี่ยของทุกสินทรัพย์ แยกตาม regime — ช่วง crisis คือช่วงที่ NBER ประกาศ recession")

    summ = build_regime_summary(PANEL)

    if summ.empty:
        empty_state("ไม่มีข้อมูลสำหรับช่วงเวลานี้", "ปรับ date range หรือ asset selector ใน sidebar")
    else:
        val_col = "mean"

        crisis = summ[summ["regime"] == "crisis"].copy()
        normal = summ[summ["regime"] == "normal"].copy()

        if crisis.empty:
            empty_state("ไม่พบข้อมูล regime=crisis", "ลองเลือก preset crisis หรือขยายช่วงเวลาใน sidebar")
        else:
            top_n = st.slider("แสดงสูงสุดกี่สินทรัพย์", 1, len(crisis), min(15, len(crisis)))
            crisis_sorted = crisis.sort_values(val_col, key=abs, ascending=False).head(top_n)
            top_assets = crisis_sorted["asset"].tolist()

            normal_top = normal[normal["asset"].isin(top_assets)]

            # Merge crisis + normal
            merged = pd.merge(
                crisis_sorted[["asset", val_col]].rename(columns={val_col: "crisis_ret"}),
                normal_top[["asset", val_col]].rename(columns={val_col: "normal_ret"}),
                on="asset", how="left",
            )
            merged = merged.sort_values("crisis_ret", ascending=True)
            merged["crisis_pct"] = merged["crisis_ret"] * 100
            merged["normal_pct"] = merged["normal_ret"] * 100
            merged["type"] = merged["asset"].apply(classify_asset)

            # Grouped horizontal bar
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="🔴 Crisis", y=merged["asset"], x=merged["crisis_pct"],
                orientation="h", marker_color=RED,
                hovertemplate="%{y}: %{x:.4f}%<extra>Crisis</extra>",
            ))
            fig.add_trace(go.Bar(
                name="🟢 Normal", y=merged["asset"], x=merged["normal_pct"],
                orientation="h", marker_color=GREEN,
                hovertemplate="%{y}: %{x:.4f}%<extra>Normal</extra>",
            ))
            fig.update_layout(barmode="group", bargap=0.20, bargroupgap=0.08)
            fig = apply_layout(fig, "ผลตอบแทนเฉลี่ยรายวัน (%) — Crisis vs Normal")
            fig.update_xaxes(title_text="Daily Return (%)", zeroline=True, zerolinecolor=TXT3, zerolinewidth=1)
            fig.update_layout(height=max(380, top_n * 30))
            st.plotly_chart(fig, use_container_width=True)

            # Gold highlight
            st.markdown("---")
            st.markdown("#### 🏅 ทองคำ vs หุ้น ในช่วง Crisis")
            g_c = crisis[crisis["asset"] == "XAUUSD GOLD"]
            g_n = normal[normal["asset"] == "XAUUSD GOLD"]
            s_c = crisis[crisis["asset"] == "SPY (S&P 500)"]
            s_n = normal[normal["asset"] == "SPY (S&P 500)"]

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                v = f"{g_c.iloc[0][val_col]*100:.4f}%" if not g_c.empty else "—"
                st.metric("🥇 ทอง — Crisis", v)
            with c2:
                v = f"{g_n.iloc[0][val_col]*100:.4f}%" if not g_n.empty else "—"
                st.metric("🥇 ทอง — Normal", v)
            with c3:
                v = f"{s_c.iloc[0][val_col]*100:.4f}%" if not s_c.empty else "—"
                st.metric("📉 SPY — Crisis", v)
            with c4:
                v = f"{s_n.iloc[0][val_col]*100:.4f}%" if not s_n.empty else "—"
                st.metric("📈 SPY — Normal", v)

            if not g_c.empty and not s_c.empty:
                gold_v = g_c.iloc[0][val_col]
                spy_v = s_c.iloc[0][val_col]
                if gold_v > 0 and spy_v < 0:
                    st.success("✅ **ทองให้ผลตอบแทนบวกขณะที่หุ้นขาดทุนในช่วง Crisis** → สนับสนุนสมมติฐาน Safe Haven")
                elif gold_v > spy_v:
                    st.info("ℹ️ ทองให้ผลตอบแทนดีกว่าหุ้นในช่วง Crisis แม้ไม่สมบูรณ์แบบ")


# ═══════════════════════════════════════════════════════
# PAGE:  ความสัมพันธ์
# ═══════════════════════════════════════════════════════
elif page_key == "corr":
    section("🔗", "ความสัมพันธ์แบบเลื่อน (Rolling Correlation)",
            "ดูว่าทองเทียบ SPY / TLT / UUP / BTC เปลี่ยนอย่างไรตามเวลา — ค่าลบ = ลักษณะ Safe Haven")

    rc = load_csv("rolling_corr_multi.csv")

    if rc.empty:
        empty_state("ไม่มี rolling_corr_multi.csv", "รัน spark_transform + generate_dashboard_data")
    else:
        rc = filter_date(rc, active_start, active_end)
        rc = rc.dropna(subset=["date"])
        pair_asset_map = {
            "spy": "SPY (S&P 500)",
            "tlt": "TLT (20Y Bond)",
            "uup": "UUP (US Dollar)",
            "btc": "BTC (Bitcoin)",
        }
        corr_cols = []
        for key, asset_name in pair_asset_map.items():
            col = f"corr_gold_{key}_{rolling_window}d"
            if col in rc.columns and asset_name in selected_assets:
                corr_cols.append(col)

        if not corr_cols:
            empty_state("ไม่พบคู่ correlation ตาม asset/rolling window ที่เลือก", "เลือก SPY, TLT, UUP หรือ BTC ใน sidebar")
        else:
            nice = {c: c.replace("corr_gold_", "Gold vs ").replace(f"_{rolling_window}d", "").replace("_", " ").upper() for c in corr_cols}
            selected = corr_cols

            if selected:
                pair_colors = [GOLD, BLUE, GREEN, PURPLE, RED, CYAN, ORANGE, PINK]
                fig = go.Figure()
                for i, col in enumerate(selected):
                    valid = rc.dropna(subset=[col])
                    fig.add_trace(go.Scatter(
                        x=valid["date"], y=valid[col],
                        mode="lines", name=nice[col],
                        line=dict(width=1.8, color=pair_colors[i % len(pair_colors)]),
                        hovertemplate="%{x|%Y-%m-%d}: %{y:.3f}<extra>" + nice[col] + "</extra>",
                    ))
                fig.add_hline(y=0, line_dash="dash", line_color=TXT3, line_width=1,
                              annotation_text="ไม่สัมพันธ์", annotation_position="bottom right",
                              annotation_font_color=TXT3, annotation_font_size=11)
                fig = apply_layout(fig, "Rolling Correlation — ทองเทียบสินทรัพย์อื่น")
                fig.update_yaxes(title_text="Correlation", range=[-1, 1])
                fig.update_xaxes(title_text="")
                fig.update_layout(height=480)
                st.plotly_chart(fig, use_container_width=True)

            # Interpretation helper
            with st.expander("📖 วิธีอ่านกราฟ Rolling Correlation"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"""
                    **🟢 ค่าบวก (+)**\n
                    ทองเคลื่อนไหว **ไปทิศเดียวกัน** กับสินทรัพย์นั้น
                    → ไม่ช่วย diversify
                    """)
                with c2:
                    st.markdown(f"""
                    **🔴 ค่าลบ (−)**\n
                    ทองเคลื่อนไหว **สวนทาง**
                    → ลักษณะ **Safe Haven**
                    """)
                with c3:
                    st.markdown(f"""
                    **⚪ ค่าใกล้ 0**\n
                    **ไม่มีความสัมพันธ์**
                    → diversification ได้ดี
                    """)


# ═══════════════════════════════════════════════════════
# PAGE:  ความเสี่ยง & ความผันผวน
# ═══════════════════════════════════════════════════════
elif page_key == "risk":
    section("📈", "ความเสี่ยง & ความผันผวน",
            "Scatter plot แสดงความสัมพันธ์ระหว่าง rolling volatility กับ drawdown — แบ่ง 4 quadrant")

    risk = build_risk_summary(PANEL)

    if risk.empty:
        empty_state("ไม่มีข้อมูล risk สำหรับช่วงเวลานี้", "ปรับ date range หรือ asset selector ใน sidebar")
    else:
        risk["type"] = risk["asset"].apply(classify_asset)
        risk["vol_pct"] = risk["rolling_volatility"] * 100
        risk["dd_pct"] = risk["drawdown"] * 100

        # Quadrant thresholds
        vol_med = risk["vol_pct"].median()
        dd_med = risk["dd_pct"].median()

        fig = px.scatter(
            risk, x="vol_pct", y="dd_pct",
            color="type", text="asset",
            size=risk["vol_pct"].abs().clip(lower=0.05) * 20,
            hover_data={"vol_pct": ":.2f", "dd_pct": ":.2f", "type": True, "asset": True},
            color_discrete_map={
                "🥇 ทอง": GOLD, "📈 หุ้น/ETF": BLUE, "📜 พันธบัตร": GREEN,
                "₿ Crypto": PURPLE, "🛢️ สินค้าโภคภัณฑ์": ORANGE, "💵 ดอลลาร์": CYAN,
            },
        )
        fig.update_traces(textposition="top center", textfont_size=10,
                          marker=dict(line=dict(width=1, color="white")))

        # Quadrant lines
        fig.add_vline(x=vol_med, line_dash="dot", line_color=TXT3, line_width=1)
        fig.add_hline(y=dd_med, line_dash="dot", line_color=TXT3, line_width=1)

        # Quadrant labels
        fig.add_annotation(x=vol_med * 0.3, y=dd_med * 0.15, text="✅ นิ่ง & ปลอดภัย",
                           font=dict(size=11, color=GREEN), showarrow=False, opacity=0.7)
        fig.add_annotation(x=risk["vol_pct"].max() * 0.85, y=risk["dd_pct"].min() * 0.85,
                           text="⚠️ ผันผวน & เสี่ยงสูง",
                           font=dict(size=11, color=RED), showarrow=False, opacity=0.7)

        fig = apply_layout(fig, f"ความผันผวน ({rolling_window}d) vs Drawdown เฉลี่ย")
        fig.update_xaxes(title_text=f"Rolling Volatility {rolling_window}d (%)")
        fig.update_yaxes(title_text="Average Drawdown (%)")
        fig.update_layout(height=560, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📖 อ่านกราฟอย่างไร"):
            st.markdown("""
            - **แกน X (ขวา)** = ผันผวนสูง  |  **แกน Y (ล่าง)** = drawdown ลึก
            - สินทรัพย์ที่อยู่ **ซ้ายบน** → นิ่ง, ปลอดภัยที่สุด
            - สินทรัพย์ที่อยู่ **ขวาล่าง** → ผันผวนสูง, drawdown ลึก = เสี่ยง
            - **ทอง (GC=F)** ควรอยู่ในโซนซ้ายบนถ้าเป็น safe haven จริง
            - เส้นประ = ค่ามัธยฐานของกลุ่มตัวอย่าง
            """)


# ═══════════════════════════════════════════════════════
# PAGE:  Return Ranking (Mean Daily Return ช่วง Crisis)
# ═══════════════════════════════════════════════════════
elif page_key == "return_rank":
    section("📊", "Return Ranking (ช่วง Crisis)",
            "⚠️ นี่คือการจัดอันดับจาก Mean Daily Return เท่านั้น — ไม่ได้หมายความว่าเป็น Safe Haven ที่ดี ดู Safe Haven Leaderboard สำหรับ composite score")

    rank = build_return_ranking(PANEL)

    if rank.empty:
        empty_state("ไม่มี crisis return ในช่วงเวลานี้", "ปรับ period/date range หรือ asset selector ใน sidebar")
    else:
        rank = rank.sort_values("mean", ascending=False).reset_index(drop=True)
        rank["type"] = rank["asset"].apply(classify_asset)
        rank["mean_pct"] = rank["mean"] * 100

        st.warning("⚠️ **หมายเหตุ**: การจัดอันดับนี้ใช้ Mean Daily Return เท่านั้น — สินทรัพย์ที่ return สูงอาจมี drawdown สูงและ correlation กับหุ้นสูง จึงไม่ใช่ Safe Haven ที่แท้จริง")

        medals = ["🥇", "🥈", "🥉"]
        medal_classes = ["", "medal-silver", "medal-bronze"]
        for i, (_, row) in enumerate(rank.head(3).iterrows()):
            cls = medal_classes[i]
            st.markdown(
                f"""<div class="medal-row {cls}">
                    <div class="medal">{medals[i]}</div>
                    <div class="medal-info">
                        <div class="medal-name">{row['asset']}  <span style="color:{TXT3};font-weight:400;font-size:13px">{row['type']}</span></div>
                        <div class="medal-stat">Mean crisis return: <b>{row['mean_pct']:.4f}%</b>  ·  Std: {row['std']*100:.2f}%  ·   {int(row['count']):,} วัน</div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        fig = go.Figure()
        colors = [GREEN if v >= 0 else RED for v in rank["mean_pct"]]
        fig.add_trace(go.Bar(
            y=rank["asset"][::-1], x=rank["mean_pct"][::-1],
            orientation="h", marker_color=colors[::-1],
            hovertemplate="%{y}: %{x:.4f}%<extra></extra>",
        ))
        fig.add_vline(x=0, line_color=TXT3, line_width=1)
        fig = apply_layout(fig, "Mean Daily Return ช่วง Crisis (%) — ทุกสินทรัพย์")
        fig.update_xaxes(title_text="Mean Daily Return (%)")
        fig.update_layout(height=max(400, len(rank) * 22), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE:  Safe Haven Leaderboard (Composite Score)
# ═══════════════════════════════════════════════════════
elif page_key == "safe_haven":
    section("🛡️", "Safe Haven Leaderboard",
            "จัดอันดับด้วย composite score 6 มิติ: crisis return, outperform SPY, drawdown, volatility, correlation, hit rate")

    sh = build_safe_haven_ranking(PANEL_DATE, selected_assets)

    if sh.empty or "safe_haven_score" not in sh.columns:
        empty_state("ไม่มีข้อมูลพอคำนวณ Safe Haven Score ในช่วงเวลานี้", "เลือกช่วงเวลาที่มี crisis days และเลือก asset อย่างน้อย 1 ตัว")
    else:
        sh = sh.sort_values("safe_haven_score", ascending=False).reset_index(drop=True)
        sh["rank"] = range(1, len(sh) + 1)
        sh["type"] = sh["asset"].apply(classify_asset)

        gold_row = sh[sh["asset"] == "XAUUSD GOLD"]
        top_row = sh.iloc[0]
        gold_rank = int(gold_row.iloc[0]["rank"]) if not gold_row.empty else 0
        gold_score = float(gold_row.iloc[0]["safe_haven_score"]) if not gold_row.empty else np.nan

        kpi_html([
            ("อันดับ 1", top_row["asset"], f"score {top_row['safe_haven_score']:.3f}"),
            ("อันดับทอง", f"#{gold_rank} / {len(sh)}" if gold_rank else "—", f"score {gold_score:.3f}" if not np.isnan(gold_score) else "—"),
            ("มิติที่ใช้", "6", "return · drawdown · vol · corr · hit rate"),
            ("แยกจาก Return Ranking", "ใช่", "mean return ไม่เท่ากับ safe haven"),
        ])

        medals = ["🥇", "🥈", "🥉"]
        medal_classes = ["", "medal-silver", "medal-bronze"]
        for i, (_, row) in enumerate(sh.head(3).iterrows()):
            st.markdown(
                f"""<div class="medal-row {medal_classes[i]}">
                    <div class="medal">{medals[i]}</div>
                    <div class="medal-info">
                        <div class="medal-name">{row['asset']}  <span style="color:{TXT3};font-weight:400;font-size:13px">{row['type']}</span></div>
                        <div class="medal-stat">Safe Haven Score: <b>{row['safe_haven_score']:.3f}</b>  ·  Crisis return: {row.get('mean_crisis_return', 0)*100:.4f}%  ·  Corr SPY: {row.get('corr_with_spy', 0):.3f}</div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        fig = go.Figure(go.Bar(
            y=sh["asset"][::-1],
            x=sh["safe_haven_score"][::-1],
            orientation="h",
            marker_color=sh["safe_haven_score"][::-1],
            marker_colorscale=[[0, RED], [0.5, GOLD], [1, GREEN]],
            hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        ))
        fig.add_vline(x=0, line_color=TXT3, line_width=1)
        fig = apply_layout(fig, "Composite Safe Haven Score — สูงกว่าคือ defensive กว่า")
        fig.update_xaxes(title_text="Safe Haven Score")
        fig.update_layout(height=max(440, len(sh) * 23), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        show_cols = [
            c for c in [
                "rank", "asset", "type", "safe_haven_score", "mean_crisis_return",
                "outperform_spy_rate", "max_drawdown_crisis", "crisis_volatility",
                "corr_with_spy", "hit_rate", "crisis_days",
            ] if c in sh.columns
        ]
        st.markdown("#### ตารางคะแนนแบบละเอียด")
        st.dataframe(sh[show_cols], use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════
# PAGE:  Machine Learning
# ═══════════════════════════════════════════════════════
elif page_key == "ml":
    section("🤖", "Machine Learning",
            "เปรียบเทียบ 3 โมเดล classification — ทำนายว่าทองจะเป็น safe haven (positive return) ในวัน crisis หรือไม่")

    ml = load_csv("ml_results.csv")
    fi = load_csv("feature_importance.csv")
    prep = load_csv("ml_preprocessing_report.csv")
    cm_path = DASH / "confusion_matrix.csv"

    if ml.empty or (len(ml.columns) == 1 and "note" in ml.columns):
        empty_state("ยังไม่มีผล ML", "รัน src/modeling.py ให้สำเร็จก่อน")
    else:
        # ── Model comparison bar chart ──
        st.markdown("#### 📊 เปรียบเทียบประสิทธิภาพโมเดล")
        metrics = [c for c in ["accuracy", "f1", "roc_auc", "precision", "recall"] if c in ml.columns]
        if metrics:
            ml_melt = ml.melt(id_vars=["model"], value_vars=metrics, var_name="metric", value_name="score")
            fig = px.bar(
                ml_melt, x="metric", y="score", color="model",
                barmode="group", text="score",
                color_discrete_sequence=[GOLD, BLUE, GREEN],
            )
            fig.update_traces(texttemplate="%{text:.3f}", textposition="outside", textfont_size=11)
            fig = apply_layout(fig, "Model Performance Comparison")
            fig.update_yaxes(range=[0, 1.08], title_text="Score")
            fig.update_xaxes(title_text="")
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

        # KPI for best model
        if "f1" in ml.columns:
            best = ml.loc[ml["f1"].idxmax()]
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🏆 โมเดลที่ดีที่สุด", best["model"].replace("Classifier", ""))
            with c2:
                st.metric("Accuracy", f"{best['accuracy']:.1%}")
            with c3:
                st.metric("F1 Score", f"{best['f1']:.1%}")
            with c4:
                if "roc_auc" in best:
                    st.metric("ROC AUC", f"{best['roc_auc']:.1%}")

        st.markdown("---")

        if not prep.empty:
            st.markdown("#### 🧪 ML Preprocessing")
            st.caption("Pipeline: SimpleImputer → StandardScaler → Model, evaluated with TimeSeriesSplit and lag-1 features.")
            st.dataframe(prep, use_container_width=True, hide_index=True)
            st.markdown("---")

        # ── Feature importance ──
        if not fi.empty and "importance" in fi.columns:
            st.markdown("#### 🔬 Feature Importance (Random Forest)")
            fi_sorted = fi.sort_values("importance", ascending=True)
            fig_fi = go.Figure(go.Bar(
                y=fi_sorted["feature"], x=fi_sorted["importance"],
                orientation="h",
                marker=dict(
                    color=fi_sorted["importance"],
                    colorscale=[[0, "#FEF3C7"], [0.5, GOLD], [1, GOLD_D]],
                ),
                hovertemplate="%{y}: %{x:.4f}<extra></extra>",
            ))
            fig_fi = apply_layout(fig_fi, "")
            fig_fi.update_xaxes(title_text="Importance")
            fig_fi.update_layout(height=max(320, len(fi) * 28), showlegend=False)
            st.plotly_chart(fig_fi, use_container_width=True)

        # ── Confusion Matrix ──
        if cm_path.exists():
            st.markdown("---")
            st.markdown("#### 🎯 Confusion Matrix (GradientBoosting)")
            cm = pd.read_csv(cm_path, index_col=0)
            z = cm.values.astype(float)
            labels_x = ["ทำนาย: Not Safe Haven", "ทำนาย: Safe Haven"]
            labels_y = ["จริง: Not Safe Haven", "จริง: Safe Haven"]

            fig_cm = go.Figure(go.Heatmap(
                z=z, x=labels_x, y=labels_y,
                colorscale=[[0, "#FEF3C7"], [0.5, GOLD], [1, GOLD_D]],
                text=z.astype(int).astype(str), texttemplate="%{text}",
                textfont=dict(size=22, color="white"),
                hovertemplate="จริง: %{y}<br>ทำนาย: %{x}<br>จำนวน: %{z}<extra></extra>",
                showscale=False,
            ))
            fig_cm = apply_layout(fig_cm, "")
            fig_cm.update_layout(height=320, xaxis_title="Predicted", yaxis_title="Actual")
            st.plotly_chart(fig_cm, use_container_width=True)

            total = z.sum()
            correct = z[0][0] + z[1][1]
            st.caption(f"ทำนายถูก {int(correct)} / {int(total)} ({correct/total:.1%})")


# ═══════════════════════════════════════════════════════
# PAGE:  Bottom Line
# ═══════════════════════════════════════════════════════
elif page_key == "bottom":
    section("💎", "Bottom Line",
            "คำตอบสุดท้ายของโปรเจกต์: ทองคำเป็น safe haven แบบมีเงื่อนไข และเหตุผลมาจาก stress, dollar, yield และ market regime")

    bottom = load_csv("bottom_line.csv")
    if bottom.empty:
        empty_state("ไม่มี bottom_line.csv", "รัน spark_transform + generate_dashboard_data")
    else:
        cards = ""
        for _, row in bottom.iterrows():
            icon = row.get("icon", "•")
            title = row.get("title", row.get("category", "Insight"))
            body = row.get("body", "")
            status = row.get("status", "")
            cards += insight_card(icon, title, f"{body}<br/><span style='color:{TXT3}'>status: {status}</span>")
        st.markdown(f'<div class="insight-grid">{cards}</div>', unsafe_allow_html=True)

        st.markdown("#### ตารางสรุปสำหรับรายงาน")
        st.dataframe(bottom, use_container_width=True, hide_index=True)

        conclusion = bottom[bottom.get("category", pd.Series(dtype=str)).eq("conclusion")]
        if not conclusion.empty:
            st.success(conclusion.iloc[0]["body"])


# ═══════════════════════════════════════════════════════
# PAGE:  Transformation Summary
# ═══════════════════════════════════════════════════════
elif page_key == "transform":
    section("⚙️", "Transformation Summary",
            "สรุปชั้นประมวลผล Spark/Parquet, dashboard-ready datasets และ ML preprocessing")

    meta = load_csv("transformation_meta.csv")
    stats = load_csv("stats_per_asset.csv")
    crisis_stats = load_csv("stats_crisis_vs_normal.csv")
    prep = load_csv("ml_preprocessing_report.csv")

    if meta.empty:
        empty_state("ไม่มี transformation_meta.csv", "รัน spark_transform + generate_dashboard_data")
    else:
        meta_map = dict(zip(meta["metric"], meta["value"]))
        kpi_html([
            ("Raw files", f"{int(float(meta_map.get('total_raw_files', 0))):,}", "Yahoo + FRED"),
            ("Rows labeled", f"{int(float(meta_map.get('labeled_dataset_rows', 0))):,}", "labeled_dataset"),
            ("Compression", f"{float(meta_map.get('compression_ratio', 0)):.2f}x", "CSV → Parquet"),
            ("Spark output files", f"{int(float(meta_map.get('spark_output_files', 0))):,}", "dashboard-ready CSV"),
        ])

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### Transformation Metadata")
            st.dataframe(meta, use_container_width=True, hide_index=True)
        with c2:
            if not prep.empty:
                st.markdown("#### ML Preprocessing")
                st.dataframe(prep, use_container_width=True, hide_index=True)

        if not stats.empty and "mean_return" in stats.columns:
            st.markdown("---")
            top = stats.sort_values("mean_return", ascending=False).head(12)
            fig = px.bar(top, x="asset", y="mean_return", color="asset", color_discrete_sequence=CW)
            fig = apply_layout(fig, "Top Assets by Full-period Mean Return")
            fig.update_yaxes(title_text="Mean daily return")
            fig.update_xaxes(title_text="")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        if not crisis_stats.empty:
            st.markdown("#### Crisis vs Normal Statistics")
            st.dataframe(crisis_stats, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════
# PAGE:  สรุปเชิงลึก
# ═══════════════════════════════════════════════════════
elif page_key == "insights":
    section("💡", "สรุปเชิงลึก",
            "Key insights จากการวิเคราะห์ Safe Haven ด้วย Big Data Pipeline — สรุปสำหรับรายงานและนำเสนอ")

    # Load data for dynamic insights
    ranking = build_safe_haven_ranking(PANEL_DATE, selected_assets)
    summ = build_regime_summary(PANEL)
    risk = build_risk_summary(PANEL)
    ml = load_csv("ml_results.csv")
    fi = load_csv("feature_importance.csv")

    # ── Insight cards ──
    cards_left = ""
    cards_right = ""

    # 1. Gold Crisis Performance
    if not ranking.empty:
        score_col = "safe_haven_score" if "safe_haven_score" in ranking.columns else "mean"
        return_col = "mean_crisis_return" if "mean_crisis_return" in ranking.columns else "mean"
        rk = ranking.sort_values(score_col, ascending=False).reset_index(drop=True)
        gr = rk.index[rk["asset"] == "XAUUSD GOLD"]
        gold_mean = rk[rk["asset"] == "XAUUSD GOLD"][return_col].values
        if len(gr) and len(gold_mean):
            pos = gr[0] + 1
            total = len(rk)
            val = gold_mean[0] * 100
            n_pos = (rk[return_col] > 0).sum()
            cards_left += insight_card(
                "🥇", "ทองเด่นเมื่อวัดแบบ Safe Haven",
                f"XAUUSD GOLD ให้ mean daily return <b>+{val:.4f}%</b> ในช่วง crisis "
                f"และอยู่อันดับ composite score <b>#{pos}</b> จาก {total} สินทรัพย์ มี {n_pos} ตัวให้ผลบวก",
            )

    # 2. Gold vs Stocks in Crisis
    val_col = "daily_return" if not summ.empty and "daily_return" in summ.columns else "mean"
    if not summ.empty:
        c_gold = summ[(summ["regime"] == "crisis") & (summ["asset"] == "XAUUSD GOLD")]
        c_spy = summ[(summ["regime"] == "crisis") & (summ["asset"] == "SPY (S&P 500)")]
        if not c_gold.empty and not c_spy.empty:
            gv = c_gold.iloc[0][val_col] * 100
            sv = c_spy.iloc[0][val_col] * 100
            cards_left += insight_card(
                "⚡", "ทอง (+) vs หุ้น (−) ในวิกฤต",
                f"ทอง <b>+{gv:.4f}%</b> ต่อวัน  ←→  SPY <b>{sv:.4f}%</b> ต่อวัน ในช่วง crisis "
                f"→ ทองเคลื่อนไหวสวนทางตลาดหุ้นในช่วงตลาดตก",
            )

    # 3. Low Volatility
    if not risk.empty:
        gold_risk = risk[risk["asset"] == "XAUUSD GOLD"]
        spy_risk = risk[risk["asset"] == "SPY (S&P 500)"]
        btc_risk = risk[risk["asset"] == "BTC (Bitcoin)"]
        if not gold_risk.empty:
            gv = gold_risk.iloc[0]["rolling_volatility"] * 100
            sv = spy_risk.iloc[0]["rolling_volatility"] * 100 if not spy_risk.empty else 0
            bv = btc_risk.iloc[0]["rolling_volatility"] * 100 if not btc_risk.empty else 0
            cards_right += insight_card(
                "📉", "ความผันผวนต่ำกว่าหุ้นและ Crypto",
                f"Volatility {rolling_window}d: ทอง <b>{gv:.2f}%</b> vs SPY {sv:.2f}% vs BTC {bv:.2f}% "
                f"→ ทองมีความเสถียรสูงกว่าหุ้นและ crypto มาก",
            )

    # 4. ML Results
    if not ml.empty and "f1" in ml.columns:
        best = ml.loc[ml["f1"].idxmax()]
        cards_right += insight_card(
            "🤖", "ML ทำนาย Safe Haven ได้แม่นยำ",
            f"โมเดล <b>{best['model']}</b> ให้ F1 = <b>{best['f1']:.1%}</b>, "
            f"ROC AUC = <b>{best.get('roc_auc', 0):.1%}</b> → "
            f"สามารถใช้ features มหภาคทำนาย safe haven behavior ได้ดี",
        )

    # 5. Top Features
    if not fi.empty:
        top3 = fi.sort_values("importance", ascending=False).head(3)["feature"].tolist()
        cards_left += insight_card(
            "🔬", "ปัจจัยสำคัญที่กำหนด Safe Haven",
            f"Top features: <b>{', '.join(top3)}</b> "
            f"→ ผลตอบแทน SPY และ drawdown ในตลาดเป็นตัวกำหนดหลักว่าทองจะเป็น safe haven หรือไม่",
        )

    # 6. Methodology
    cards_right += insight_card(
        "📦", "Big Data Pipeline ครบวงจร",
        "ข้อมูล 30 ปี · 35+ สินทรัพย์ · Yahoo Finance + FRED · Spark processing · "
        "Parquet partitioning · Airflow orchestration · ML benchmark 3 โมเดล · Streamlit dashboard",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(cards_left, unsafe_allow_html=True)
    with col2:
        st.markdown(cards_right, unsafe_allow_html=True)

    # ── Final verdict ──
    st.markdown("---")
    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,{NAVY} 0%,{NAVY_L} 100%);
     border-radius:18px; padding:24px 28px; color:#F8FAFC;
     box-shadow:0 12px 40px rgba(15,23,42,0.25); animation:fadeUp .6s ease both">
  <div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;opacity:.7;margin-bottom:8px">
    Conclusion
  </div>
  <div style="font-size:20px;font-weight:700;line-height:1.4;margin-bottom:8px">
    ทองคำเป็น <span style="color:{GOLD_L}">Conditional Safe Haven</span>
  </div>
  <div style="font-size:14px;opacity:.88;line-height:1.65">
     ข้อมูลบ่งชี้ว่าทองคำ (XAUUSD GOLD) ให้ผลตอบแทนเป็นบวกในช่วง recession/crisis ขณะที่หุ้น (SPY) ติดลบ
     แต่ประสิทธิภาพขึ้นกับปัจจัยมหภาค เช่น VIX, USD, real yield
     — จึงเป็น <b>conditional safe haven</b> มากกว่า absolute safe haven
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── Raw markdown from pipeline ──
    report_path = REPORTS / "final_insight_summary.md"
    if report_path.exists():
        with st.expander("📄 ดู Insight Summary จาก pipeline (raw)"):
            st.markdown(report_path.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════
# PAGE:  เจาะลึกวิกฤต (Crisis Deep-Dive)
# ═══════════════════════════════════════════════════════
elif page_key == "deep":
    section("🔍", "เจาะลึกวิกฤตรายเหตุการณ์",
            "เลือกวิกฤตเฉพาะเหตุการณ์เพื่อดูว่าสินทรัพย์แต่ละตัวเสียหายหรือรอดแค่ไหน")

    events = load_csv("crisis_events.csv")
    prices = PANEL.copy()

    if events.empty or prices.empty:
        empty_state("ไม่มีข้อมูล crisis_events.csv หรือ analysis_panel.parquet", "รัน pipeline ให้ครบ")
    else:
        events["start_date"] = pd.to_datetime(events["start_date"])
        events["end_date"] = pd.to_datetime(events["end_date"])
        prices["date"] = pd.to_datetime(prices["date"], errors="coerce")

        event_names = events["name"].tolist()
        selected_event = st.selectbox("🗓️ เลือกเหตุการณ์วิกฤต", event_names)
        ev = events[events["name"] == selected_event].iloc[0]

        st.markdown(
            f'<div class="insight-card"><div class="ic-icon">📅</div>'
            f'<div class="ic-title">{ev["name"]}</div>'
            f'<div class="ic-body">{ev["description"]}<br/>'
            f'<b>{ev["start_date"].strftime("%Y-%m-%d")}</b> → <b>{ev["end_date"].strftime("%Y-%m-%d")}</b></div></div>',
            unsafe_allow_html=True,
        )

        # Filter price data to crisis window (with 30-day pre-buffer for normalization)
        pre_start = ev["start_date"] - pd.Timedelta(days=30)
        mask = (prices["date"] >= pre_start) & (prices["date"] <= ev["end_date"] + pd.Timedelta(days=10))
        crisis_prices = prices[mask].copy()

        all_assets = sorted(crisis_prices["asset"].dropna().unique().tolist())
        deep_sel = [a for a in selected_assets if a in all_assets]
        if not deep_sel:
            deep_sel = [a for a in DEFAULT_ASSETS if a in all_assets]
        st.caption("สินทรัพย์ในกราฟนี้มาจาก Global Asset Selector ใน sidebar")

        if deep_sel:
            sub = crisis_prices[crisis_prices["asset"].isin(deep_sel)].copy()
            sub = sub.sort_values(["asset", "date"])
            px_col = "adj_close" if "adj_close" in sub.columns else "close"
            sub["_px"] = pd.to_numeric(sub[px_col], errors="coerce")
            # Normalize to 100 at crisis start
            sub["_norm"] = sub.groupby("asset")["_px"].transform(lambda s: 100 * s / s.iloc[0])

            fig = px.line(sub, x="date", y="_norm", color="asset",
                          hover_data={"_norm": ":.2f"})
            fig = apply_layout(fig, f"Normalized Price (100 = start) — {selected_event}")
            fig.update_yaxes(title_text="Normalized Price")
            fig.update_xaxes(title_text="")
            # Add crisis window shading
            fig.add_vrect(x0=ev["start_date"], x1=ev["end_date"],
                          fillcolor="rgba(239,68,68,0.08)", line_width=0,
                          annotation_text="Crisis Window", annotation_position="top left",
                          annotation_font_color=RED, annotation_font_size=11)
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

            # Performance table: % change during exact crisis window
            st.markdown("---")
            st.markdown("#### 📊 ผลตอบแทนในช่วงวิกฤตนี้ (% เปลี่ยนแปลง)")
            perf_rows = []
            crisis_mask = (sub["date"] >= ev["start_date"]) & (sub["date"] <= ev["end_date"])
            crisis_sub = sub[crisis_mask]
            for asset_name in deep_sel:
                a_data = crisis_sub[crisis_sub["asset"] == asset_name].sort_values("date")
                if len(a_data) >= 2:
                    start_px = a_data["_px"].iloc[0]
                    end_px = a_data["_px"].iloc[-1]
                    min_px = a_data["_px"].min()
                    ret = (end_px / start_px - 1) * 100
                    max_dd = (min_px / start_px - 1) * 100
                    perf_rows.append({
                        "สินทรัพย์": asset_name,
                        "ประเภท": classify_asset(asset_name),
                        "ผลตอบแทน (%)": f"{ret:+.2f}%",
                        "Max Drawdown (%)": f"{max_dd:.2f}%",
                        "สถานะ": "✅ รอด" if ret >= 0 else "❌ เสียหาย",
                    })
            if perf_rows:
                perf_df = pd.DataFrame(perf_rows)
                st.dataframe(perf_df, use_container_width=True, hide_index=True)

                # Verdict
                gold_rows = [r for r in perf_rows if "GOLD" in r["สินทรัพย์"] or "ทอง" in r["ประเภท"]]
                spy_rows = [r for r in perf_rows if "SPY" in r["สินทรัพย์"]]
                if gold_rows and spy_rows:
                    gold_ret = float(gold_rows[0]["ผลตอบแทน (%)"].replace("%", "").replace("+", ""))
                    spy_ret = float(spy_rows[0]["ผลตอบแทน (%)"].replace("%", "").replace("+", ""))
                    if gold_ret > 0 and spy_ret < 0:
                        st.success(f"✅ ในช่วง **{selected_event}** ทองให้ผล **+{gold_ret:.2f}%** ขณะ SPY ขาดทุน **{spy_ret:.2f}%** → Safe Haven ชัดเจน!")
                    elif gold_ret > spy_ret:
                        st.info(f"ℹ️ ทองเสียหายน้อยกว่าหุ้น ({gold_ret:+.2f}% vs {spy_ret:+.2f}%) → มีคุณสมบัติ Safe Haven บางส่วน")
                    else:
                        st.warning(f"⚠️ ในช่วงนี้ทอง ({gold_ret:+.2f}%) ไม่ได้ช่วยปกป้องพอร์ตเมื่อเทียบกับ SPY ({spy_ret:+.2f}%)")


# ═══════════════════════════════════════════════════════
# PAGE:  จำลองพอร์ตลงทุน (Portfolio Simulator)
# ═══════════════════════════════════════════════════════
elif page_key == "portfolio":
    section("🎮", "จำลองพอร์ตลงทุน (Portfolio Simulator)",
            "ปรับสัดส่วนพอร์ตเพื่อดูว่าการผสมทองคำช่วยลด Drawdown ในวิกฤตได้จริงหรือไม่")

    prices = PANEL.copy()

    if prices.empty:
        empty_state("ไม่มี analysis_panel.parquet", "รัน pipeline ให้เสร็จก่อน")
    else:
        prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
        all_assets = [a for a in selected_assets if a in prices["asset"].dropna().unique().tolist()]

        st.markdown("#### ⚙️ ตั้งค่าพอร์ตลงทุน")
        st.caption("ลาก Slider เพื่อปรับสัดส่วน — ผลรวมจะถูกปรับให้ = 100% อัตโนมัติ")

        # Let user pick assets and allocations
        col1, col2 = st.columns([2, 1])
        with col1:
            port_assets = st.multiselect(
                "เลือกสินทรัพย์ในพอร์ต", all_assets,
                default=all_assets[: min(3, len(all_assets))],
                key="port_assets",
            )

        if len(port_assets) < 2:
            st.warning("เลือกสินทรัพย์อย่างน้อย 2 ตัวเพื่อจำลองพอร์ต")
        else:
            # Allocation sliders
            raw_weights = {}
            cols = st.columns(len(port_assets))
            for i, asset in enumerate(port_assets):
                with cols[i]:
                    w = st.slider(f"{asset}", 0, 100, 100 // len(port_assets), key=f"w_{asset}")
                    raw_weights[asset] = w

            total_w = sum(raw_weights.values())
            if total_w == 0:
                st.warning("สัดส่วนรวมเป็น 0 — ปรับ Slider ใหม่")
            else:
                weights = {k: v / total_w for k, v in raw_weights.items()}

                # Show allocation pie chart
                alloc_df = pd.DataFrame([
                    {"asset": k, "weight": v * 100} for k, v in weights.items()
                ])
                with col2:
                    st.markdown("**สัดส่วนพอร์ต:**")
                    for _, row in alloc_df.iterrows():
                        st.markdown(f"- {row['asset']}: **{row['weight']:.1f}%**")

                # Calculate portfolio returns
                px_col = "adj_close" if "adj_close" in prices.columns else "close"
                port_data = prices[prices["asset"].isin(port_assets)][["date", "asset", px_col]].copy()
                port_data[px_col] = pd.to_numeric(port_data[px_col], errors="coerce")
                port_data = port_data.sort_values(["asset", "date"])
                port_data["daily_ret"] = port_data.groupby("asset")[px_col].pct_change()

                # Pivot to wide format
                pivot = port_data.pivot_table(index="date", columns="asset", values="daily_ret")
                pivot = pivot.dropna()

                # Weighted portfolio return
                pivot["Portfolio"] = sum(pivot[a] * weights[a] for a in port_assets if a in pivot.columns)

                # Also compute 100% equity (SPY only) benchmark
                spy_col = [a for a in all_assets if "SPY" in a]
                if spy_col and spy_col[0] in pivot.columns:
                    pivot["100% หุ้น (SPY)"] = pivot[spy_col[0]]

                # Cumulative returns
                cum_cols = ["Portfolio"]
                if "100% หุ้น (SPY)" in pivot.columns:
                    cum_cols.append("100% หุ้น (SPY)")
                cum = (1 + pivot[cum_cols]).cumprod() - 1
                cum = cum.reset_index()
                cum_melt = cum.melt(id_vars="date", var_name="strategy", value_name="cumulative_return")

                # Plot cumulative return
                st.markdown("---")
                st.markdown("#### 📈 ผลตอบแทนสะสม")
                fig = px.line(cum_melt, x="date", y="cumulative_return", color="strategy",
                              color_discrete_map={"Portfolio": GOLD, "100% หุ้น (SPY)": BLUE})
                fig = apply_layout(fig, "Cumulative Return — My Portfolio vs 100% Stocks")
                fig.update_yaxes(title_text="Cumulative Return", tickformat=".0%")
                fig.update_layout(height=480)
                st.plotly_chart(fig, use_container_width=True)

                # KPI comparison
                st.markdown("#### 📊 สรุปสถิติพอร์ต")

                def calc_stats(series, name):
                    cum_ret = (1 + series).cumprod()
                    total_ret = cum_ret.iloc[-1] - 1
                    ann_ret = (1 + total_ret) ** (252 / len(series)) - 1 if len(series) > 0 else 0
                    ann_vol = series.std() * (252 ** 0.5)
                    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
                    max_dd = (cum_ret / cum_ret.cummax() - 1).min()
                    return {
                        "กลยุทธ์": name,
                        "ผลตอบแทนรวม": f"{total_ret:.1%}",
                        "ผลตอบแทนต่อปี": f"{ann_ret:.1%}",
                        "ความผันผวนต่อปี": f"{ann_vol:.1%}",
                        "Sharpe Ratio": f"{sharpe:.2f}",
                        "Max Drawdown": f"{max_dd:.1%}",
                    }

                stats_rows = [calc_stats(pivot["Portfolio"], "🎯 My Portfolio")]
                if "100% หุ้น (SPY)" in pivot.columns:
                    stats_rows.append(calc_stats(pivot["100% หุ้น (SPY)"], "📉 100% หุ้น (SPY)"))

                stats_df = pd.DataFrame(stats_rows)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

                # Drawdown chart
                st.markdown("---")
                st.markdown("#### 📉 Drawdown Comparison")
                dd_data = pd.DataFrame(index=pivot.index)
                for col_name in cum_cols:
                    cum_ret = (1 + pivot[col_name]).cumprod()
                    dd_data[col_name] = (cum_ret / cum_ret.cummax() - 1) * 100

                dd_data = dd_data.reset_index()
                dd_melt = dd_data.melt(id_vars="date", var_name="strategy", value_name="drawdown")
                fig_dd = px.area(dd_melt, x="date", y="drawdown", color="strategy",
                                 color_discrete_map={"Portfolio": GOLD, "100% หุ้น (SPY)": BLUE})
                fig_dd = apply_layout(fig_dd, "Drawdown (%) — ยิ่งตื้นยิ่งดี")
                fig_dd.update_yaxes(title_text="Drawdown (%)")
                fig_dd.update_layout(height=380)
                st.plotly_chart(fig_dd, use_container_width=True)

                # Insight
                port_dd = (1 + pivot["Portfolio"]).cumprod()
                port_max_dd = (port_dd / port_dd.cummax() - 1).min() * 100
                if "100% หุ้น (SPY)" in pivot.columns:
                    spy_dd = (1 + pivot["100% หุ้น (SPY)"]).cumprod()
                    spy_max_dd = (spy_dd / spy_dd.cummax() - 1).min() * 100
                    diff = spy_max_dd - port_max_dd
                    if port_max_dd > spy_max_dd:
                        st.success(
                            f"✅ พอร์ตที่ผสมทองคำมี Max Drawdown **{port_max_dd:.1f}%** "
                            f"เทียบกับ 100% หุ้น **{spy_max_dd:.1f}%** "
                            f"→ ลดการสูญเสียสูงสุดได้ **{diff:.1f}%**"
                        )
                    else:
                        st.info(
                            f"ℹ️ พอร์ตนี้มี Max Drawdown **{port_max_dd:.1f}%** "
                            f"(100% หุ้น: **{spy_max_dd:.1f}%**) — ลองปรับสัดส่วนทองคำเพิ่มดู"
                        )


# ═══════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    f"""<div style="text-align:center;color:{TXT3};font-size:12px;padding:8px 0 16px">
    Gold Safe Haven Analytics · Big Data Project · Streamlit + Plotly + Yahoo Finance + FRED<br/>
    ปรับแต่งได้ที่ <code>app/dashboard.py</code>
    </div>""",
    unsafe_allow_html=True,
)
