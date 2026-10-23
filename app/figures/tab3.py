"""Plotly figure builders for Tab 3 — Income vs Housing Price (v2 design)."""
from __future__ import annotations

import plotly.graph_objects as go

from app.figures.theme import (
    FONT_FAMILY, SEMANTIC_COLORS, TOKENS,
    get_base_layout, region_color, region_dash,
)
from app.metrics import cagr_pct


def fig_price_to_income_hero(
    data: list[dict],
    y0: int,
    y1: int,
    selected_region: int | None = None,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    colors = SEMANTIC_COLORS[theme]
    fig = go.Figure()

    by_region: dict[str, list] = {}
    for r in data:
        by_region.setdefault(r["short_th"], []).append(r)

    all_ys = [r["price_to_income_index"] for r in data if r.get("price_to_income_index") is not None]
    min_val = min(all_ys) if all_ys else 95.0
    max_val = max(all_ys) if all_ys else 150.0

    y_min = min(95.0, min_val - 5.0)
    y_max = max_val + 10.0

    shapes = [
        # Orange shaded area above 100 (Harder to buy)
        dict(
            type="rect",
            xref="paper",
            x0=0,
            x1=1,
            y0=100,
            y1=y_max,
            fillcolor=colors["housing"],
            opacity=0.07,
            line_width=0,
            layer="below",
        ),
        # Blue shaded area below 100 (Easier to buy)
        dict(
            type="rect",
            xref="paper",
            x0=0,
            x1=1,
            y0=y_min,
            y1=100,
            fillcolor=colors["income"],
            opacity=0.07,
            line_width=0,
            layer="below",
        ),
        # Reference line at y=100
        dict(
            type="line",
            xref="paper",
            x0=0,
            x1=1,
            y0=100,
            y1=100,
            line=dict(color=t["text_muted"], width=1.5, dash="dash"),
        ),
    ]

    annotations = [
        # 100 reference text
        dict(
            xref="paper",
            x=0.01,
            y=100,
            text="100 = ราคาบ้านกับรายได้โตเท่ากัน",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(family=FONT_FAMILY, size=11, color=t["text_muted"]),
        ),
        # Buying harder
        dict(
            xref="paper",
            x=0.01,
            y=y_max - 2,
            text="ซื้อยากขึ้น",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_FAMILY, size=12, color=colors["housing"], weight=600),
        ),
        # Buying easier
        dict(
            xref="paper",
            x=0.01,
            y=y_min + 2,
            text="ซื้อง่ายขึ้น",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_FAMILY, size=12, color=colors["income"], weight=600),
        ),
    ]

    for name, rows in by_region.items():
        rid = rows[0]["region_id"]
        is_national = rows[0].get("is_national", False)
        is_selected = (selected_region is not None and selected_region == rid) or (selected_region is None and is_national)
        has_any_selected = selected_region is not None and selected_region > 0

        # Colors & width
        if is_selected:
            color = t["text"] if is_national else region_color(name, theme)
            width = 4.0
            opacity = 1.0
        else:
            color = region_color(name, theme)
            width = 1.5
            opacity = 0.35

        xs = [str(r["year_be"]) for r in rows]
        ys = [r["price_to_income_index"] for r in rows]

        # Customdata for rich hover
        customdata = []
        for r in rows:
            pti = r["price_to_income_index"]
            diff = pti - 100.0
            sign = "+" if diff > 0 else ""
            customdata.append([
                name,
                pti,
                r["income_index"],
                r["hpi_index"],
                f"{sign}{diff:.1f}%",
            ])

        hovertemplate = (
            "<b>ปี %{x} · %{customdata[0]}</b><br>"
            "อัตราส่วน: %{customdata[1]:.1f}<br>"
            "ดัชนีรายได้: %{customdata[2]:.1f}<br>"
            "ดัชนีราคาบ้าน: %{customdata[3]:.1f}<br>"
            "เทียบต้นช่วง: %{customdata[4]}"
            "<extra></extra>"
        )

        trace = go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=width, dash=region_dash(is_national)),
            marker=dict(size=5, line=dict(color=t["surface"], width=2)),
            customdata=customdata,
            hovertemplate=hovertemplate,
            opacity=opacity,
        )
        fig.add_trace(trace)

        # End point value and status label
        if rows:
            last_val = ys[-1]
            status_text = "ซื้อยากขึ้น" if last_val > 100 else "ซื้อง่ายขึ้น"
            label_text = f"  <b>{last_val:.1f}</b> ({status_text})" if is_selected else f"  {last_val:.1f}"
            fig.add_trace(go.Scatter(
                x=[xs[-1]],
                y=[last_val],
                mode="text",
                text=[label_text],
                textposition="middle right",
                textfont=dict(family=FONT_FAMILY, size=11, color=color),
                hoverinfo="skip",
                showlegend=False,
                opacity=opacity,
            ))

    layout.update({
        "margin": {"l": 48, "r": 120, "t": 8, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
        },
        "yaxis": {
            **layout["yaxis"],
            "range": [y_min, y_max],
            "title": {"text": f"ดัชนีราคาบ้าน ÷ ดัชนีรายได้ (ปี {y0} = 100)"},
        },
        "height": 420,
        "hovermode": "closest",
        "shapes": shapes,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_cagr_by_region(
    income_rows: list[dict],
    hpi_rows: list[dict],
    selected_region: int | None = None,
    pt: int = 1,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    colors = SEMANTIC_COLORS[theme]

    # Categories: National first, then 5 regions
    categories = ["<b>ภาพรวม (ทั้งประเทศ)</b>", "กทม.+ปริมณฑล", "กลาง", "เหนือ", "อีสาน", "ใต้"]
    region_id_map = {"<b>ภาพรวม (ทั้งประเทศ)</b>": 0, "กทม.+ปริมณฑล": 1, "กลาง": 2, "เหนือ": 3, "อีสาน": 4, "ใต้": 5}

    inc_dict = {r["region_id"]: cagr_pct(r["v0"], r["v1"], r["years"]) for r in income_rows}
    hpi_dict = {r["region_id"]: cagr_pct(r["v0"], r["v1"], r["years"]) for r in hpi_rows}

    inc_vals, hpi_vals = [], []
    inc_texts, hpi_texts = [], []
    has_selection = selected_region is not None and selected_region > 0

    for cat in categories:
        rid = region_id_map[cat]
        # Income
        inc_c = inc_dict.get(rid, 0.0) or 0.0
        inc_vals.append(inc_c)
        inc_texts.append(f"{inc_c:+.2f}%" if inc_c != 0 else "0.00%")

        # HPI (Townhouse pt=3 in North/NE has no data)
        if pt == 3 and rid in (3, 4):
            hpi_vals.append(None)
            hpi_texts.append("ไม่มีข้อมูลราคาบ้าน")
        else:
            hpi_c = hpi_dict.get(rid, 0.0) or 0.0
            hpi_vals.append(hpi_c)
            hpi_texts.append(f"{hpi_c:+.2f}%" if hpi_c != 0 else "0.00%")

    fig = go.Figure()

    # Opacities
    opacities = []
    for cat in categories:
        rid = region_id_map[cat]
        if not has_selection or (selected_region == rid):
            opacities.append(1.0)
        else:
            opacities.append(0.55)

    # Income Bars
    fig.add_trace(go.Bar(
        x=categories,
        y=inc_vals,
        name="รายได้ครัวเรือน",
        marker=dict(
            color=colors["income"],
            opacity=opacities,
            cornerradius=6,
        ),
        text=inc_texts,
        textposition="outside",
        textfont=dict(family=FONT_FAMILY, size=11, color=t["text"]),
        hovertemplate="%{x}<br>รายได้: %{y:.2f}%/ปี<extra></extra>",
    ))

    # Housing Bars
    fig.add_trace(go.Bar(
        x=categories,
        y=hpi_vals,
        name="ราคาบ้าน",
        marker=dict(
            color=colors["housing"],
            opacity=opacities,
            cornerradius=6,
        ),
        text=hpi_texts,
        textposition="outside",
        textfont=dict(family=FONT_FAMILY, size=11, color=t["text"]),
        hovertemplate="%{x}<br>ราคาบ้าน: %{y:.2f}%/ปี<extra></extra>",
    ))

    # Thin vertical separator after national category (at x = 0.5)
    shapes = [
        dict(
            type="line",
            x0=0.5,
            x1=0.5,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color=t["border"], width=1, dash="dot"),
        ),
    ]

    layout.update({
        "margin": {"l": 48, "r": 24, "t": 20, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
        },
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": "%/ปี"},
            "tickformat": "+,.1f",
        },
        "barmode": "group",
        "height": 360,
        "shapes": shapes,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


def fig_cagr_by_type(
    types_data: list[dict],
    income_cagr: float,
    scope: str,
    selected_pt: int = 1,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    colors = SEMANTIC_COLORS[theme]

    cats = [r["name_th"] for r in types_data]
    hpi_vals = [cagr_pct(r["v0"], r["v1"], r["years"]) or 0.0 for r in types_data]
    texts = [f"{v:+.2f}%" for v in hpi_vals]

    # Differences compared to income
    diffs = [round(v - income_cagr, 2) for v in hpi_vals]

    # Opacity for selected property type
    opacities = []
    for r in types_data:
        if r.get("property_type_id") == selected_pt:
            opacities.append(1.0)
        else:
            opacities.append(0.65)

    customdata = [[scope, diff] for diff in diffs]

    fig = go.Figure(go.Bar(
        x=cats,
        y=hpi_vals,
        marker=dict(
            color=colors["housing"],
            opacity=opacities,
            cornerradius=6,
        ),
        text=texts,
        textposition="outside",
        textfont=dict(family=FONT_FAMILY, size=11.5, color=t["text"]),
        customdata=customdata,
        hovertemplate="%{x}<br>ราคาบ้าน: %{y:.2f}%/ปี<br>เทียบรายได้: %{customdata[1]:+.2f} จุด<extra></extra>",
    ))

    # Horizontal dashed blue reference line for income CAGR
    shapes = [
        dict(
            type="line",
            xref="paper",
            x0=0,
            x1=1,
            y0=income_cagr,
            y1=income_cagr,
            line=dict(color=colors["income"], width=2, dash="dash"),
        ),
    ]

    annotations = [
        dict(
            xref="paper",
            x=0.98,
            y=income_cagr,
            text=f"รายได้ {income_cagr:+.2f}%/ปี",
            showarrow=False,
            xanchor="right",
            yanchor="bottom" if income_cagr >= 0 else "top",
            font=dict(family=FONT_FAMILY, size=11, color=colors["income"], weight=600),
        ),
    ]

    layout.update({
        "margin": {"l": 48, "r": 24, "t": 20, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
        },
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": "%/ปี"},
            "tickformat": "+,.1f",
        },
        "height": 360,
        "shapes": shapes,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()
