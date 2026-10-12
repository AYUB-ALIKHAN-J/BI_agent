"""Agent tools: plain Python functions over SQL, called by the LLM via LangGraph.

The LLM never calculates or writes SQL; it only selects and calls these tools
with appropriate arguments.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from langchain_core.tools import tool

from olist_bi.warehouse import kpis
from olist_bi.warehouse.connection import query_df


def get_warehouse_path() -> str:
    """Get warehouse path from environment or default location."""
    import os
    return os.environ.get("OLIST_WAREHOUSE_PATH", "warehouse/olist.duckdb")


@tool
def get_headline_kpis(
    start: Annotated[str, "Start month in YYYY-MM format, e.g. 2017-01"],
    end: Annotated[str, "End month in YYYY-MM format, e.g. 2018-12"],
) -> dict:
    """Get headline KPIs (revenue, orders, AOV, cancellation rate, on-time rate, avg review)."""
    wh = get_warehouse_path()
    return kpis.headline_kpis(wh, start, end)


@tool
def get_monthly_trend(
    start: Annotated[str, "Start month in YYYY-MM format, e.g. 2017-01"],
    end: Annotated[str, "End month in YYYY-MM format, e.g. 2018-12"],
) -> str:
    """Get monthly revenue and order trends as a formatted table."""
    wh = get_warehouse_path()
    df = kpis.monthly_trend(wh, start, end)
    return df.to_string(index=False)


@tool
def get_revenue_by_category(
    start: Annotated[str, "Start month in YYYY-MM format, e.g. 2017-01"],
    end: Annotated[str, "End month in YYYY-MM format, e.g. 2018-12"],
    top: Annotated[int, "Number of top categories to return, default 10"] = 10,
) -> str:
    """Get revenue breakdown by product category."""
    wh = get_warehouse_path()
    df = kpis.revenue_by_category(wh, start, end, top)
    return df.to_string(index=False)


@tool
def get_revenue_by_state(
    start: Annotated[str, "Start month in YYYY-MM format, e.g. 2017-01"],
    end: Annotated[str, "End month in YYYY-MM format, e.g. 2018-12"],
) -> str:
    """Get revenue breakdown by customer state."""
    wh = get_warehouse_path()
    df = kpis.revenue_by_state(wh, start, end)
    return df.to_string(index=False)


@tool
def get_available_months() -> list[str]:
    """Get list of all available months in the warehouse."""
    wh = get_warehouse_path()
    return kpis.available_months(wh)


@tool
def get_forecast(
    category: Annotated[str, "Product category, e.g. 'health_beauty' or 'all' for all categories"],
    metric: Annotated[str, "Metric to forecast: 'revenue' or 'orders'"],
    horizon: Annotated[int, "Number of months to forecast, default 3"] = 3,
) -> str:
    """Get demand forecast for a category and metric."""
    from olist_bi.analytics import forecast as fc_module
    from olist_bi.warehouse import drilldown
    
    wh = get_warehouse_path()
    cats = drilldown.categories_by_revenue(wh)
    
    cat = None if category.lower() == "all" else category
    
    try:
        series = fc_module.monthly_series(wh, cat, metric)
        result = fc_module.forecast_series(series, horizon=horizon, holdout=3)
        
        lines = [
            f"Best model: {result.best_model}",
            f"Backtest MAPE: {result.mape:.1%}",
            f"Naive MAPE: {result.naive_mape:.1%}",
            "",
            "Forecast:",
        ]
        for month, value in result.forecast.items():
            lines.append(f"  {month}: {value:,.0f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error forecasting: {e}"


@tool
def get_rfm_segments(
    start: Annotated[str, "Start month in YYYY-MM format, e.g. 2017-01"],
    end: Annotated[str, "End month in YYYY-MM format, e.g. 2018-12"],
    n_clusters: Annotated[int, "Number of clusters (3-7), default 5"] = 5,
) -> str:
    """Get RFM customer segmentation results."""
    from olist_bi.analytics import rfm as rfm_module
    
    wh = get_warehouse_path()
    summary = rfm_module.top_segments(wh, start, end, n_clusters)
    return summary.to_string()


@tool
def get_basket_rules(
    start: Annotated[str, "Start month in YYYY-MM format, e.g. 2017-01"],
    end: Annotated[str, "End month in YYYY-MM format, e.g. 2018-12"],
    min_support: Annotated[float, "Minimum support threshold, default 0.01"] = 0.01,
    min_lift: Annotated[float, "Minimum lift threshold, default 1.5"] = 1.5,
) -> str:
    """Get market basket association rules."""
    from olist_bi.analytics import basket as basket_module
    
    wh = get_warehouse_path()
    try:
        rules = basket_module.basket_analysis(wh, start, end, min_support, min_lift)
        if rules.empty:
            return "No association rules found with the given parameters."
        return rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(20).to_string()
    except Exception as e:
        return f"Error analyzing baskets: {e}"
