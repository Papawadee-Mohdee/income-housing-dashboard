"""FastAPI application entry point (v2 design).

Endpoints:
- GET /                    -> Web UI (HTML)
- GET /healthz             -> Health check
- GET /api/meta            -> Filter metadata, as-of dates, and cpi_available
- GET /api/tab/{tab_id}    -> Tab 1, 2, or 3 data (kpis, charts, status_line, notes)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.figures import tab1 as fig_tab1, tab2 as fig_tab2, tab3 as fig_tab3
from app.filters import Filters
from app.metrics import cagr_pct, pct_change

app = FastAPI(title="Income × Housing Dashboard API", version="2.0.0")

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

    region_info = next((r for r in meta["regions"] if r["region_id"] == region), None) if region is not None else None
    scope = region_info["short_th"] if region_info else "ทั่วประเทศ"
    area_info = next((a for a in meta["area_types"] if a["area_type_id"] == area), None)
    area_name = area_info["name_th"] if area_info else "รวมทุกเขต"

    # Status line
    status_line = f"{scope} · ปี {year} · {area_name}"

    # KPIs
    kpi_raw = db.query_tab1_kpi(year, area, region)
    income_val = kpi_raw["monthly_income"]
    base_income_val = kpi_raw["base_income"]

    is_base_year = (year == 2554)
    delta_val = pct_change(base_income_val, income_val) if not is_base_year else None
    years_span = year - 2554
    income_cagr = cagr_pct(base_income_val, income_val, years_span) if years_span > 0 else None

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
            } if delta_val is not None else None,
        },
        {
            "id": "cagr",
            "label": f"CAGR 2554→{year}",
            "value": round(income_cagr, 2) if income_cagr is not None else "—",
            "unit": "%/ปี" if income_cagr is not None else "(ปีฐาน)",
            "delta": {
                "value": round(abs(income_cagr), 2),
                "unit": "%",
                "vs": "2554",
                "direction": "up" if (income_cagr or 0) >= 0 else "down",
            } if (income_cagr is not None and not is_base_year) else None,
        },
        {
            "id": "transfer",
            "label": "สัดส่วนเงินโอน/สวัสดิการ",
            "value": round(kpi_raw["transfer_pct"], 1),
            "unit": "% ของรายได้",
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

    # Chart 1A: Choropleth
    if f.metric == "transfer":
        choro_data = db.query_tab1_choropleth_transfer(year, area)
        metric_label = "สัดส่วนเงินโอน"
        choro_unit = "%"
    elif f.metric == "index":
        choro_data = db.query_tab1_choropleth_index(year, area)
        metric_label = "ดัชนีรายได้"
        choro_unit = "(2554=100)"
    else:
        choro_data = db.query_tab1_choropleth(year, area)
        metric_label = "รายได้เฉลี่ย"
        choro_unit = "บาท/เดือน"

    fig_1a = fig_tab1.fig_choropleth(
        choro_data,
        selected_region=region,
        theme=theme,
        metric_label=metric_label,
        unit=choro_unit,
        year=year,
        area_name=area_name,
    )

    # Chart 1B: Trend (Straight line, categories matching survey years)
    trend_data = db.query_tab1_trend(area, 2554, 2568)
    fig_1c = fig_tab1.fig_trend(
        trend_data,
        selected_region=region,
        theme=theme,
        metric=f.metric,
    )

    # Chart 1C: Urban-Rural Heatmap
    heatmap_data = db.query_tab1_heatmap(2554, 2568)
    fig_1d = fig_tab1.fig_heatmap(
        heatmap_data,
        selected_region=region,
        selected_year=year,
        theme=theme,
    )

    # Chart 1D: Treemap (Strict parent share calculations, full width)
    treemap_data = db.query_tab1_treemap(year, area, region)
    fig_1b = fig_tab1.fig_treemap(treemap_data, theme=theme)

    return {
        "filters": f.to_dict(),
        "status_line": status_line,
        "kpis": kpis,
        "charts": {
            "choropleth": {
                "figure": fig_1a,
                "read_guide": "สีเข้ม = รายได้สูง · คลิกภาคเพื่อกรอง",
                "note": "ที่มา: สสช. SES (บาท/ครัวเรือน/เดือน ราคาตามปี)",
                "empty": None,
            },
            "trend": {
                "figure": fig_1c,
                "read_guide": "คลิกจุดเพื่อเลือกปี · คลิกเส้นเพื่อเลือกภาค",
                "note": "รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี) ไม่เติมค่าปีที่ขาด",
                "empty": None,
            },
            "heatmap": {
                "figure": fig_1d,
                "read_guide": "คลิกช่องเพื่อเลือกภาคและปีพร้อมกัน",
                "note": "ช่องว่างเมือง-ชนบท = (ในเขต − นอกเขต) ÷ นอกเขต × 100",
                "empty": None,
            },
            "treemap": {
                "figure": fig_1b,
                "read_guide": "ขนาดกล่อง = ยอดรายได้ · สี = แหล่งที่มาของรายได้",
                "note": "สัดส่วนคำนวณจากยอดรวมของภาคนั้นๆ (รวม 100%)",
                "empty": None,
            },
        },
        "notes": [
            "รายได้เฉลี่ยต่อเดือนของครัวเรือน จากการสำรวจภาวะเศรษฐกิจและสังคมของครัวเรือน (สสช.)",
            "ข้อมูลมีเฉพาะปีสำรวจทุก 2 ปี (8 รอบ 2554–2568) ไม่เติมค่าข้ามปีที่ขาด",
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

    status_line = f"{scope} · ปี {year} · {pt_name}"

    # KPIs
    kpi_raw = db.query_tab2_kpi(year, pt, region)
    idx_val = kpi_raw["index_value"] or 100.0
    base_val = kpi_raw["base_value"] or 100.0
    is_base_year = (year == 2554)
    years_span = year - 2554
    cagr_val = cagr_pct(base_val, idx_val, years_span) if years_span > 0 else None
    yoy_val = kpi_raw["yoy_pct"] if not is_base_year else None

    # Calculate CAGR from 2554 for fastest region
    fastest_cagr = cagr_pct(100.0, kpi_raw["fastest_idx"] or 100.0, years_span) if years_span > 0 else 0.0

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
            "value": f"{yoy_val:+.2f}%" if yoy_val is not None else "—",
            "unit": "เทียบปีก่อน" if yoy_val is not None else "(ปีฐาน)",
            "delta": None,
        },
        {
            "id": "cagr",
            "label": f"CAGR 2554→{year}",
            "value": round(cagr_val, 2) if cagr_val is not None else "—",
            "unit": "%/ปี" if cagr_val is not None else "(ปีฐาน)",
            "delta": {
                "value": round(abs(cagr_val), 2),
                "unit": "%",
                "vs": "2554",
                "direction": "up" if (cagr_val or 0) >= 0 else "down",
            } if (cagr_val is not None and not is_base_year) else None,
        },
        {
            "id": "fastest",
            "label": "ภาคที่โตเร็วสุด",
            "value": kpi_raw["fastest_region"] or "—",
            "unit": f"({fastest_cagr:.2f}%/ปี)" if years_span > 0 else "",
            "delta": None,
        },
    ]

    # Chart 2A: Choropleth
    if f.metric == "yoy":
        choro_data = db.query_tab2_choropleth_yoy(year, pt)
        metric_label = "YoY"
        unit_label = "%"
    elif f.metric == "cagr":
        choro_data = db.query_tab2_choropleth_cagr(year, pt)
        metric_label = f"CAGR (2554→{year})"
        unit_label = "%/ปี"
    else:
        choro_data = db.query_tab2_choropleth(year, pt)
        metric_label = "ดัชนีราคาบ้าน"
        unit_label = "(2554=100)"

    fig_2a = fig_tab2.fig_choropleth(
        choro_data,
        selected_region=region,
        theme=theme,
        metric_label=metric_label,
        unit=unit_label,
        year=year,
        pt_name=pt_name,
    )

    empty_notice = None
    if pt == 3 and region in (3, 4):
        empty_notice = "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ในฐานข้อมูล ธปท."

    # Chart 2B: Trend
    if grain == "monthly":
        trend_data = db.query_tab2_trend_monthly(pt, 2554, 2568)
        fig_2b = fig_tab2.fig_trend(trend_data, selected_region=region, theme=theme, is_monthly=True)
    else:
        trend_data = db.query_tab2_trend_annual(pt, 2554, 2568)
        fig_2b = fig_tab2.fig_trend(trend_data, selected_region=region, theme=theme, is_monthly=False)

    # Chart 2C: Heatmap YoY
    heatmap_data = db.query_tab2_heatmap(pt, 2554, 2568)
    fig_2c = fig_tab2.fig_heatmap(heatmap_data, selected_region=region, selected_year=year, theme=theme)

    return {
        "filters": f.to_dict(),
        "status_line": status_line,
        "kpis": kpis,
        "charts": {
            "choropleth": {
                "figure": fig_2a,
                "read_guide": "สีเข้ม = ดัชนีสูง · สีเทา = ไม่มีข้อมูล · คลิกภาคเพื่อกรอง",
                "note": "ที่มา: ธปท. (EC_EI_008_S4 ฐาน 2554=100)",
                "empty": empty_notice,
            },
            "trend": {
                "figure": fig_2b,
                "read_guide": "คลิกจุดเพื่อเลือกปี · คลิกเส้นเพื่อเลือกภาค",
                "note": "เฉลี่ยเคลื่อนที่ 3 เดือน · ม.ค. 2566 เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ",
                "empty": empty_notice,
            },
            "heatmap": {
                "figure": fig_2c,
                "read_guide": "ฟ้า = ติดลบ · ส้ม = ขยายตัว · คลิกช่องเพื่อเลือกภาคและปีพร้อมกัน",
                "note": "ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท",
                "empty": empty_notice,
            },
        },
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
    cagr_view = f.cagr_view

    region_info = next((r for r in meta["regions"] if r["region_id"] == region), None) if region is not None else None
    scope = region_info["short_th"] if region_info else "ทั่วประเทศ"
    pt_info = next((p for p in meta["property_types"] if p["property_type_id"] == pt), None)
    pt_name = pt_info["name_th"] if pt_info else "รวมทุกประเภทที่อยู่อาศัย"

    status_line = f"{scope} · {pt_name} · {y0}–{y1}"

    # Hero Data: Price-to-Income Ratio
    pti_data = db.query_tab3_price_to_income(pt, y0, y1)

    # Rebase so that start year y0 = 100
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
            new_pti = 100.0 * (new_hpi / 100.0) / (new_inc / 100.0) if new_inc else 100.0
            rebased_data.append({
                **r,
                "income_index": new_inc,
                "hpi_index": new_hpi,
                "price_to_income_index": new_pti,
            })
    pti_data = rebased_data

    target_rid = region if region is not None else 0
    target_row = next((r for r in pti_data if r["region_id"] == target_rid and r["year_be"] == y1), None)
    pti_val = target_row["price_to_income_index"] if target_row else 100.0
    hpi_end = target_row["hpi_index"] if target_row else 100.0
    inc_end = target_row["income_index"] if target_row else 100.0

    # Status badge (10.6)
    if abs(pti_val - 100.0) <= 0.5:
        status_text = "ใกล้เดิม"
        status_dir = "neutral"
    elif pti_val > 100.0:
        status_text = "ซื้อยากขึ้น"
        status_dir = "harder"
    else:
        status_text = "ซื้อง่ายขึ้น"
        status_dir = "easier"

    # CAGRs over window y0 -> y1
    income_cagr_rows = db.query_tab3_cagr_income(y0, y1)
    hpi_cagr_rows = db.query_tab3_cagr_hpi(pt, y0, y1)

    inc_row = next((r for r in income_cagr_rows if r["region_id"] == target_rid), None)
    hpi_row = next((r for r in hpi_cagr_rows if r["region_id"] == target_rid), None)

    inc_cagr = cagr_pct(inc_row["v0"], inc_row["v1"], inc_row["years"]) if inc_row else 0.0
    hpi_cagr = cagr_pct(hpi_row["v0"], hpi_row["v1"], hpi_row["years"]) if hpi_row else 0.0
    gap = round((hpi_cagr or 0) - (inc_cagr or 0), 2)
    gap_sign = "+" if gap > 0 else ""

    kpis = [
        {
            "id": "pti",
            "label": f"ดัชนีราคา ÷ รายได้ ปี {y1}",
            "value": round(pti_val, 1),
            "unit": f"({status_text})",
            "subline": f"ราคาบ้าน {hpi_end:.1f} ÷ รายได้ {inc_end:.1f}",
            "status": status_dir,
            "delta": None,
        },
        {
            "id": "inc_cagr",
            "label": f"CAGR รายได้ {y0}→{y1}",
            "value": round(inc_cagr, 2) if inc_cagr is not None else "—",
            "unit": "%/ปี",
            "delta": None,
        },
        {
            "id": "hpi_cagr",
            "label": f"CAGR ราคาบ้าน {y0}→{y1}",
            "value": round(hpi_cagr, 2) if hpi_cagr is not None else "—",
            "unit": "%/ปี",
            "delta": None,
        },
        {
            "id": "gap",
            "label": f"ช่องว่าง CAGR (บ้าน − รายได้)",
            "value": f"{gap_sign}{gap:.2f}",
            "unit": "จุดเปอร์เซ็นต์",
            "delta": None,
        },
    ]

    # Chart 3A: Hero ratio line (Graph 1)
    fig_hero = fig_tab3.fig_price_to_income_hero(
        pti_data,
        y0=y0,
        y1=y1,
        selected_region=region,
        theme=theme,
    )

    # Chart 3B: CAGR Comparison (Graph 2 with toggle: summary vs by_type)
    cagr_note = "คำนวณจากอัตราเติบโตเฉลี่ยสะสมต่อปี (CAGR)"
    types_data = db.query_tab3_cagr_hpi_by_type(target_rid, y0, y1)
    if cagr_view == "by_type" and target_rid in (3, 4):
        cagr_note = "ภาคนี้มีเฉพาะบ้านเดี่ยว ดัชนีรวมเท่ากับบ้านเดี่ยว ไม่มีข้อมูลทาวน์เฮ้าส์ (Q-H1)"

    fig_cagr = fig_tab3.fig_cagr_comparison(
        income_cagr=inc_cagr or 0.0,
        hpi_cagr=hpi_cagr or 0.0,
        types_data=types_data,
        income_rows=income_cagr_rows,
        hpi_rows=hpi_cagr_rows,
        view_mode=cagr_view or "summary",
        scope_name=scope,
        selected_pt=pt,
        theme=theme,
    )

    # Chart 3C: Affordability Gap Area (Graph 3)
    fig_gap_area = fig_tab3.fig_affordability_gap_area(
        pti_data,
        selected_region=region,
        theme=theme,
    )

    # Chart 3D: Growth Balance Scatter Plot (Graph 4)
    fig_scatter = fig_tab3.fig_growth_balance_scatter(
        income_rows=income_cagr_rows,
        hpi_rows=hpi_cagr_rows,
        selected_region=region,
        theme=theme,
    )

    return {
        "filters": f.to_dict(),
        "status_line": status_line,
        "kpis": kpis,
        "charts": {
            "hero": {
                "figure": fig_hero,
                "read_guide": "เส้นสูงขึ้น = ราคาบ้านโตเร็วกว่ารายได้ (ซื้อยากขึ้น) · เส้นต่ำลง = ซื้อง่ายขึ้น",
                "note": "ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ระดับราคาบ้านเป็นบาท · ตัดผลเงินเฟ้อส่วนใหญ่ออกไปแล้ว",
                "empty": None,
            },
            "cagr": {
                "figure": fig_cagr,
                "read_guide": "แท่งเปรียบเทียบอัตราการเติบโตเฉลี่ยสะสมต่อปี (CAGR)",
                "note": cagr_note,
                "empty": None,
            },
            "gap_area": {
                "figure": fig_gap_area,
                "read_guide": "พื้นที่สีแดง = ราคาบ้านพุ่งแซงรายได้ (ซื้อยากขึ้น) · พื้นที่สีเขียว = รายได้โตแซง (ซื้อง่ายขึ้น)",
                "note": "ช่องว่างความเหลื่อมล้ำ = ดัชนีราคาบ้าน − ดัชนีรายได้",
                "empty": None,
            },
            "scatter": {
                "figure": fig_scatter,
                "read_guide": "ใต้เส้นประ = รายได้โตไวกว่า · เหนือเส้นประ = ราคาบ้านแซง · ซ้ายบน = เสี่ยงฟองสบู่",
                "note": "คลิกที่จุดเพื่อเลือกดูภาคนั้นๆ · เส้นประทแยงมุม 45 องศาคือระดับที่รายได้และราคาบ้านเติบโตเท่ากัน",
                "empty": None,
            },
        },
        "notes": [
            "รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี) ไม่เติมค่าปีที่ขาด · ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ระดับราคาบ้านเป็นบาท",
            "นิยามกทม.+ปริมณฑลของ สสช. กับ ธปท. อาจไม่ตรงกัน",
            "อัตราส่วนของสองดัชนีตัดผลเงินเฟ้อส่วนใหญ่ออกไปแล้ว แต่ตอบเรื่อง 'รายได้จริงโตหรือไม่' ไม่ได้",
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
    cagr_view: Optional[str] = Query(None),
    real: Optional[bool] = Query(None),
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
            cagr_view=cagr_view,
            real=real,
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


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = Path(__file__).resolve().parent / "templates" / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Income × Housing Dashboard</h1>")
