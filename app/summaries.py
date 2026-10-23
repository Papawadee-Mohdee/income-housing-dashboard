"""Thai-language auto-summary templates for each chart.

Each function takes chart data and returns a summary dict:
  {"headline": str, "bullets": list[str], "caution": str|None}

Templates use fixed Thai text with f-string placeholders — no LLM, fully deterministic.
"""
from __future__ import annotations

from app.metrics import cagr_pct, format_number, pct_change


def _fmt(v: float, d: int = 0) -> str:
    return format_number(v, d)


def _sign(v: float) -> str:
    return "เพิ่ม" if v >= 0 else "ลด"


# ──────────────────────────────────────── Tab 1

def summary_1a(year: int, data: list[dict]) -> dict:
    """Choropleth summary — income by region."""
    if not data:
        return {"headline": "", "bullets": [], "caution": None}
    top = max(data, key=lambda r: r["value"])
    bottom = min(data, key=lambda r: r["value"])
    ratio = round(top["value"] / bottom["value"], 2) if bottom["value"] else 0
    return {
        "headline": f"ปี {year} {top['short_th']} มีรายได้สูงสุด {_fmt(top['value'])} บาท/เดือน ส่วน{bottom['short_th']}ต่ำสุด {_fmt(bottom['value'])} บาท (ต่างกัน {ratio:.2f} เท่า)",
        "bullets": [
            f"{r['short_th']}: {_fmt(r['value'])} บาท/เดือน" for r in data
        ],
        "caution": None,
    }


def summary_1b(year: int, treemap_data: list[dict], scope: str) -> dict:
    """Treemap summary — income sources."""
    if not treemap_data:
        return {"headline": "", "bullets": [], "caution": None}
    work = [r for r in treemap_data if "ทำงาน" in r["source_name_th"]]
    transfer = [r for r in treemap_data if "โอน" in r["source_name_th"] or "สวัสดิการ" in r["source_name_th"]]
    work_pct = sum(r["share_pct"] for r in work) if work else 0
    transfer_pct = sum(r["share_pct"] for r in transfer) if transfer else 0
    # region with highest transfer dependency
    by_region = {}
    for r in treemap_data:
        if "โอน" in r["source_name_th"] or "สวัสดิการ" in r["source_name_th"]:
            by_region[r["region"]] = by_region.get(r["region"], 0) + r["share_pct"]
    max_transfer = max(by_region.items(), key=lambda x: x[1]) if by_region else (scope, transfer_pct)

    return {
        "headline": f"ปี {year} {scope} รายได้มาจากการทำงาน {work_pct:.1f}% เงินโอน/สวัสดิการ {transfer_pct:.1f}%",
        "bullets": [
            f"{max_transfer[0]}พึ่งเงินโอนมากสุด {max_transfer[1]:.1f}%",
        ],
        "caution": None,
    }


def summary_1c(y0: int, y1: int, scope: str, trend_data: list[dict]) -> dict:
    """Trend summary — income over time."""
    if not trend_data:
        return {"headline": "", "bullets": [], "caution": None}
    # Group by region
    by_region: dict[str, list] = {}
    for r in trend_data:
        by_region.setdefault(r["short_th"], []).append(r)
    # National totals
    national = by_region.get("ทั่วประเทศ", [])
    if national:
        first, last = national[0], national[-1]
        pct = pct_change(first["monthly_income"], last["monthly_income"])
        c = cagr_pct(first["monthly_income"], last["monthly_income"], y1 - y0)
        direction = _sign(pct) if pct else "ไม่เปลี่ยน"
    else:
        pct, c, direction = 0, 0, ""
    # fastest region
    cagrs = {}
    for name, rows in by_region.items():
        if rows[0].get("is_national"):
            continue
        c_val = cagr_pct(rows[0]["monthly_income"], rows[-1]["monthly_income"], y1 - y0)
        if c_val is not None:
            cagrs[name] = c_val
    fastest = max(cagrs.items(), key=lambda x: x[1]) if cagrs else None
    slowest = min(cagrs.items(), key=lambda x: x[1]) if cagrs else None

    bullets = []
    if fastest:
        bullets.append(f"{fastest[0]}โตเร็วสุด {fastest[1]:.2f}%/ปี")
    if slowest and slowest[1] < 0:
        bullets.append(f"{slowest[0]}ติดลบ {slowest[1]:.2f}%/ปี")

    return {
        "headline": f"{y0}→{y1} รายได้{scope}{direction} {abs(pct) if pct else 0:.1f}% (CAGR {c:.2f}%/ปี)",
        "bullets": bullets,
        "caution": "รายได้มีเฉพาะปีรอบสำรวจ ไม่ interpolate ปีที่ขาด · ตัวเลขเป็นราคาตามปี (nominal)",
    }


def summary_1d(year: int, heatmap_data: list[dict]) -> dict:
    """Heatmap summary — urban-rural gap."""
    year_data = [r for r in heatmap_data if r["year_be"] == year]
    if not year_data:
        return {"headline": "", "bullets": [], "caution": None}
    top = max(year_data, key=lambda r: r["gap_pct"])
    bottom = min(year_data, key=lambda r: r["gap_pct"])
    return {
        "headline": f"ปี {year} ช่องว่างเมือง-ชนบทสูงสุดที่{top['short_th']} {top['gap_pct']:.1f}% ต่ำสุดที่{bottom['short_th']} {bottom['gap_pct']:.1f}%",
        "bullets": [f"{r['short_th']}: {r['gap_pct']:.1f}%" for r in year_data],
        "caution": "กทม.+ปริมณฑล อาจมีความแตกต่างของคำนิยาม \"ในเขต/นอกเขต\" กับภาคอื่น",
    }


# ──────────────────────────────────────── Tab 2

def summary_2a(year: int, pt_name: str, scope: str, data: list[dict],
               base_data: list[dict] | None = None) -> dict:
    """Choropleth / trend summary — house price index."""
    if not data:
        return {"headline": "", "bullets": [], "caution": None}
    # For national data
    national = [r for r in data if r.get("region_id") == 0]
    idx = national[0]["value"] if national else data[0]["value"]
    pct = round(idx - 100, 1)
    # CAGR from base
    years_span = year - 2554
    c = cagr_pct(100, idx, years_span) if years_span > 0 else 0
    fastest = max([r for r in data if r.get("region_id", 0) > 0], key=lambda r: r["value"]) if len(data) > 1 else None
    slowest = min([r for r in data if r.get("region_id", 0) > 0], key=lambda r: r["value"]) if len(data) > 1 else None

    bullets = []
    if fastest:
        fc = cagr_pct(100, fastest["value"], years_span) if years_span > 0 else 0
        bullets.append(f"{fastest['short_th']}โตเร็วสุด {fc:.2f}%/ปี")
    if slowest:
        sc = cagr_pct(100, slowest["value"], years_span) if years_span > 0 else 0
        bullets.append(f"{slowest['short_th']}ช้าสุด {sc:.2f}%/ปี")

    return {
        "headline": f"{year} ดัชนีราคาบ้าน{pt_name}{scope} {idx:.1f} (สูงกว่าปี 2554 {pct:.1f}%) โตเฉลี่ย {c:.2f}%/ปี",
        "bullets": bullets,
        "caution": "ดัชนีผ่านการเฉลี่ยเคลื่อนที่ 3 เดือน · ตั้งแต่ ม.ค. 2566 เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ",
    }


def summary_2c(year: int, heatmap_data: list[dict]) -> dict:
    """Heatmap summary — YoY changes."""
    year_data = [r for r in heatmap_data if r["year_be"] == year]
    if not year_data:
        return {"headline": "", "bullets": [], "caution": None}
    national = [r for r in year_data if r.get("is_national")]
    yoy = national[0]["yoy_pct"] if national else year_data[0]["yoy_pct"]
    top = max(year_data, key=lambda r: r["yoy_pct"])
    return {
        "headline": f"ปี {year} ราคาบ้านเพิ่มจากปีก่อน {yoy:.1f}% (ทั้งประเทศ)",
        "bullets": [f"สูงสุด{top['short_th']} {top['yoy_pct']:.1f}%"],
        "caution": "ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคา ห้ามเรียงอันดับว่าภาคใดแพงที่สุด",
    }


# ──────────────────────────────────────── Tab 3

def summary_3a(y0: int, y1: int, scope: str, pti_data: list[dict]) -> dict:
    """Price-to-income index trend summary."""
    if not pti_data:
        return {"headline": "", "bullets": [], "caution": None}
    # Get final year national data
    final = [r for r in pti_data if r["year_be"] == y1]
    national = [r for r in final if r.get("is_national")]
    pti = national[0]["price_to_income_index"] if national else (final[0]["price_to_income_index"] if final else 100)
    pct = round(pti - 100, 0)
    difficulty = "ยากขึ้น" if pti > 100 else "ง่ายขึ้น"
    regions_final = [r for r in final if not r.get("is_national")]
    hardest = max(regions_final, key=lambda r: r["price_to_income_index"]) if regions_final else None
    easiest = min(regions_final, key=lambda r: r["price_to_income_index"]) if regions_final else None

    bullets = []
    if hardest:
        bullets.append(f"ยากขึ้นมากสุดที่{hardest['short_th']} (ดัชนี {hardest['price_to_income_index']:.1f})")
    if easiest:
        bullets.append(f"น้อยสุดที่{easiest['short_th']} ({easiest['price_to_income_index']:.1f})")

    return {
        "headline": f"ปี {y1} ราคาบ้านโตเร็วกว่ารายได้ {abs(pct):.0f}% เทียบ {y0} ({scope}) → {difficulty}",
        "bullets": bullets,
        "caution": "รายได้มีเฉพาะปีรอบสำรวจ ไม่ interpolate · ทั้งสองชุดเป็นราคาตามปี · นิยาม กทม.+ปริมณฑล ของ สสช. กับ ธปท. อาจไม่ตรงกัน",
    }


def summary_3c(income_cagr: float, hpi_cagr: float) -> dict:
    """CAGR comparison summary."""
    gap = round(hpi_cagr - income_cagr, 2)
    return {
        "headline": f"ราคาบ้านโต {hpi_cagr:.2f}%/ปี เทียบรายได้ {income_cagr:.2f}%/ปี ช่องว่าง {gap:.2f} จุด",
        "bullets": [],
        "caution": None,
    }


def summary_3d(region_name: str, income_cagr: float, hpi_cagr: float) -> dict:
    """CAGR by region/type summary."""
    income_desc = "ติดลบ " if income_cagr < 0 else ""
    return {
        "headline": f"{region_name}: รายได้{income_desc}{income_cagr:.2f}%/ปี ขณะที่ราคาบ้านโต {hpi_cagr:.2f}%/ปี",
        "bullets": [],
        "caution": None,
    }


# ──────────────────────────────────────── Tab-level insights

def tab1_insights(kpi: dict, choropleth_summary: dict, trend_summary: dict, heatmap_summary: dict) -> list[str]:
    """Combine summaries into 3-5 insights for the tab-level Insights panel."""
    insights = []
    if choropleth_summary.get("headline"):
        insights.append(choropleth_summary["headline"])
    if trend_summary.get("headline"):
        insights.append(trend_summary["headline"])
    if heatmap_summary.get("headline"):
        insights.append(heatmap_summary["headline"])
    return insights[:5]


def tab2_insights(kpi: dict, choropleth_summary: dict, heatmap_summary: dict) -> list[str]:
    insights = []
    if choropleth_summary.get("headline"):
        insights.append(choropleth_summary["headline"])
    if heatmap_summary.get("headline"):
        insights.append(heatmap_summary["headline"])
    return insights[:5]


def tab3_insights(pti_summary: dict, cagr_summary: dict) -> list[str]:
    insights = []
    if pti_summary.get("headline"):
        insights.append(pti_summary["headline"])
    if cagr_summary.get("headline"):
        insights.append(cagr_summary["headline"])
    return insights[:5]
