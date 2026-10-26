"""Plotly figure builders for Tab 3 — Income vs Housing Price (v2 redesign).

4 Charts:
1. Hero: Price-to-Income Ratio Trend (Baseline 100, shaded zones, rich hover comparing indices)
2. CAGR Comparison: Grouped Bar Chart with toggle (ภาพรวม vs แยกตามประเภทบ้าน)
3. Affordability Gap Area Chart: Shaded gap (HPI index - Income index; Red above 0, Green below 0)
4. Growth Balance Scatter Plot: X=Income CAGR, Y=HPI CAGR, 45-degree balance line, quadrant zones
"""
from __future__ import annotations

import plotly.graph_objects as go

from app.figures.theme import (
    FONT_FAMILY, SEMANTIC_COLORS, TOKENS,
    get_base_layout, region_color, region_dash,
)
from app.metrics import cagr_pct


# ──────────────── 1. Hero: Price-to-Income Ratio Trend ────────────────
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
        dict(
            xref="paper",
            x=0.01,
            y=y_max - 2,
            text="ซื้อยากขึ้น (ราคาบ้านพุ่งแซงรายได้)",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_FAMILY, size=12, color=colors["housing"], weight=600),
        ),
        dict(
            xref="paper",
            x=0.01,
            y=y_min + 2,
            text="ซื้อง่ายขึ้น (รายได้โตแซงราคาบ้าน)",
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

        # Rich hover customdata: [name, ratio, income_index, hpi_index, diff_from_start]
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
                rid,
            ])

        hovertemplate = (
            "<b>ปี %{x} · %{customdata[0]}</b><br>"
            "อัตราส่วนราคา÷รายได้: <b>%{customdata[1]:.1f}</b><br>"
            "ดัชนีราคาบ้าน: %{customdata[3]:.1f}<br>"
            "ดัชนีรายได้: %{customdata[2]:.1f}<br>"
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
        "height": 400,
        "hovermode": "closest",
        "hoverdistance": 30,
        "shapes": shapes,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


# ──────────────── 2. CAGR Comparison: Grouped Bar Chart ────────────────
def fig_cagr_comparison(
    income_cagr: float,
    hpi_cagr: float,
    types_data: list[dict],
    income_rows: list[dict] | None = None,
    hpi_rows: list[dict] | None = None,
    view_mode: str = "summary",
    scope_name: str = "ทั่วประเทศ",
    selected_pt: int = 1,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    colors = SEMANTIC_COLORS[theme]
    fig = go.Figure()

    if view_mode == "by_type":
        # Grouped by property type: 3 categories
        cats = [r["name_th"] for r in types_data]
        inc_vals = [income_cagr] * len(cats)
        hpi_vals = [cagr_pct(r["v0"], r["v1"], r["years"]) or 0.0 for r in types_data]

        inc_texts = [f"{v:+.2f}% ต่อปี" for v in inc_vals]
        hpi_texts = [f"{v:+.2f}% ต่อปี" for v in hpi_vals]

        # Income bars
        fig.add_trace(go.Bar(
            x=cats,
            y=inc_vals,
            name="CAGR รายได้ครัวเรือน",
            marker=dict(color=colors["income"], cornerradius=6),
            text=inc_texts,
            textposition="outside",
            textfont=dict(family=FONT_FAMILY, size=11.5, color=t["text"]),
            hovertemplate="%{x}<br>รายได้: %{y:.2f}%/ปี<extra></extra>",
        ))

        # Housing bars
        fig.add_trace(go.Bar(
            x=cats,
            y=hpi_vals,
            name="CAGR ราคาบ้าน",
            marker=dict(color=colors["housing"], cornerradius=6),
            text=hpi_texts,
            textposition="outside",
            textfont=dict(family=FONT_FAMILY, size=11.5, color=t["text"]),
            hovertemplate="%{x}<br>ราคาบ้าน: %{y:.2f}%/ปี<extra></extra>",
        ))
    elif view_mode == "by_region":
        # Grouped by region: 6 categories (National + 5 regions)
        regions = [
            {"id": 0, "name": "ทั่วประเทศ"},
            {"id": 1, "name": "กทม.+ปริมณฑล"},
            {"id": 2, "name": "กลาง"},
            {"id": 3, "name": "เหนือ"},
            {"id": 4, "name": "อีสาน"},
            {"id": 5, "name": "ใต้"},
        ]
        inc_dict = {r["region_id"]: (cagr_pct(r["v0"], r["v1"], r["years"]) or 0.0) for r in (income_rows or [])}
        hpi_dict = {r["region_id"]: (cagr_pct(r["v0"], r["v1"], r["years"]) or 0.0) for r in (hpi_rows or [])}

        cats = [reg["name"] for reg in regions]
        inc_vals = [inc_dict.get(reg["id"], 0.0) for reg in regions]
        hpi_vals = [hpi_dict.get(reg["id"], 0.0) for reg in regions]

        inc_texts = [f"{v:+.2f}%" for v in inc_vals]
        hpi_texts = [f"{v:+.2f}%" for v in hpi_vals]

        fig.add_trace(go.Bar(
            x=cats,
            y=inc_vals,
            name="CAGR รายได้ครัวเรือน",
            marker=dict(color=colors["income"], cornerradius=6),
            text=inc_texts,
            textposition="outside",
            textfont=dict(family=FONT_FAMILY, size=11, color=t["text"]),
            hovertemplate="%{x}<br>CAGR รายได้: %{y:.2f}%/ปี<extra></extra>",
        ))

        fig.add_trace(go.Bar(
            x=cats,
            y=hpi_vals,
            name="CAGR ราคาบ้าน",
            marker=dict(color=colors["housing"], cornerradius=6),
            text=hpi_texts,
            textposition="outside",
            textfont=dict(family=FONT_FAMILY, size=11, color=t["text"]),
            hovertemplate="%{x}<br>CAGR ราคาบ้าน: %{y:.2f}%/ปี<extra></extra>",
        ))
    else:
        # Summary view: 1 pair comparing the selected scope
        cats = [f"<b>{scope_name}</b>"]
        inc_vals = [income_cagr]
        hpi_vals = [hpi_cagr]

        fig.add_trace(go.Bar(
            x=cats,
            y=inc_vals,
            name="CAGR รายได้ครัวเรือน",
            marker=dict(color=colors["income"], cornerradius=6),
            text=[f"{income_cagr:+.2f}% ต่อปี"],
            textposition="outside",
            textfont=dict(family=FONT_FAMILY, size=12, color=t["text"]),
            hovertemplate="รายได้: %{y:.2f}%/ปี<extra></extra>",
        ))

        fig.add_trace(go.Bar(
            x=cats,
            y=hpi_vals,
            name="CAGR ราคาบ้าน",
            marker=dict(color=colors["housing"], cornerradius=6),
            text=[f"{hpi_cagr:+.2f}% ต่อปี"],
            textposition="outside",
            textfont=dict(family=FONT_FAMILY, size=12, color=t["text"]),
            hovertemplate="ราคาบ้าน: %{y:.2f}%/ปี<extra></extra>",
        ))

    all_bar_vals = inc_vals + hpi_vals
    y_max = max(all_bar_vals) * 1.3 if all_bar_vals and max(all_bar_vals) > 0 else 5.0
    y_min = min(min(all_bar_vals) * 1.3, 0.0) if all_bar_vals else 0.0

    layout.update({
        "margin": {"l": 48, "r": 24, "t": 20, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
        },
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": "%/ปี"},
            "range": [y_min, y_max],
            "tickformat": "+,.1f",
        },
        "barmode": "group",
        "height": 340,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


# ──────────────── 3. Affordability Gap Area Chart ────────────────
def fig_affordability_gap_area(
    data: list[dict],
    selected_region: int | None = None,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    fig = go.Figure()

    # Target region rows
    target_rid = selected_region if selected_region is not None else 0
    rows = [r for r in data if r["region_id"] == target_rid]
    rows.sort(key=lambda x: x["year_be"])

    xs = [str(r["year_be"]) for r in rows]
    inc_indices = [r["income_index"] for r in rows]
    hpi_indices = [r["hpi_index"] for r in rows]
    gaps = [round(h - i, 2) for h, i in zip(hpi_indices, inc_indices)]

    # Separate positive gap (Harder / Red) and negative gap (Easier / Green)
    pos_gaps = [max(0.0, g) for g in gaps]
    neg_gaps = [min(0.0, g) for g in gaps]

    customdata = [[h, i, g] for h, i, g in zip(hpi_indices, inc_indices, gaps)]

    # Shaded positive area (Red: House price growth > Income growth)
    fig.add_trace(go.Scatter(
        x=xs,
        y=pos_gaps,
        mode="lines",
        name="ราคาบ้านพุ่งแซง (ซื้อยากขึ้น)",
        line=dict(color="#E5484D", width=2),
        fill="tozeroy",
        fillcolor="rgba(229, 72, 77, 0.20)",
        customdata=customdata,
        hovertemplate=(
            "<b>ปี %{x}</b><br>"
            "ส่วนต่างราคาบ้าน − รายได้: <b>%{customdata[2]:+.1f} จุด</b><br>"
            "ดัชนีราคาบ้าน: %{customdata[0]:.1f}<br>"
            "ดัชนีรายได้: %{customdata[1]:.1f}"
            "<extra></extra>"
        ),
    ))

    # Shaded negative area (Green: Income growth > House price growth)
    fig.add_trace(go.Scatter(
        x=xs,
        y=neg_gaps,
        mode="lines",
        name="รายได้โตแซง (ซื้อง่ายขึ้น)",
        line=dict(color="#0E9F6E", width=2),
        fill="tozeroy",
        fillcolor="rgba(14, 159, 110, 0.20)",
        customdata=customdata,
        hovertemplate=(
            "<b>ปี %{x}</b><br>"
            "ส่วนต่างราคาบ้าน − รายได้: <b>%{customdata[2]:+.1f} จุด</b><br>"
            "ดัชนีราคาบ้าน: %{customdata[0]:.1f}<br>"
            "ดัชนีรายได้: %{customdata[1]:.1f}"
            "<extra></extra>"
        ),
    ))

    # Reference zero line
    shapes = [
        dict(
            type="line",
            xref="paper",
            x0=0,
            x1=1,
            y0=0,
            y1=0,
            line=dict(color=t["text_muted"], width=1.5, dash="dash"),
        ),
    ]

    annotations = [
        dict(
            xref="paper",
            x=0.01,
            y=0,
            text="0 = รายได้กับราคาบ้านเติบโตเท่ากัน (สมดุล)",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(family=FONT_FAMILY, size=11, color=t["text_muted"]),
        ),
    ]

    min_g = min(min(gaps), 0) - 5
    max_g = max(max(gaps), 0) + 5

    layout.update({
        "margin": {"l": 48, "r": 24, "t": 20, "b": 28},
        "xaxis": {
            **layout["xaxis"],
            "type": "category",
        },
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": "ส่วนต่างดัชนี (ราคาบ้าน − รายได้)"},
            "range": [min_g, max_g],
            "tickformat": "+,.0f",
        },
        "height": 340,
        "shapes": shapes,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()


# ──────────────── 4. Growth Balance Scatter Plot ────────────────
def fig_growth_balance_scatter(
    income_rows: list[dict],
    hpi_rows: list[dict],
    selected_region: int | None = None,
    theme: str = "dark",
) -> dict:
    layout = get_base_layout(theme)
    t = TOKENS[theme]
    fig = go.Figure()

    # Regions mapping
    regions = [
        {"id": 1, "name": "กทม.+ปริมณฑล"},
        {"id": 2, "name": "กลาง"},
        {"id": 3, "name": "เหนือ"},
        {"id": 4, "name": "อีสาน"},
        {"id": 5, "name": "ใต้"},
        {"id": 0, "name": "ทั้งประเทศ"},
    ]

    inc_dict = {r["region_id"]: cagr_pct(r["v0"], r["v1"], r["years"]) or 0.0 for r in income_rows}
    hpi_dict = {r["region_id"]: cagr_pct(r["v0"], r["v1"], r["years"]) or 0.0 for r in hpi_rows}

    xs = []
    ys = []
    texts = []
    colors = []
    sizes = []
    customdata = []

    for reg in regions:
        rid = reg["id"]
        rname = reg["name"]
        x_val = inc_dict.get(rid, 0.0)
        y_val = hpi_dict.get(rid, 0.0)
        gap = round(y_val - x_val, 2)
        is_sel = (selected_region is not None and selected_region == rid) or (selected_region is None and rid == 0)

        xs.append(x_val)
        ys.append(y_val)
        texts.append(f"  {rname}")
        colors.append(region_color(rname, theme))
        sizes.append(20 if is_sel else 14)

        status_desc = "ราคาบ้านโตเร็วกว่า" if gap > 0 else "รายได้โตเร็วกว่า"
        customdata.append([rname, x_val, y_val, gap, status_desc, rid])

    # Dynamic bounds for 45-degree diagonal line
    all_vals = xs + ys
    v_min = min(all_vals) - 1.0
    v_max = max(all_vals) + 1.2

    # 45-degree diagonal equality line (X = Y)
    fig.add_trace(go.Scatter(
        x=[v_min, v_max],
        y=[v_min, v_max],
        mode="lines",
        name="เส้นสมดุล (X = Y)",
        line=dict(color=t["text_muted"], width=1.5, dash="dash"),
        hoverinfo="skip",
    ))

    # Scatter points for regions
    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        name="ภูมิภาค",
        text=texts,
        textposition="top right",
        textfont=dict(family=FONT_FAMILY, size=12, color=t["text"], weight=600),
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(color=t["surface"], width=2.5),
        ),
        customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "CAGR รายได้: %{customdata[1]:+.2f}%/ปี<br>"
            "CAGR ราคาบ้าน: %{customdata[2]:+.2f}%/ปี<br>"
            "ส่วนต่าง (บ้าน − รายได้): %{customdata[3]:+.2f} จุด (%{customdata[4]})"
            "<extra></extra>"
        ),
    ))

    # Zone annotations
    annotations = [
        # Line of balance label
        dict(
            x=(v_min + v_max) / 2 + 0.3,
            y=(v_min + v_max) / 2 - 0.2,
            text="เส้นสมดุล (รายได้โต = ราคาบ้านโต)",
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=11, color=t["text_muted"]),
            textangle=35,
        ),
        # Easier (below diagonal)
        dict(
            xref="paper",
            yref="paper",
            x=0.85,
            y=0.15,
            text="รายได้โตไวกว่าราคาบ้าน<br>(ทำเลทองคนซื้อ)",
            showarrow=False,
            xanchor="center",
            font=dict(family=FONT_FAMILY, size=11.5, color="#0E9F6E", weight=600),
        ),
        # Harder (above diagonal)
        dict(
            xref="paper",
            yref="paper",
            x=0.25,
            y=0.90,
            text="ราคาบ้านพุ่งแซงรายได้<br>(เริ่มซื้อยาก)",
            showarrow=False,
            xanchor="center",
            font=dict(family=FONT_FAMILY, size=11.5, color="#FF7A1A", weight=600),
        ),
        # Bubble warning (top left)
        dict(
            xref="paper",
            yref="paper",
            x=0.08,
            y=0.72,
            text="เสี่ยงฟองสบู่<br>(ราคาพุ่งแต่รายได้ไม่โต)",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_FAMILY, size=10.5, color="#E5484D"),
        ),
    ]

    layout.update({
        "margin": {"l": 48, "r": 36, "t": 20, "b": 36},
        "xaxis": {
            **layout["xaxis"],
            "title": {"text": "CAGR รายได้ครัวเรือน (%/ปี)"},
            "range": [v_min, v_max],
            "tickformat": "+,.1f",
        },
        "yaxis": {
            **layout["yaxis"],
            "title": {"text": "CAGR ราคาบ้าน (%/ปี)"},
            "range": [v_min, v_max],
            "tickformat": "+,.1f",
        },
        "height": 400,
        "annotations": annotations,
    })
    fig.update_layout(**layout)
    return fig.to_plotly_json()
