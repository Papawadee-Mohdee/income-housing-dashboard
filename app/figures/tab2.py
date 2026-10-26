"""Plotly figure builders for Tab 2 — House Price Index (v2 design)."""
from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go

from app.figures.theme import (
    CHOROPLETH_HOUSING_SCALE, FONT_FAMILY, TOKENS,
    get_base_layout, get_heatmap_yoy_scale, region_color, region_dash,
)

GEOJSON_PATH = Path(__file__).resolve().parents[2] / "static" / "regions.geojson"
_geojson_cache = None


def _get_geojson():
    global _geojson_cache
    if _geojson_cache is None:
        _geojson_cache = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    return _geojson_cache


REGION_LABEL_COORDS = {
    1: {"lon": 100.40, "lat": 13.60},
    2: {"lon": 100.20, "lat": 15.20},
    3: {"lon": 99.40, "lat": 17.71},
    4: {"lon": 103.17, "lat": 16.29},
    5: {"lon": 99.48, "lat": 8.32},
}

ALL_REGION_IDS = {1, 2, 3, 4, 5}


def fig_choropleth(
    data: list[dict],
    selected_region: int | None = None,
    theme: str = "dark",
    metric_label: str = "ดัชนี",
    unit: str = "(2554=100)",
    year: int = 2566,
    pt_name: str = "รวมทุกประเภทที่อยู่อาศัย",
) -> dict:
    gj = _get_geojson()
    t = TOKENS[theme]
    map_style = "carto-darkmatter" if theme == "dark" else "carto-positron"

    present_ids = {r["region_id"] for r in data}
    missing_ids = ALL_REGION_IDS - present_ids

    locs = [r["region_id"] for r in data]
    vals = [r["value"] for r in data]
    custom = [f"{r['short_th']}<br>{metric_label} {r['value']:,.1f} {unit}<br>{pt_name} · ปี {year}" for r in data]

    traces = []

    # Missing regions gray layer
    if missing_ids:
        missing_names = {3: "เหนือ", 4: "อีสาน"}
        m_custom = [f"{missing_names.get(mid, '')}<br>ไม่มีข้อมูล<br>{pt_name}" for mid in missing_ids]
        missing_color = "#232D3F" if theme == "dark" else "#E5E7EB"
        traces.append(go.Choroplethmap(
            geojson=gj,
            locations=list(missing_ids),
            z=[0] * len(missing_ids),
            featureidkey="properties.region_id",
            colorscale=[[0, missing_color], [1, missing_color]],
            showscale=False,
            customdata=m_custom,
            hovertemplate="%{customdata}<extra></extra>",
            marker_line_color=t["border"],
            marker_line_width=0.5,
            marker_opacity=0.7,
        ))

    # Main Choroplethmap
    if data:
        traces.append(go.Choroplethmap(
            geojson=gj,
            locations=locs,
            z=vals,
            featureidkey="properties.region_id",
            colorscale=CHOROPLETH_HOUSING_SCALE,
            customdata=custom,
            hovertemplate="%{customdata}<extra></extra>",
            marker_line_color=t["border"],
            marker_line_width=0.5,
            marker_opacity=0.85,
            colorbar=dict(
                orientation="h",
                x=0.03,
                y=0.03,
                xanchor="left",
                yanchor="bottom",
                thickness=10,
                outlinewidth=0,
                tickfont=dict(family=FONT_FAMILY, color=t["text_muted"], size=11),
                tickformat=",.1f" if "ดัชนี" in metric_label else "+,.1f",
                title=dict(text=""),
            ),
        ))

    # Selected region border highlight
    if selected_region and selected_region in locs:
        sel_row = next(r for r in data if r["region_id"] == selected_region)
        traces.append(go.Choroplethmap(
            geojson=gj,
            locations=[selected_region],
            z=[sel_row["value"]],
            featureidkey="properties.region_id",
            colorscale=CHOROPLETH_HOUSING_SCALE,
            showscale=False,
            marker_line_color=t["text"],
            marker_line_width=3,
            marker_opacity=0.9,
            hoverinfo="skip",
        ))

    # Label text overlay on map
    lbl_lons, lbl_lats, lbl_texts = [], [], []
    for r in data:
        coords = REGION_LABEL_COORDS.get(r["region_id"])
        if coords:
            lbl_lons.append(coords["lon"])
            lbl_lats.append(coords["lat"])
            lbl_texts.append(f"<b>{r['short_th']}</b><br>{r['value']:,.1f}")

    traces.append(go.Scattermap(
        mode="text",
        lon=lbl_lons,
        lat=lbl_lats,
        text=lbl_texts,
        textfont=dict(family=FONT_FAMILY, size=12, color=t["text"]),
        hoverinfo="skip",
    ))

    fig = go.Figure(traces)
    layout = get_base_layout(theme)
    layout.update({
        "height": 560,
        "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
        "map": {
            "style": map_style,
            "center": {"lat": 13.0, "lon": 101.2},
            "zoom": 4.6,
        },
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_trend(
    data: list[dict],
    selected_region: int | None = None,
    theme: str = "dark",
    is_monthly: bool = False,
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    fig = go.Figure()

    by_region: dict[str, list] = {}
    for r in data:
        by_region.setdefault(r["short_th"], []).append(r)

    shapes = []
    annotations = []

    for name, rows in by_region.items():
        rid = rows[0]["region_id"]
        is_national = rows[0].get("is_national", False)
        is_selected = (selected_region is not None and selected_region == rid) or (selected_region is None and is_national)
        has_any_selected = selected_region is not None and selected_region > 0

        color = region_color(name, theme)
        if has_any_selected and not is_selected:
            opacity = 0.3
            line_width = 1.5
        elif is_selected:
            opacity = 1.0
            line_width = 3.5
        else:
            opacity = 1.0
            line_width = 2.5

        if is_monthly:
            xs = [f"{r['year_be']}-{r['month_no']:02d}" for r in rows]
        else:
            xs = [str(r["year_be"]) for r in rows]
        ys = [r["index_value"] for r in rows]

        fill_mode = "tozeroy" if (is_selected and not is_national) else "none"

        trace = go.Scatter(
            x=xs,
            y=ys,
            mode="lines" if is_monthly else "lines+markers",
            name=name,
            line=dict(
                color=color,
                dash=region_dash(is_national),
                width=line_width,
            ),
            fill=fill_mode,
            fillcolor=f"rgba(255, 122, 26, 0.08)" if theme == "light" else "rgba(255, 138, 61, 0.08)",
            opacity=opacity,
            marker=dict(size=5, line=dict(color=t["surface"], width=2)),
            hovertemplate=f"{name}: %{{y:.1f}}<extra></extra>",
        )
        fig.add_trace(trace)

        # End of line text label
        if rows:
            fig.add_trace(go.Scatter(
                x=[xs[-1]],
                y=[ys[-1]],
                mode="text",
                text=[f"  {name}"],
                textposition="middle right",
                textfont=dict(family=FONT_FAMILY, size=11, color=color),
                hoverinfo="skip",
                showlegend=False,
                opacity=opacity,
            ))

    xaxis_config = {
        **layout["xaxis"],
        "type": "category",
        "showspikes": True,
        "spikethickness": 1,
        "spikecolor": t["grid"],
        "spikemode": "across",
        "tickangle": 0,
    }
    if is_monthly:
        years = sorted(list(set(r["year_be"] for r in data)))
        xaxis_config.update({
            "tickmode": "array",
            "tickvals": [f"{y}-01" for y in years],
            "ticktext": [str(y) for y in years],
        })

    layout.update({
        "margin": {"l": 48, "r": 60, "t": 8, "b": 32},
        "xaxis": xaxis_config,
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": ""},
            "tickformat": ",.0f",
        },
        "height": 320,
        "hovermode": "x unified",
        "shapes": shapes,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_heatmap(
    data: list[dict],
    selected_region: int | None = None,
    selected_year: int = 2566,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]

    region_order = ["กทม.+ปริมณฑล", "กลาง", "เหนือ", "อีสาน", "ใต้", "ทั่วประเทศ"]
    y_categories = list(reversed(region_order))

    years = sorted(list(set(r["year_be"] for r in data)))
    x_categories = [str(y) for y in years]

    lookup = {(r["short_th"], str(r["year_be"])): r["yoy_pct"] for r in data}

    z = []
    text = []
    for reg in y_categories:
        row_z = []
        row_t = []
        for yr in x_categories:
            val = lookup.get((reg, yr))
            row_z.append(val)
            row_t.append(f"{val:.0f}%" if val is not None else "")
        z.append(row_z)
        text.append(row_t)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_categories,
        y=y_categories,
        text=text,
        texttemplate="%{text}",
        textfont=dict(family=FONT_FAMILY, size=11.5),
        colorscale=get_heatmap_yoy_scale(theme),
        zmid=0,
        xgap=4,
        ygap=4,
        hovertemplate="%{y} ปี %{x}<br>YoY: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            thickness=10,
            outlinewidth=0,
            tickfont=dict(family=FONT_FAMILY, color=t["text_muted"], size=10),
            title=dict(text=""),
        ),
    ))

    shapes = []
    # Separator line above national
    shapes.append(dict(
        type="line",
        x0=-0.5,
        x1=len(x_categories) - 0.5,
        y0=0.5,
        y1=0.5,
        line=dict(color=t["text_muted"], width=1, dash="dot"),
    ))

    # Highlight selected year column
    year_str = str(selected_year)
    if year_str in x_categories:
        col_idx = x_categories.index(year_str)
        shapes.append(dict(
            type="rect",
            x0=col_idx - 0.48,
            x1=col_idx + 0.48,
            y0=-0.48,
            y1=len(y_categories) - 0.52,
            line=dict(color=t["text"], width=2),
            fillcolor="rgba(0,0,0,0)",
        ))

    # Highlight selected region row
    region_names = {0: "ทั่วประเทศ", 1: "กทม.+ปริมณฑล", 2: "กลาง", 3: "เหนือ", 4: "อีสาน", 5: "ใต้"}
    if selected_region is not None and selected_region in region_names:
        reg_name = region_names[selected_region]
        if reg_name in y_categories:
            row_idx = y_categories.index(reg_name)
            shapes.append(dict(
                type="rect",
                x0=-0.48,
                x1=len(x_categories) - 0.52,
                y0=row_idx - 0.48,
                y1=row_idx + 0.48,
                line=dict(color=t["text"], width=2),
                fillcolor="rgba(0,0,0,0)",
            ))

    layout.update({
        "margin": {"l": 48, "r": 48, "t": 8, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
        },
        "yaxis": {
            **layout["yaxis"],
            "type": "category",
            "showgrid": True,
        },
        "height": 280,
        "shapes": shapes,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()
