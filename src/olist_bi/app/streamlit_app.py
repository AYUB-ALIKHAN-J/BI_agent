"""Streamlit GUI — Olist Decision Intelligence Platform."""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import streamlit as st

from olist_bi.app.tabs import basket, chat, delivery, drilldown, forecast, overview, segments
from olist_bi.config import get_settings
from olist_bi.logging_setup import setup_logging
from olist_bi.warehouse import kpis
from olist_bi.warehouse.connection import WarehouseNotFound
from olist_bi.warehouse.drilldown import reliable_months

st.set_page_config(
    page_title="Olist Decision Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Main background */
    .stApp { background-color: #0f1117; color: #e0e0e0; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #12151f 100%);
        border-right: 1px solid #2a2d3e;
    }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #1e2130;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 16px 20px;
        transition: transform 0.2s;
    }
    [data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: #4f8ef7; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
    [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 1.6rem !important; font-weight: 700; }
    [data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

    /* Tabs */
    [data-testid="stTabs"] button {
        color: #8b949e !important;
        font-weight: 500;
        font-size: 0.88rem;
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #4f8ef7 !important;
        border-bottom: 2px solid #4f8ef7 !important;
        background: #1e2130 !important;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    .stDataFrame thead th { background: #1e2130 !important; color: #8b949e !important; font-size: 0.78rem; text-transform: uppercase; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #4f8ef7, #7c5cbf);
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 20px;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* Expander */
    [data-testid="stExpander"] {
        background: #1e2130;
        border: 1px solid #2a2d3e;
        border-radius: 10px;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #e6edf3;
        margin: 20px 0 10px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #2a2d3e;
    }

    /* Status badge */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-green { background: #1a3a2a; color: #3fb950; border: 1px solid #3fb950; }
    .badge-blue  { background: #1a2a3a; color: #4f8ef7; border: 1px solid #4f8ef7; }
    .badge-red   { background: #3a1a1a; color: #f85149; border: 1px solid #f85149; }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: #1e2130 !important;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        margin-bottom: 8px;
    }

    /* Plotly charts */
    .js-plotly-plot { border-radius: 10px; }

    /* Divider */
    hr { border-color: #2a2d3e !important; }

    /* Info / warning boxes */
    [data-testid="stAlert"] { border-radius: 10px; }

    /* Selectbox / slider */
    [data-testid="stSelectbox"] > div, [data-testid="stSlider"] > div { color: #c9d1d9; }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = get_settings()
setup_logging(settings.log_level)
WH = settings.warehouse_path


@st.cache_data(show_spinner=False)
def _months(wh: str, mtime: float) -> tuple[list[str], list[str]]:
    return kpis.available_months(wh), reliable_months(wh)


def main() -> None:
    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 📊 Olist BI")
        st.markdown("---")

        try:
            all_months, good = _months(str(WH), WH.stat().st_mtime)
        except (WarehouseNotFound, FileNotFoundError) as exc:
            st.error(str(exc) if isinstance(exc, WarehouseNotFound)
                     else f"Warehouse not found. Run `make etl` first.")
            st.stop()

        default = (good[0], good[-1]) if good else (all_months[0], all_months[-1])

        st.markdown("**📅 Period**")
        start, end = st.select_slider("Period", options=all_months, value=default, label_visibility="collapsed")
        st.markdown(f"<small style='color:#8b949e'>From **{start}** to **{end}**</small>", unsafe_allow_html=True)

        if len(good) < len(all_months):
            st.info(f"Excluding {len(all_months) - len(good)} sparse months from tails.")

        st.markdown("---")
        st.markdown("**🗄️ Warehouse**")
        st.markdown(f"<small style='color:#8b949e'>`{WH.name}`</small>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            "<small style='color:#555'>Olist Decision Intelligence<br>BI Lab Project</small>",
            unsafe_allow_html=True,
        )

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(
        "<h1 style='font-size:1.8rem; font-weight:700; color:#e6edf3; margin-bottom:4px;'>"
        "📊 E-Commerce Decision Intelligence</h1>"
        "<p style='color:#8b949e; margin-top:0; font-size:0.9rem;'>"
        "Olist Brazilian E-Commerce · Real-time analytics & AI analyst</p>",
        unsafe_allow_html=True,
    )

    # ── Tabs ─────────────────────────────────────────────────────────────────
    t_over, t_cx, t_dd, t_fc, t_seg, t_basket, t_chat = st.tabs([
        "🏠 Overview",
        "🚚 Delivery & CX",
        "🔍 Drill-down",
        "📈 Forecast",
        "👥 Segments",
        "🛒 Basket",
        "🤖 Ask the Analyst",
    ])

    with t_over:
        overview.render(WH, start, end)
    with t_cx:
        delivery.render(WH, start, end)
    with t_dd:
        drilldown.render(WH, start, end)
    with t_fc:
        forecast.render(WH, start, end)
    with t_seg:
        segments.render(WH, start, end)
    with t_basket:
        basket.render(WH, start, end)
    with t_chat:
        chat.render(WH, start, end)


main()
