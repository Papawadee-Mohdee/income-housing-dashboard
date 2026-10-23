"""Plotly figure builders for Tab 2 — House Price Index."""
from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go

from app.figures.theme import (
    CHOROPLETH_HOUSING, CHOROPLETH_HOUSING_LIGHT,
    get_base_layout, region_color, region_dash, TOKENS,
    HEATMAP_DIVERGING, HEATMAP_DIVERGING_DARK,
)

GEOJSON_PATH = Path(__file__).resolve().parents[2] / "static" / "regions.geojson"
_geojson_cache = None


def _get_geojson():
    global _geojson_cache
    if _geojson_cache is None:
        _geojson_cache = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    return _geojson_cache


# All 5 region IDs
ALL_REGION_IDS = {1, 2, 3, 4, 5}


def fig_choropleth(data: list[dict], theme: str = "dark",
                   title: str = "ดัชนีราคาบ้านรายภาค") -> dict:
    """Choropleth map of HPI by region, with missing regions shown as grey."""
    gj = _get_geojson()
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    colorscale = CHOROPLETH_HOUSING if theme == "dark" else CHOROPLETH_HOUSING_LIGHT

    present_ids = {r["region_id"] for r in data}
    missing_ids = ALL_REGION_IDS - present_ids

    fig = go.Figure()

    # Main choropleth for regions with data
    if data:
        fig.add_trace(go.Choropleth(
            geojson=gj,
            locations=[r["region_id"] for r in data],
            z=[r["value"] for r in data],
            featureidkey="properties.region_id",
            colorscale=colorscale,
            text=[r["short_th"] for r in data],
            hovertemplate="%{text}<br>ดัชนี: %{z:.1f}<extra></extra>",
            marker_line_color=t["border"],
            marker_line_width=1,
            colorbar=dict(
                title=dict(text="ดัชนี", font=dict(color=t["text_muted"])),
                tickfont=dict(color=t["text_muted"]),
            ),
        ))

    # Grey overlay for missing regions
    if missing_ids:
        fig.add_trace(go.Choropleth(
            geojson=gj,
            locations=list(missing_ids),
            z=[0] * len(missing_ids),
            featureidkey="properties.region_id",
            colorscale=[[0, "#888888"], [1, "#888888"]],
            showscale=False,
            hovertemplate="ไม่มีข้อมูล<extra></extra>",
            marker_line_color=t["border"],
            marker_line_width=1,
        ))

    layout.update({
        "title": {"text": title, "font": {"color": t["text"]}},
        "geo": {"fitbounds": "locations", "visible": False, "bgcolor": "rgba(0,0,0,0)"},
        "height": 420,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_trend(data: list[dict], theme: str = "dark", is_monthly: bool = False,
              title: str = "แนวโน้มดัชนีราคาบ้าน") -> dict:
    """Line chart of HPI over time."""
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    fig = go.Figure()

    by_region: dict[str, list] = {}
    for r in data:
        by_region.setdefault(r["short_th"], []).append(r)

    for name, rows in by_region.items():
        is_national = rows[0].get("is_national", False)
        if is_monthly:
            x = [f"{r['year_be']}-{r['month_no']:02d}" for r in rows]
        else:
            x = [r["year_be"] for r in rows]

        fig.add_trace(go.Scatter(
            x=x,
            y=[r["index_value"] for r in rows],
            mode="lines" if is_monthly else "lines+markers",
            name=name,
            line=dict(
                color=region_color(name, theme),
                dash=region_dash(is_national),
                width=2.5 if is_national else 1.5,
            ),
            marker=dict(size=5),
            hovertemplate=f"{name}<br>ดัชนี: %{{y:.1f}}<extra></extra>",
        ))

    shapes = []
    annotations = []

    # Reference line at Jan 2566 (data source change)
    if is_monthly and "2566-01" in x:
        shapes.append(dict(
            type="line",
            x0="2566-01", x1="2566-01",
            y0=0, y1=1,
            yref="paper",
            line=dict(dash="dot", color=t["text_muted"], width=1.5),
        ))
        annotations.append(dict(
            x="2566-01", y=1,
            yref="paper",
            text="เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ",
            showarrow=False,
            xanchor="right",
            font=dict(color=t["text_muted"], size=10),
        ))

    if is_monthly:
        annotations.append({
            "text": "* ดัชนีผ่านการเฉลี่ยเคลื่อนที่ 3 เดือน",
            "xref": "paper", "yref": "paper", "x": 0, "y": -0.15,
            "showarrow": False, "font": {"color": t["text_muted"], "size": 11},
        })

    x_title = "เดือน" if is_monthly else "ปี (พ.ศ.)"
    layout.update({
        "title": {"text": title},
        "xaxis": {**layout["xaxis"], "title": x_title},
        "yaxis": {**layout["yaxis"], "title": "ดัชนี (2554=100)"},
        "height": 400,
        "hovermode": "x unified",
        "shapes": shapes,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_heatmap(data: list[dict], theme: str = "dark",
                title: str = "อัตราเปลี่ยนแปลงรายปี (YoY %)") -> dict:
    """Heatmap: region × year showing YoY change."""
    layout = get_base_layout(theme)
    t = TOKENS[theme]

    regions = list(dict.fromkeys(r["short_th"] for r in data))
    years = sorted(set(r["year_be"] for r in data))
    lookup = {(r["short_th"], r["year_be"]): r["yoy_pct"] for r in data}

    z, text = [], []
    for region in regions:
        row, text_row = [], []
        for year in years:
            v = lookup.get((region, year))
            row.append(v)
            text_row.append(f"{v:.1f}%" if v is not None else "")
        z.append(row)
        text.append(text_row)

    colorscale = HEATMAP_DIVERGING_DARK if theme == "dark" else HEATMAP_DIVERGING

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[str(y) for y in years],
        y=regions,
        text=text,
        texttemplate="%{text}",
        colorscale=colorscale,
        zmid=0,
        hovertemplate="%{y} ปี %{x}<br>YoY: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            title=dict(text="YoY %", font=dict(color=t["text_muted"])),
            tickfont=dict(color=t["text_muted"]),
        ),
    ))
    layout.update({
        "title": {"text": title},
        "xaxis": {**layout["xaxis"], "title": "ปี (พ.ศ.)"},
        "yaxis": {**layout["yaxis"], "title": "", "autorange": "reversed"},
        "height": 350,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()
