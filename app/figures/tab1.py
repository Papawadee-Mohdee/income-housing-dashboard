"""Plotly figure builders for Tab 1 — Household Income."""
from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go

from app.figures.theme import (
    CHOROPLETH_INCOME, CHOROPLETH_INCOME_LIGHT,
    get_base_layout, region_color, region_dash, TOKENS, HEATMAP_DIVERGING_DARK, HEATMAP_DIVERGING,
)

GEOJSON_PATH = Path(__file__).resolve().parents[2] / "static" / "regions.geojson"
_geojson_cache = None


def _get_geojson():
    global _geojson_cache
    if _geojson_cache is None:
        _geojson_cache = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    return _geojson_cache


def fig_choropleth(data: list[dict], theme: str = "dark", title: str = "รายได้เฉลี่ยรายภาค") -> dict:
    """Choropleth map of income by region."""
    gj = _get_geojson()
    layout = get_base_layout(theme)
    colorscale = CHOROPLETH_INCOME if theme == "dark" else CHOROPLETH_INCOME_LIGHT

    fig = go.Figure(go.Choropleth(
        geojson=gj,
        locations=[r["region_id"] for r in data],
        z=[r["value"] for r in data],
        featureidkey="properties.region_id",
        colorscale=colorscale,
        text=[r["short_th"] for r in data],
        hovertemplate="%{text}<br>%{z:,.0f} บาท/เดือน<extra></extra>",
        marker_line_color=TOKENS[theme]["border"],
        marker_line_width=1,
        colorbar=dict(
            title=dict(text="บาท/เดือน", font=dict(color=TOKENS[theme]["text_muted"])),
            tickfont=dict(color=TOKENS[theme]["text_muted"]),
        ),
    ))
    layout.update({
        "title": {"text": title, "font": {"color": TOKENS[theme]["text"]}},
        "geo": {
            "fitbounds": "locations",
            "visible": False,
            "bgcolor": "rgba(0,0,0,0)",
        },
        "height": 420,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_treemap(data: list[dict], theme: str = "dark", title: str = "แหล่งที่มาของรายได้") -> dict:
    """Treemap of income sources."""
    t = TOKENS[theme]
    layout = get_base_layout(theme)

    if not data:
        fig = go.Figure()
        fig.update_layout(**layout, title=title, height=400)
        return fig.to_plotly_json()

    labels, parents, values, texts = [], [], [], []
    # Check if multi-region or single-region
    regions = list(set(r["region"] for r in data))
    if len(regions) > 1:
        # Multi-region: outer = region, inner = source
        for region in regions:
            labels.append(region)
            parents.append("")
            region_rows = [r for r in data if r["region"] == region]
            values.append(sum(r["amount_baht"] for r in region_rows))
            texts.append("")
            for r in region_rows:
                labels.append(f"{r['source_name_th']} ({region})")
                parents.append(region)
                values.append(r["amount_baht"])
                texts.append(f"{r['share_pct']:.1f}%")
    else:
        # Single region: outer = group, inner = source
        groups = list(set(r["group_th"] for r in data))
        for group in groups:
            labels.append(group)
            parents.append("")
            group_rows = [r for r in data if r["group_th"] == group]
            values.append(sum(r["amount_baht"] for r in group_rows))
            texts.append("")
            for r in group_rows:
                labels.append(r["source_name_th"])
                parents.append(group)
                values.append(r["amount_baht"])
                texts.append(f"{r['share_pct']:.1f}%")

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        text=texts,
        textinfo="label+text",
        hovertemplate="%{label}<br>%{value:,.0f} บาท<br>%{text}<extra></extra>",
        marker=dict(
            colors=values,
            colorscale=[[0, t["blue"]], [1, TOKENS[theme]["orange"]]],
        ),
        textfont=dict(color=t["text"], family=t["font_family"]),
    ))
    layout.update({"title": {"text": title}, "height": 400, "margin": {"l": 10, "r": 10, "t": 50, "b": 10}})
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_trend(data: list[dict], theme: str = "dark", metric: str = "income",
              title: str = "แนวโน้มรายได้ตามปี") -> dict:
    """Line chart of income over time, one line per region."""
    layout = get_base_layout(theme)
    fig = go.Figure()

    # Group by region
    by_region: dict[str, list] = {}
    for r in data:
        by_region.setdefault(r["short_th"], []).append(r)

    y_key = "monthly_income" if metric == "income" else "income_index"
    y_title = "บาท/เดือน" if metric == "income" else "ดัชนี (2554=100)"
    hover_fmt = "%{y:,.0f} บาท" if metric == "income" else "%{y:.1f}"

    for name, rows in by_region.items():
        is_national = rows[0].get("is_national", False)
        fig.add_trace(go.Scatter(
            x=[r["year_be"] for r in rows],
            y=[r[y_key] for r in rows],
            mode="lines+markers",
            name=name,
            line=dict(
                color=region_color(name, theme),
                dash=region_dash(is_national),
                width=3 if is_national else 2,
            ),
            marker=dict(size=7),
            hovertemplate=f"{name} ปี %{{x}}<br>{hover_fmt}<extra></extra>",
        ))

    layout.update({
        "title": {"text": title},
        "xaxis": {**layout["xaxis"], "title": "ปี (พ.ศ.)", "dtick": 2},
        "yaxis": {**layout["yaxis"], "title": y_title},
        "height": 400,
        "hovermode": "x unified",
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_heatmap(data: list[dict], theme: str = "dark",
                title: str = "ช่องว่างเมือง-ชนบท (%)") -> dict:
    """Heatmap: region × year showing urban-rural gap."""
    layout = get_base_layout(theme)
    t = TOKENS[theme]

    # Pivot data
    regions = list(dict.fromkeys(r["short_th"] for r in data))
    years = sorted(set(r["year_be"] for r in data))
    lookup = {(r["short_th"], r["year_be"]): r["gap_pct"] for r in data}

    z = []
    text = []
    for region in regions:
        row = []
        text_row = []
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
        hovertemplate="%{y} ปี %{x}<br>ช่องว่าง: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            title=dict(text="%", font=dict(color=t["text_muted"])),
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
