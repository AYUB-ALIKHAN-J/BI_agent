"""Streamlit GUI. Iteration 2-4: Overview, Delivery & CX, Drill-down, Forecast, Segments, Basket, Chat (LLM agent)."""

from __future__ import annotations

import streamlit as st

from olist_bi.app.tabs import basket, chat, delivery, drilldown, forecast, overview, segments
from olist_bi.config import get_settings
from olist_bi.warehouse import kpis
from olist_bi.warehouse.connection import WarehouseNotFound
from olist_bi.warehouse.drilldown import reliable_months

st.set_page_config(page_title="Olist Decision Intelligence", page_icon="📊", layout="wide")
settings = get_settings()
WH = settings.warehouse_path


@st.cache_data(show_spinner=False)
def _months(wh: str, mtime: float) -> tuple[list[str], list[str]]:
    return kpis.available_months(wh), reliable_months(wh)


def main() -> None:
    st.title("📊 E-Commerce Decision Intelligence")
    try:
        all_months, good = _months(str(WH), WH.stat().st_mtime)
    except (WarehouseNotFound, FileNotFoundError) as exc:
        st.error(
            str(exc)
            if isinstance(exc, WarehouseNotFound)
            else f"Warehouse not found at {WH}. Run `olist-bi etl` (or `make etl`) first."
        )
        st.stop()

    default = (good[0], good[-1]) if good else (all_months[0], all_months[-1])
    with st.sidebar:
        st.header("Filters")
        start, end = st.select_slider("Period", options=all_months, value=default)
        if len(good) < len(all_months):
            st.caption(
                f"Default window {default[0]} to {default[1]} excludes {len(all_months) - len(good)} "
                "sparse months (dataset launch / cut-off) that distort trends."
            )
        st.caption(f"Warehouse: `{WH.name}`")

    t_over, t_cx, t_dd, t_fc, t_seg, t_basket, t_chat = st.tabs(
        ["Overview", "Delivery & CX", "Drill-down", "Forecast", "Segments", "Basket", "Ask the analyst"]
    )
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
