"""Plotly figure builders for Tab 1 — Household Income (v2 design)."""
from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go

from app.figures.theme import (
    CHOROPLETH_INCOME_SCALE, FONT_FAMILY, HEATMAP_GAP_SCALE,
    INCOME_SOURCE_COLORS, TOKENS, get_base_layout, region_color, region_dash,
)

GEOJSON_PATH = Path(__file__).resolve().parents[2] / "static" / "regions.geojson"
_geojson_cache = None


def _get_geojson():
    global _geojson_cache
    if _geojson_cache is None:
        _geojson_cache = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    return _geojson_cache


# Center coordinates for region labels on the map
REGION_LABEL_COORDS = {
    1: {"lon": 100.40, "lat": 13.60},  # BMR shifted bottom-left
    2: {"lon": 100.20, "lat": 15.20},  # Central
    3: {"lon": 99.40, "lat": 17.71},   # North
    4: {"lon": 103.17, "lat": 16.29},  # Northeast
    5: {"lon": 99.48, "lat": 8.32},    # South
}


def fig_choropleth(
    data: list[dict],
    selected_region: int | None = None,
    theme: str = "dark",
    metric_label: str = "รายได้",
    unit: str = "บาท/เดือน",
    year: int = 2566,
    area_name: str = "รวมทุกเขต",
) -> dict:
    gj = _get_geojson()
    t = TOKENS[theme]
    map_style = "carto-darkmatter" if theme == "dark" else "carto-positron"

    # Split into general regions and selected region for border highlight
    locs = [r["region_id"] for r in data]
    vals = [r["value"] for r in data]
    texts = [r["short_th"] for r in data]
    custom = [f"{r['short_th']}<br>{r['value']:,.0f} {unit}<br>{area_name} · ปี {year}" for r in data]

    # Main Choroplethmap trace
    choro_trace = go.Choroplethmap(
        geojson=gj,
        locations=locs,
        z=vals,
        featureidkey="properties.region_id",
        colorscale=CHOROPLETH_INCOME_SCALE,
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
            tickformat=",.0f",
            title=dict(text=""),
        ),
    )

    traces = [choro_trace]

    # Highlight border for selected region if any
    if selected_region and selected_region in locs:
        sel_row = next(r for r in data if r["region_id"] == selected_region)
        highlight_trace = go.Choroplethmap(
            geojson=gj,
            locations=[selected_region],
            z=[sel_row["value"]],
            featureidkey="properties.region_id",
            colorscale=CHOROPLETH_INCOME_SCALE,
            showscale=False,
            marker_line_color=t["text"],
            marker_line_width=3,
            marker_opacity=0.9,
            hoverinfo="skip",
        )
        traces.append(highlight_trace)

    # Label text overlay on map
    lbl_lons, lbl_lats, lbl_texts = [], [], []
    for r in data:
        coords = REGION_LABEL_COORDS.get(r["region_id"])
        if coords:
            lbl_lons.append(coords["lon"])
            lbl_lats.append(coords["lat"])
            lbl_texts.append(f"<b>{r['short_th']}</b><br>{r['value']:,.0f}")

    label_trace = go.Scattermap(
        mode="text",
        lon=lbl_lons,
        lat=lbl_lats,
        text=lbl_texts,
        textfont=dict(family=FONT_FAMILY, size=12, color=t["text"]),
        hoverinfo="skip",
    )
    traces.append(label_trace)

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
    metric: str = "income",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    fig = go.Figure()

    by_region: dict[str, list] = {}
    for r in data:
        by_region.setdefault(r["short_th"], []).append(r)

    y_key = "monthly_income" if metric == "income" else "income_index"
    hover_fmt = "%{y:,.0f} บาท" if metric == "income" else "%{y:.1f}"

    for name, rows in by_region.items():
        rid = rows[0]["region_id"]
        is_national = rows[0].get("is_national", False)
        is_selected = (selected_region is not None and selected_region == rid) or (selected_region is None and is_national)
        has_any_selected = selected_region is not None and selected_region > 0

        # Colors & styling
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

        xs = [str(r["year_be"]) for r in rows]
        ys = [r[y_key] for r in rows]

        # Area gradient or subtle fill for selected region
        fill_mode = "tozeroy" if (is_selected and not is_national) else "none"

        trace = go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name=name,
            line=dict(
                color=color,
                dash=region_dash(is_national),
                width=line_width,
            ),
            fill=fill_mode,
            fillcolor=f"rgba(47, 107, 255, 0.08)" if theme == "light" else "rgba(91, 140, 255, 0.08)",
            opacity=opacity,
            marker=dict(size=5, line=dict(color=t["surface"], width=2)),
            hovertemplate=f"{name}: {hover_fmt}<extra></extra>",
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

    layout.update({
        "margin": {"l": 48, "r": 60, "t": 8, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
            "showspikes": True,
            "spikethickness": 1,
            "spikecolor": t["grid"],
            "spikemode": "across",
        },
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": ""},
        },
        "height": 320,
        "hovermode": "x unified",
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

    # Fixed ordering: BMR, Central, North, Northeast, South, and National at bottom
    region_order = ["กทม.+ปริมณฑล", "กลาง", "เหนือ", "อีสาน", "ใต้", "ทั่วประเทศ"]
    y_categories = list(reversed(region_order))  # Plotly bottom-to-top

    years = sorted(list(set(r["year_be"] for r in data)))
    x_categories = [str(y) for y in years]

    lookup = {(r["short_th"], str(r["year_be"])): r["gap_pct"] for r in data}

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
        colorscale=HEATMAP_GAP_SCALE,
        zmin=0,
        zmax=65,
        xgap=4,
        ygap=4,
        hovertemplate="%{y} ปี %{x}<br>ช่องว่าง: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            thickness=10,
            outlinewidth=0,
            tickfont=dict(family=FONT_FAMILY, color=t["text_muted"], size=10),
            title=dict(text=""),
        ),
    ))

    # Highlight box for selected region row and selected year column
    shapes = []
    # Separator line above national (between index 0 "ทั่วประเทศ" and index 1 "ใต้")
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

    # Highlight selected region row if any
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


def fig_treemap(data: dict, theme: str = "dark") -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    source_colors = INCOME_SOURCE_COLORS[theme]

    labels = []
    parents = []
    values = []
    texts = []
    marker_colors = []
    customdata = []

    if data.get("mode") == "single":
        # Single region: show full width with 5 detailed sources
        region_name = data.get("region", "")
        tot = data.get("monthly_income", 1)
        for leaf in data.get("leaves", []):
            labels.append(leaf["name"])
            parents.append("")
            values.append(leaf["amount"])
            texts.append(f"{leaf['name']}<br>{leaf['amount']:,.0f} บาท ({leaf['share']:.1f}%)")
            customdata.append([leaf["share"], leaf["name"]])
            # Map color
            color = source_colors.get(leaf["name"], source_colors["อื่น ๆ"])
            marker_colors.append(color)

        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            text=texts,
            customdata=customdata,
            textinfo="text",
            hoverinfo="text",
            marker=dict(colors=marker_colors),
            textfont=dict(family=FONT_FAMILY, size=13),
            root_color="rgba(0,0,0,0)",
            pathbar=dict(visible=False),
        ))
    else:
        # Multi-region: 5 regions as parent boxes, 4 groups per region
        for reg in data.get("regions", []):
            reg_name = reg["region"]
            tot = reg["monthly_income"]
            groups = reg.get("groups", [])
            children_sum = sum(g["amount"] for g in groups)
            parent_val = children_sum if children_sum > 0 else tot

            # Parent node
            reg_id = f"REG_{reg['region_id']}"
            labels.append(reg_id)
            parents.append("")
            values.append(parent_val)
            texts.append(f"<b>{reg_name} · {tot:,.0f} บาท</b>")
            customdata.append([100.0, reg_name])
            marker_colors.append(t["surface_2"])

            for g in reg.get("groups", []):
                child_id = f"{reg_id}_{g['name']}"
                labels.append(child_id)
                parents.append(reg_id)
                values.append(g["amount"])
                texts.append(f"{g['name']}<br>{g['share']:.1f}%")
                customdata.append([g["share"], g["name"]])
                marker_colors.append(source_colors.get(g["name"], source_colors["อื่น ๆ"]))

        fig = go.Figure(go.Treemap(
            branchvalues="total",
            labels=labels,
            parents=parents,
            values=values,
            text=texts,
            customdata=customdata,
            textinfo="text",
            hoverinfo="text",
            marker=dict(
                colors=marker_colors,
                pad=dict(t=28, l=3, r=3, b=3),
            ),
            textfont=dict(family=FONT_FAMILY, size=12),
            root_color="rgba(0,0,0,0)",
            pathbar=dict(visible=False),
        ))

    layout.update({
        "height": 440,
        "margin": {"l": 4, "r": 4, "t": 4, "b": 4},
        "uniformtext": dict(minsize=11, mode="hide"),
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()
