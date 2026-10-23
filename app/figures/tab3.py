"""Plotly figure builders for Tab 3 — Income vs Housing Price."""
from __future__ import annotations

import plotly.graph_objects as go

from app.figures.theme import (
    get_base_layout, region_color, region_dash, TOKENS, SEMANTIC_COLORS,
)
from app.metrics import cagr_pct


def fig_price_to_income_trend(data: list[dict], y0: int, y1: int,
                               theme: str = "dark",
                               title: str = "ดัชนีราคาบ้าน ÷ รายได้") -> dict:
    """Line chart of price-to-income index over time, with reference at 100."""
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    fig = go.Figure()

    # Shade above/below 100
    fig.add_hrect(y0=100, y1=200, fillcolor=SEMANTIC_COLORS[theme]["negative"],
                  opacity=0.05, line_width=0)
    fig.add_hrect(y0=50, y1=100, fillcolor=SEMANTIC_COLORS[theme]["positive"],
                  opacity=0.05, line_width=0)
    fig.add_hline(y=100, line_dash="dash", line_color=t["text_muted"],
                  annotation_text="ฐาน = 100", annotation_position="top left",
                  annotation_font_color=t["text_muted"])

    # Group by region
    by_region: dict[str, list] = {}
    for r in data:
        by_region.setdefault(r["short_th"], []).append(r)

    for name, rows in by_region.items():
        xs = [r["year_be"] for r in rows]
        ys = [r["price_to_income_index"] for r in rows]

        is_national = rows[0].get("is_national", False)
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers", name=name,
            line=dict(color=region_color(name, theme), dash=region_dash(is_national), width=2.5 if is_national else 2),
            marker=dict(size=7),
            hovertemplate=f"{name} ปี %{{x}}<br>ดัชนี: %{{y:.1f}}<extra></extra>",
        ))

    # Add annotations
    annotations = [
        {"text": "ซื้อยากขึ้น ▲", "x": 1.02, "y": 110, "xref": "paper", "yref": "y",
         "showarrow": False, "font": {"color": SEMANTIC_COLORS[theme]["negative"], "size": 11}},
        {"text": "ง่ายขึ้น ▼", "x": 1.02, "y": 90, "xref": "paper", "yref": "y",
         "showarrow": False, "font": {"color": SEMANTIC_COLORS[theme]["positive"], "size": 11}},
    ]

    layout.update({
        "title": {"text": title},
        "xaxis": {**layout["xaxis"], "title": "ปี (พ.ศ.)", "dtick": 2},
        "yaxis": {**layout["yaxis"], "title": "ดัชนีราคา ÷ รายได้"},
        "height": 420,
        "hovermode": "x unified",
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_paired_bars(data: list[dict], region_name: str | None,
                    theme: str = "dark",
                    title: str = "ดัชนีรายได้ vs ดัชนีราคาบ้าน") -> dict:
    """Paired bar chart: income index (blue) vs HPI index (orange) by year."""
    layout = get_base_layout(theme)
    colors = SEMANTIC_COLORS[theme]

    # Filter to the selected region or national
    if region_name:
        filtered = [r for r in data if r["short_th"] == region_name]
    else:
        filtered = [r for r in data if r.get("is_national")]

    if not filtered:
        filtered = data  # fallback

    years = [r["year_be"] for r in filtered]
    income_idx = [r["income_index"] for r in filtered]
    hpi_idx = [r["hpi_index"] for r in filtered]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=income_idx, name="รายได้",
        marker_color=colors["income"],
        hovertemplate="ปี %{x}<br>ดัชนีรายได้: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=years, y=hpi_idx, name="ราคาบ้าน",
        marker_color=colors["housing"],
        hovertemplate="ปี %{x}<br>ดัชนีราคาบ้าน: %{y:.1f}<extra></extra>",
    ))

    scope = region_name if region_name else "ทั่วประเทศ"
    layout.update({
        "title": {"text": f"{title} ({scope})"},
        "xaxis": {**layout["xaxis"], "title": "ปี (พ.ศ.)", "dtick": 2},
        "yaxis": {**layout["yaxis"], "title": "ดัชนี (2554=100)"},
        "barmode": "group",
        "height": 380,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_cagr_comparison(income_cagr: float, hpi_cagr: float,
                        theme: str = "dark",
                        title: str = "CAGR ตลอดช่วง") -> dict:
    """Two-bar chart comparing CAGR of income vs housing."""
    layout = get_base_layout(theme)
    colors = SEMANTIC_COLORS[theme]
    t = TOKENS[theme]

    gap = round(hpi_cagr - income_cagr, 2)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["รายได้", "ราคาบ้าน"], y=[income_cagr, hpi_cagr],
        marker_color=[colors["income"], colors["housing"]],
        text=[f"{income_cagr:.2f}%", f"{hpi_cagr:.2f}%"],
        textposition="outside",
        textfont=dict(color=t["text"]),
        hovertemplate="%{x}: %{y:.2f}%/ปี<extra></extra>",
    ))

    annotations = [{
        "text": f"ช่องว่าง: {gap:.2f} จุด",
        "xref": "paper", "yref": "paper", "x": 0.5, "y": 1.05,
        "showarrow": False,
        "font": {"color": colors["negative"] if gap > 0 else colors["positive"], "size": 14},
    }]

    layout.update({
        "title": {"text": title},
        "yaxis": {**layout["yaxis"], "title": "%/ปี"},
        "height": 350,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_cagr_by_region(income_data: list[dict], hpi_data: list[dict],
                       theme: str = "dark",
                       title: str = "CAGR แยกตามภาค") -> dict:
    """Paired bars of CAGR by region."""
    layout = get_base_layout(theme)
    colors = SEMANTIC_COLORS[theme]

    regions = [r["short_th"] for r in income_data if not r.get("is_national")]
    income_cagrs = []
    hpi_cagrs = []
    for r in income_data:
        if r.get("is_national"):
            continue
        c = cagr_pct(r["v0"], r["v1"], r["years"])
        income_cagrs.append(c if c is not None else 0)
    for r in hpi_data:
        if r.get("is_national"):
            continue
        c = cagr_pct(r["v0"], r["v1"], r["years"])
        hpi_cagrs.append(c if c is not None else 0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=regions, y=income_cagrs, name="รายได้",
        marker_color=colors["income"],
        text=[f"{v:.2f}%" for v in income_cagrs],
        textposition="outside",
        hovertemplate="%{x}: รายได้ %{y:.2f}%/ปี<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=regions, y=hpi_cagrs, name="ราคาบ้าน",
        marker_color=colors["housing"],
        text=[f"{v:.2f}%" for v in hpi_cagrs],
        textposition="outside",
        hovertemplate="%{x}: ราคาบ้าน %{y:.2f}%/ปี<extra></extra>",
    ))

    layout.update({
        "title": {"text": title},
        "yaxis": {**layout["yaxis"], "title": "%/ปี"},
        "barmode": "group",
        "height": 400,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()
