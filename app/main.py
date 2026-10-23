"""FastAPI application entry point.

Endpoints:
- GET /                    -> Web UI (HTML)
- GET /healthz             -> Health check
- GET /api/meta            -> Filter metadata & as-of dates
- GET /api/tab/{tab_id}    -> Tab 1, 2, or 3 data (kpis, ring, charts, summaries, tables)
- GET /api/export/{tab}/{chart}.csv -> Export CSV with UTF-8 BOM
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.figures import tab1 as fig_tab1, tab2 as fig_tab2, tab3 as fig_tab3
from app.filters import Filters
from app.metrics import cagr_pct, format_number, pct_change
from app import summaries

app = FastAPI(title="Income × Housing Dashboard API", version="1.0.0")

# Mount static folder
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/meta")
def get_meta():
    return db.query_meta()


# ──────────────────────────────────────── TAB 1 HANDLER
def _handle_tab1(f: Filters) -> dict:
    meta = db.query_meta()
    year = f.year
    area = f.area
    region = f.region
    y0, y1 = f.y0, f.y1
    theme = f.theme

    # Region name
    region_info = next((r for r in meta["regions"] if r["region_id"] == region), None) if region is not None else None
    scope = region_info["short_th"] if region_info else "ทั่วประเทศ"

    # KPIs
    kpi_raw = db.query_tab1_kpi(year, area, region)
    income_val = kpi_raw["monthly_income"]
    base_income_val = kpi_raw["base_income"]
    delta_val = pct_change(base_income_val, income_val)
    years_span = year - 2554
    income_cagr = cagr_pct(base_income_val, income_val, years_span) if years_span > 0 else 0.0

    kpis = [
        {
            "id": "income",
            "label": "รายได้เฉลี่ย",
            "value": round(income_val),
            "unit": "บาท/เดือน",
            "delta": {
                "value": abs(delta_val) if delta_val is not None else 0.0,
                "unit": "%",
                "vs": "2554",
                "direction": "up" if (delta_val or 0) >= 0 else "down",
            },
        },
        {
            "id": "cagr",
            "label": f"CAGR 2554→{year}",
            "value": income_cagr,
            "unit": "%/ปี",
            "delta": None,
        },
        {
            "id": "transfer",
            "label": "สัดส่วนเงินโอน/สวัสดิการ",
            "value": round(kpi_raw["transfer_pct"], 1),
            "unit": "%",
            "delta": None,
        },
        {
            "id": "gap",
            "label": "ช่องว่างเมือง-ชนบท",
            "value": round(kpi_raw["gap_pct"], 1) if kpi_raw["gap_pct"] is not None else 0.0,
            "unit": "%",
            "delta": None,
        },
    ]

    ring = {
        "label": "สัดส่วนรายได้จากการทำงาน",
        "value": round(kpi_raw["work_pct"], 1),
        "unit": "%",
    }

    # Chart 1A: Choropleth
    if f.metric == "transfer":
        choro_data = db.query_tab1_choropleth_transfer(year, area)
        choro_title = f"สัดส่วนเงินโอน/สวัสดิการรายภาค ปี {year} (%)"
    elif f.metric == "index":
        choro_data = db.query_tab1_choropleth_index(year, area)
        choro_title = f"ดัชนีรายได้รายภาค ปี {year} (2554=100)"
    else:
        choro_data = db.query_tab1_choropleth(year, area)
        choro_title = f"รายได้เฉลี่ยรายภาค ปี {year} (บาท/เดือน)"

    fig_1a = fig_tab1.fig_choropleth(choro_data, theme=theme, title=choro_title)
    summary_1a_res = summaries.summary_1a(year, choro_data)
    table_1a = {
        "columns": ["รหัสภาค", "ภาค", "ค่า"],
        "rows": [[r["code"], r["short_th"], round(r["value"], 1)] for r in choro_data],
    }

    # Chart 1B: Treemap
    treemap_data = db.query_tab1_treemap(year, area, region)
    treemap_title = f"แหล่งที่มาของรายได้ ปี {year} ({scope})"
    fig_1b = fig_tab1.fig_treemap(treemap_data, theme=theme, title=treemap_title)
    summary_1b_res = summaries.summary_1b(year, treemap_data, scope)
    table_1b = {
        "columns": ["ภาค", "กลุ่ม", "แหล่งรายได้", "จำนวนเงิน (บาท)", "สัดส่วน (%)"],
        "rows": [
            [r["region"], r["group_th"], r["source_name_th"], round(r["amount_baht"]), round(r["share_pct"], 1)]
            for r in treemap_data
        ],
    }

    # Chart 1C: Linear Trend
    trend_data = db.query_tab1_trend(area, y0, y1)
    trend_title = f"แนวโน้มรายได้ {y0}→{y1}"
    fig_1c = fig_tab1.fig_trend(trend_data, theme=theme, metric=f.metric, title=trend_title)
    summary_1c_res = summaries.summary_1c(y0, y1, scope, trend_data)
    table_1c = {
        "columns": ["ปี (พ.ศ.)", "ภาค", "รายได้ (บาท/เดือน)", "ดัชนี (2554=100)"],
        "rows": [
            [r["year_be"], r["short_th"], round(r["monthly_income"]), round(r["income_index"], 1)]
            for r in trend_data
        ],
    }

    # Chart 1D: Urban-Rural Heatmap
    heatmap_data = db.query_tab1_heatmap(y0, y1)
    fig_1d = fig_tab1.fig_heatmap(heatmap_data, theme=theme, title=f"ช่องว่างเมือง-ชนบท {y0}→{y1} (%)")
    summary_1d_res = summaries.summary_1d(year, heatmap_data)
    table_1d = {
        "columns": ["ปี (พ.ศ.)", "ภาค", "ช่องว่าง (%)"],
        "rows": [[r["year_be"], r["short_th"], round(r["gap_pct"], 1)] for r in heatmap_data],
    }

    insights = summaries.tab1_insights(kpi_raw, summary_1a_res, summary_1c_res, summary_1d_res)

    return {
        "filters": f.to_dict(),
        "headline": summary_1c_res["headline"],
        "kpis": kpis,
        "ring": ring,
        "charts": {
            "choropleth": {
                "figure": fig_1a,
                "summary": summary_1a_res,
                "table": table_1a,
                "empty": None,
            },
            "treemap": {
                "figure": fig_1b,
                "summary": summary_1b_res,
                "table": table_1b,
                "empty": None,
            },
            "trend": {
                "figure": fig_1c,
                "summary": summary_1c_res,
                "table": table_1c,
                "empty": None,
            },
            "heatmap": {
                "figure": fig_1d,
                "summary": summary_1d_res,
                "table": table_1d,
                "empty": None,
            },
        },
        "insights": insights,
        "notes": [
            "รายได้เฉลี่ยต่อเดือนของครัวเรือน จากการสำรวจภาวะเศรษฐกิจและสังคมของครัวเรือน (สสช.)",
            "ข้อมูลมีเฉพาะปีสำรวจทุก 2 ปี (8 รอบ 2554-2568) ไม่ interpolate ข้ามปีที่ขาด",
            "ตัวเลขเป็นราคาตามปี (nominal) ไม่ปรับอัตราเงินเฟ้อ",
        ],
        "as_of": meta["as_of"],
    }


# ──────────────────────────────────────── TAB 2 HANDLER
def _handle_tab2(f: Filters) -> dict:
    meta = db.query_meta()
    year = f.year
    pt = f.pt
    region = f.region
    y0, y1 = f.y0, f.y1
    theme = f.theme
    grain = f.grain

    region_info = next((r for r in meta["regions"] if r["region_id"] == region), None) if region is not None else None
    scope = region_info["short_th"] if region_info else "ทั่วประเทศ"
    pt_info = next((p for p in meta["property_types"] if p["property_type_id"] == pt), None)
    pt_name = pt_info["name_th"] if pt_info else "รวมทุกประเภทที่อยู่อาศัย"

    # KPIs
    kpi_raw = db.query_tab2_kpi(year, pt, region)
    idx_val = kpi_raw["index_value"] or 100.0
    base_val = kpi_raw["base_value"] or 100.0
    years_span = year - 2554
    cagr_val = cagr_pct(base_val, idx_val, years_span) if years_span > 0 else 0.0

    kpis = [
        {
            "id": "hpi",
            "label": f"ดัชนีราคาบ้าน ปี {year}",
            "value": round(idx_val, 1),
            "unit": "(2554=100)",
            "delta": None,
        },
        {
            "id": "yoy",
            "label": f"YoY ปี {year}",
            "value": round(kpi_raw["yoy_pct"], 1) if kpi_raw["yoy_pct"] is not None else 0.0,
            "unit": "%",
            "delta": None,
        },
        {
            "id": "cagr",
            "label": f"CAGR 2554→{year}",
            "value": cagr_val,
            "unit": "%/ปี",
            "delta": None,
        },
        {
            "id": "fastest",
            "label": "ภาคที่โตเร็วสุด",
            "value": kpi_raw["fastest_region"] or "-",
            "unit": f"({round(kpi_raw['fastest_idx'] or 0, 1)})",
            "delta": None,
        },
    ]

    ring = {
        "label": f"สูงกว่าปีฐาน (2554)",
        "value": round(idx_val - 100.0, 1),
        "unit": "%",
    }

    # Chart 2A: Choropleth
    choro_data = db.query_tab2_choropleth(year, pt)
    choro_title = f"ดัชนีราคาบ้านรายภาค ปี {year} ({pt_name})"
    fig_2a = fig_tab2.fig_choropleth(choro_data, theme=theme, title=choro_title)
    summary_2a_res = summaries.summary_2a(year, pt_name, scope, choro_data)
    table_2a = {
        "columns": ["รหัสภาค", "ภาค", "ดัชนี (2554=100)"],
        "rows": [[r["code"], r["short_th"], round(r["value"], 1)] for r in choro_data],
    }

    # Check for empty / unavailable series (e.g. Townhouse in North/NE)
    empty_notice = None
    if pt == 3 and region in (3, 4):
        empty_notice = "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ในฐานข้อมูล ธปท."

    # Chart 2B: Trend (monthly or annual)
    if grain == "monthly":
        trend_data = db.query_tab2_trend_monthly(pt, y0, y1)
        fig_2b = fig_tab2.fig_trend(trend_data, theme=theme, is_monthly=True,
                                    title=f"แนวโน้มดัชนีราคาบ้านรายเดือน ({pt_name})")
        table_2b = {
            "columns": ["เดือน", "ปี (พ.ศ.)", "ภาค", "ดัชนี"],
            "rows": [[r["month_no"], r["year_be"], r["short_th"], round(r["index_value"], 1)] for r in trend_data],
        }
    else:
        trend_data = db.query_tab2_trend_annual(pt, y0, y1)
        fig_2b = fig_tab2.fig_trend(trend_data, theme=theme, is_monthly=False,
                                    title=f"แนวโน้มดัชนีราคาบ้านรายปี ({pt_name})")
        table_2b = {
            "columns": ["ปี (พ.ศ.)", "ภาค", "ดัชนี"],
            "rows": [[r["year_be"], r["short_th"], round(r["index_value"], 1)] for r in trend_data],
        }

    # Chart 2C: Heatmap YoY
    heatmap_data = db.query_tab2_heatmap(pt, y0, y1)
    fig_2c = fig_tab2.fig_heatmap(heatmap_data, theme=theme, title=f"อัตราเปลี่ยนแปลงรายปี (YoY %) {y0}→{y1}")
    summary_2c_res = summaries.summary_2c(year, heatmap_data)
    table_2c = {
        "columns": ["ปี (พ.ศ.)", "ภาค", "YoY (%)"],
        "rows": [[r["year_be"], r["short_th"], round(r["yoy_pct"], 1)] for r in heatmap_data],
    }

    insights = summaries.tab2_insights(kpi_raw, summary_2a_res, summary_2c_res)

    return {
        "filters": f.to_dict(),
        "headline": summary_2a_res["headline"],
        "kpis": kpis,
        "ring": ring,
        "charts": {
            "choropleth": {
                "figure": fig_2a,
                "summary": summary_2a_res,
                "table": table_2a,
                "empty": empty_notice,
            },
            "trend": {
                "figure": fig_2b,
                "summary": summary_2a_res,
                "table": table_2b,
                "empty": empty_notice,
            },
            "heatmap": {
                "figure": fig_2c,
                "summary": summary_2c_res,
                "table": table_2c,
                "empty": empty_notice,
            },
        },
        "insights": insights,
        "notes": [
            "ดัชนีราคาที่อยู่อาศัย (2554=100) ธนาคารแห่งประเทศไทย (BoT EC_EI_008_S4)",
            "ดัชนีคำนวณด้วย Hedonic regression แบบเฉลี่ยเคลื่อนที่ 3 เดือน จากฐานข้อมูลสินเชื่อ",
            "ภาคเหนือและอีสานไม่มีชุดข้อมูลทาวน์เฮ้าส์ (ดัชนีรวมทุกประเภทจึงเท่ากับบ้านเดี่ยว)",
            "ตั้งแต่ ม.ค. 2566 เพิ่มฐานข้อมูลของสถาบันการเงินเฉพาะกิจ",
        ],
        "as_of": meta["as_of"],
    }


# ──────────────────────────────────────── TAB 3 HANDLER
def _handle_tab3(f: Filters) -> dict:
    meta = db.query_meta()
    year = f.year
    pt = f.pt
    region = f.region
    y0, y1 = f.y0, f.y1
    theme = f.theme

    region_info = next((r for r in meta["regions"] if r["region_id"] == region), None) if region is not None else None
    scope = region_info["short_th"] if region_info else "ทั่วประเทศ"
    pt_info = next((p for p in meta["property_types"] if p["property_type_id"] == pt), None)
    pt_name = pt_info["name_th"] if pt_info else "รวมทุกประเภทที่อยู่อาศัย"

    # KPIs
    kpi_raw = db.query_tab3_kpi(year, pt, y0, y1, region)
    pti_val = kpi_raw["price_to_income_index"] or 100.0
    status_label = "ซื้อยากขึ้น" if pti_val > 100 else "ง่ายขึ้น"

    # CAGRs over window y0 -> y1
    income_cagr_rows = db.query_tab3_cagr_income(y0, y1)
    hpi_cagr_rows = db.query_tab3_cagr_hpi(pt, y0, y1)

    target_rid = region if region is not None else 0
    inc_row = next((r for r in income_cagr_rows if r["region_id"] == target_rid), None)
    hpi_row = next((r for r in hpi_cagr_rows if r["region_id"] == target_rid), None)

    inc_cagr = cagr_pct(inc_row["v0"], inc_row["v1"], inc_row["years"]) if inc_row else 0.0
    hpi_cagr = cagr_pct(hpi_row["v0"], hpi_row["v1"], hpi_row["years"]) if hpi_row else 0.0
    gap = round((hpi_cagr or 0) - (inc_cagr or 0), 2)

    kpis = [
        {
            "id": "pti",
            "label": f"ดัชนีราคา ÷ รายได้ ปี {year}",
            "value": round(pti_val, 1),
            "unit": f"({status_label})",
            "delta": None,
        },
        {
            "id": "inc_cagr",
            "label": f"CAGR รายได้ {y0}→{y1}",
            "value": inc_cagr,
            "unit": "%/ปี",
            "delta": None,
        },
        {
            "id": "hpi_cagr",
            "label": f"CAGR ราคาบ้าน {y0}→{y1}",
            "value": hpi_cagr,
            "unit": "%/ปี",
            "delta": None,
        },
        {
            "id": "cagr_gap",
            "label": "ช่องว่าง CAGR (บ้าน - รายได้)",
            "value": gap,
            "unit": "จุด %",
            "delta": None,
        },
    ]

    ring = {
        "label": "ภาคที่ราคาบ้านโตเร็วกว่ารายได้",
        "value": f"{kpi_raw['regions_harder']} / {kpi_raw['total_regions']}",
        "unit": "ภาค",
    }

    # Chart 3A: Ratio Trend
    pti_data = db.query_tab3_price_to_income(pt, y0, y1)

    # If y0 > 2554, rebase income_index, hpi_index, and price_to_income_index so that y0 = 100
    if y0 > 2554:
        by_reg = {}
        for r in pti_data:
            by_reg.setdefault(r["region_id"], []).append(r)

        rebased_data = []
        for rid, rows in by_reg.items():
            base_row = next((r for r in rows if r["year_be"] == y0), None)
            if not base_row:
                rebased_data.extend(rows)
                continue
            b_inc = base_row["income_index"]
            b_hpi = base_row["hpi_index"]
            for r in rows:
                new_inc = 100.0 * r["income_index"] / b_inc if b_inc else 100.0
                new_hpi = 100.0 * r["hpi_index"] / b_hpi if b_hpi else 100.0
                new_pti = 100.0 * new_hpi / new_inc if new_inc else 100.0
                rebased_data.append({
                    **r,
                    "income_index": new_inc,
                    "hpi_index": new_hpi,
                    "price_to_income_index": new_pti,
                })
        pti_data = rebased_data

    # Update pti_val for KPI from rebased data if available
    target_pti_row = next((r for r in pti_data if r["region_id"] == target_rid and r["year_be"] == year), None)
    if target_pti_row:
        pti_val = target_pti_row["price_to_income_index"]
        status_label = "ซื้อยากขึ้น" if pti_val > 100 else "ง่ายขึ้น"
    fig_3a = fig_tab3.fig_price_to_income_trend(pti_data, y0, y1, theme=theme,
                                                title=f"ดัชนีราคาบ้าน ÷ รายได้ {y0}→{y1}")
    summary_3a_res = summaries.summary_3a(y0, y1, scope, pti_data)
    table_3a = {
        "columns": ["ปี (พ.ศ.)", "ภาค", "ดัชนีรายได้", "ดัชนีราคาบ้าน", "ดัชนีราคา÷รายได้"],
        "rows": [
            [r["year_be"], r["short_th"], round(r["income_index"], 1), round(r["hpi_index"], 1), round(r["price_to_income_index"], 1)]
            for r in pti_data
        ],
    }

    # Chart 3B: Paired Bars (income index vs hpi index)
    fig_3b = fig_tab3.fig_paired_bars(pti_data, region_name=scope, theme=theme,
                                      title=f"เปรียบเทียบดัชนีรายได้ vs ราคาบ้าน")
    table_3b = table_3a

    # Chart 3C: CAGR comparison (2 bars)
    fig_3c = fig_tab3.fig_cagr_comparison(inc_cagr or 0, hpi_cagr or 0, theme=theme,
                                          title=f"CAGR ตลอดช่วง {y0}→{y1} ({scope})")
    summary_3c_res = summaries.summary_3c(inc_cagr or 0, hpi_cagr or 0)
    table_3c = {
        "columns": ["ตัวชี้วัด", "CAGR (%/ปี)"],
        "rows": [["รายได้ครัวเรือน", inc_cagr], ["ดัชนีราคาบ้าน", hpi_cagr]],
    }

    # Chart 3D: CAGR by region
    fig_3d = fig_tab3.fig_cagr_by_region(income_cagr_rows, hpi_cagr_rows, theme=theme,
                                        title=f"CAGR แยกตามภาค {y0}→{y1}")
    summary_3d_res = summaries.summary_3d(scope, inc_cagr or 0, hpi_cagr or 0)
    table_3d = {
        "columns": ["ภาค", "CAGR รายได้ (%/ปี)", "CAGR ราคาบ้าน (%/ปี)", "ช่องว่าง (จุด)"],
        "rows": [
            [
                r_inc["short_th"],
                cagr_pct(r_inc["v0"], r_inc["v1"], r_inc["years"]),
                cagr_pct(r_hpi["v0"], r_hpi["v1"], r_hpi["years"]),
                round((cagr_pct(r_hpi["v0"], r_hpi["v1"], r_hpi["years"]) or 0) - (cagr_pct(r_inc["v0"], r_inc["v1"], r_inc["years"]) or 0), 2)
            ]
            for r_inc, r_hpi in zip(income_cagr_rows, hpi_cagr_rows)
            if not r_inc.get("is_national")
        ],
    }

    insights = summaries.tab3_insights(summary_3a_res, summary_3c_res)

    return {
        "filters": f.to_dict(),
        "headline": summary_3a_res["headline"],
        "kpis": kpis,
        "ring": ring,
        "charts": {
            "price_to_income": {
                "figure": fig_3a,
                "summary": summary_3a_res,
                "table": table_3a,
                "empty": None,
            },
            "paired_bars": {
                "figure": fig_3b,
                "summary": summary_3a_res,
                "table": table_3b,
                "empty": None,
            },
            "cagr_comparison": {
                "figure": fig_3c,
                "summary": summary_3c_res,
                "table": table_3c,
                "empty": None,
            },
            "cagr_by_region": {
                "figure": fig_3d,
                "summary": summary_3d_res,
                "table": table_3d,
                "empty": None,
            },
        },
        "insights": insights,
        "notes": [
            "รายได้มีเฉพาะปีรอบสำรวจของ สสช. ไม่ interpolate ปีที่ขาด",
            "ทั้งสองชุดข้อมูลเป็นราคาตามปี (nominal) และดัชนีราคาบ้านบอกเฉพาะการเปลี่ยนแปลง ไม่ใช่ระดับราคา",
            "นิยามพื้นที่ กทม.+ปริมณฑล ของ สสช. กับ ธปท. อาจไม่ตรงกัน (เทียบได้โดยประมาณ)",
        ],
        "as_of": meta["as_of"],
    }


@app.get("/api/tab/{tab_id}")
def get_tab(
    tab_id: int,
    year: Optional[int] = Query(None),
    y0: Optional[int] = Query(None),
    y1: Optional[int] = Query(None),
    region: Optional[int] = Query(None),
    area: Optional[int] = Query(None),
    pt: Optional[int] = Query(None),
    metric: Optional[str] = Query(None),
    grain: Optional[str] = Query(None),
    theme: Optional[str] = Query(None),
):
    try:
        f = Filters.from_params(
            tab=tab_id,
            year=year,
            y0=y0,
            y1=y1,
            region=region,
            area=area,
            pt=pt,
            metric=metric,
            grain=grain,
            theme=theme,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if tab_id == 1:
        return _handle_tab1(f)
    elif tab_id == 2:
        return _handle_tab2(f)
    elif tab_id == 3:
        return _handle_tab3(f)
    else:
        raise HTTPException(status_code=404, detail="Tab not found")


@app.get("/api/export/{tab_id}/{chart_id}.csv")
def export_csv(
    tab_id: int,
    chart_id: str,
    year: Optional[int] = Query(None),
    y0: Optional[int] = Query(None),
    y1: Optional[int] = Query(None),
    region: Optional[int] = Query(None),
    area: Optional[int] = Query(None),
    pt: Optional[int] = Query(None),
    metric: Optional[str] = Query(None),
    grain: Optional[str] = Query(None),
    theme: Optional[str] = Query(None),
):
    try:
        f = Filters.from_params(
            tab=tab_id,
            year=year,
            y0=y0,
            y1=y1,
            region=region,
            area=area,
            pt=pt,
            metric=metric,
            grain=grain,
            theme=theme,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if tab_id == 1:
        tab_res = _handle_tab1(f)
    elif tab_id == 2:
        tab_res = _handle_tab2(f)
    elif tab_id == 3:
        tab_res = _handle_tab3(f)
    else:
        raise HTTPException(status_code=404, detail="Tab not found")

    chart_data = tab_res["charts"].get(chart_id)
    if not chart_data or "table" not in chart_data:
        raise HTTPException(status_code=404, detail=f"Chart '{chart_id}' not found")

    table = chart_data["table"]
    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens it with Thai characters intact
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(table["columns"])
    for row in table["rows"]:
        writer.writerow(row)

    csv_content = output.getvalue()
    filename = f"export_tab{tab_id}_{chart_id}_{f.year}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = Path(__file__).resolve().parent / "templates" / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Income × Housing Dashboard</h1>")
