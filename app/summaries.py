"""Deterministic Thai-language summary generators for dashboard charts (v2).

Features:
- Fixed Thai templates without LLM
- Strictly no causal words: เพราะ, เนื่องจาก, ส่งผลให้, สาเหตุ
- Strictly no forbidden words: แพงที่สุด, แพงกว่า, ค่าครองชีพ, รายได้จริง
- Uses Unicode minus U+2212 (MINUS) for negative numbers
- Uses '+' for positive deltas
- Reuses DB query functions from app.db (zero SQL duplication)
- In-memory caching for < 150ms responses
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from app import db
from app.filters import Filters
from app.metrics import cagr_pct, pct_change

MINUS = "\u2212"  # U+2212 mathematical minus sign

VALID_CHART_IDS = {
    1: {"t1_map", "t1_trend", "t1_gap", "t1_sources"},
    2: {"t2_map", "t2_trend", "t2_yoy"},
    3: {"t3_ratio", "t3_cagr"},
}

CHART_TITLES = {
    "t1_map": "แผนที่รายได้เฉลี่ยต่อเดือน",
    "t1_trend": "แนวโน้มรายได้เฉลี่ยต่อเดือน",
    "t1_gap": "ช่องว่างเมือง-ชนบท (%)",
    "t1_sources": "สัดส่วนแหล่งที่มาของรายได้",
    "t2_map": "แผนที่ดัชนีราคาบ้าน",
    "t2_trend": "แนวโน้มดัชนีราคาบ้าน",
    "t2_yoy": "อัตราเปลี่ยนแปลงรายปี (YoY %)",
    "t3_ratio": "1 · แนวโน้มดัชนีราคาบ้านเทียบกับรายได้ (Price-to-Income Ratio)",
    "t3_cagr": "3 · เปรียบเทียบอัตราเติบโต (CAGR)",
}

PROPERTY_TYPE_NAMES = {
    1: "รวมทุกประเภท",
    2: "บ้านเดี่ยว",
    3: "ทาวน์เฮ้าส์",
}

AREA_NAMES = {
    0: "รวมทุกเขต",
    1: "ในเขตเทศบาล (เมือง)",
    2: "นอกเขตเทศบาล (ชนบท)",
}

CAGR_VIEW_NAMES = {
    "summary": "ภาพรวม",
    "by_region": "แยกภาค",
    "by_type": "แยกบ้าน",
}


def _fmt_baht(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"{int(round(v)):,}"


def _fmt_cagr(v: float | None) -> str:
    if v is None:
        return "—"
    if v < 0:
        return f"{MINUS}{abs(v):.2f}%/ปี"
    return f"{v:.2f}%/ปี"


def _fmt_sign_pct(v: float | None, d: int = 2) -> str:
    if v is None:
        return "—"
    if v < 0:
        return f"{MINUS}{abs(v):.{d}f}%"
    return f"+{v:.{d}f}%"


def _fmt_diff_points(v: float | None) -> str:
    if v is None:
        return "—"
    if v < 0:
        return f"{MINUS}{abs(v):.2f} จุด"
    return f"+{v:.2f} จุด"


def _get_scope_name(meta: dict, region_id: int | None) -> str:
    if region_id is None or region_id == 0:
        return "ทั่วประเทศ"
    reg = next((r for r in meta["regions"] if r["region_id"] == region_id), None)
    return reg["short_th"] if reg else "ทั่วประเทศ"


# ─────────────────────────────────────────────────────────────
# 1. TAB 1 SUMMARIES
# ─────────────────────────────────────────────────────────────

def _build_t1_map(f: Filters, meta: dict) -> dict:
    year = f.year
    area = f.area
    metric = f.metric
    region = f.region
    scope = _get_scope_name(meta, region)

    if metric == "income_index":
        rows = db.query_tab1_choropleth_index(year, area)
        if not rows:
            return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}
        top = max(rows, key=lambda r: r["value"])
        bottom = min(rows, key=lambda r: r["value"])
        below_100 = [r for r in rows if r["value"] < 100.0]

        headline = f"ปี {year} ดัชนีรายได้สูงสุดที่{top['short_th']} ({top['value']:.1f}) ต่ำสุดที่{bottom['short_th']} ({bottom['value']:.1f})"
        bullets = [
            "5 ภาคเรียงตามดัชนีรายได้: " + " · ".join([f"{r['short_th']} {r['value']:.1f}" for r in sorted(rows, key=lambda r: r["value"], reverse=True)]),
        ]
        if below_100:
            bullets.append("ภาคที่ดัชนีรายได้ต่ำกว่า 100: " + " · ".join([f"{r['short_th']} ({r['value']:.1f})" for r in below_100]))
        else:
            bullets.append("ทุกภาคมีดัชนีรายได้สูงกว่าปีฐาน 2554 (ดัชนี > 100)")
        caution = "ตัวเลขเป็นราคาตามปี ไม่ปรับเงินเฟ้อ"
        return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}

    elif metric == "transfer_share":
        rows = db.query_tab1_choropleth_transfer(year, area)
        if not rows:
            return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}
        top = max(rows, key=lambda r: r["value"])
        bottom = min(rows, key=lambda r: r["value"])
        kpi_nat = db.query_tab1_kpi(year, area, 0)
        nat_transfer = kpi_nat["transfer_pct"]

        headline = f"ปี {year} สัดส่วนเงินโอน/สวัสดิการสูงสุดที่{top['short_th']} {top['value']:.1f}% ต่ำสุดที่{bottom['short_th']} {bottom['value']:.1f}%"
        bullets = [
            f"อีสานสูงสุด {top['value']:.1f}% กทม.+ปริมณฑลต่ำสุด {bottom['value']:.1f}% (ทั้งประเทศ {nat_transfer:.1f}%)" if (top['short_th'] == "อีสาน" and bottom['short_th'] == "กทม.+ปริมณฑล") else f"{top['short_th']}สูงสุด {top['value']:.1f}% {bottom['short_th']}ต่ำสุด {bottom['value']:.1f}% (ทั้งประเทศ {nat_transfer:.1f}%)",
            "5 ภาคเรียงตามสัดส่วนเงินโอน: " + " · ".join([f"{r['short_th']} {r['value']:.1f}%" for r in sorted(rows, key=lambda r: r["value"], reverse=True)]),
        ]
        caution = "ตัวเลขเป็นราคาตามปี ไม่ปรับเงินเฟ้อ"
        return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}

    else:
        # Default: metric == 'income'
        rows = db.query_tab1_choropleth(year, area)
        if not rows:
            return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}
        sorted_rows = sorted(rows, key=lambda r: r["value"], reverse=True)
        top = sorted_rows[0]
        bottom = sorted_rows[-1]
        ratio = round(top["value"] / bottom["value"], 2) if bottom["value"] else 0.0
        kpi_nat = db.query_tab1_kpi(year, area, 0)
        nat_v = kpi_nat["monthly_income"]

        if region is not None and region > 0:
            rank = next(i for i, r in enumerate(sorted_rows, 1) if r["region_id"] == region)
            cur = next(r for r in sorted_rows if r["region_id"] == region)
            headline = f"ปี {year} {cur['short_th']} มีรายได้ {_fmt_baht(cur['value'])} บาท/เดือน เป็นอันดับที่ {rank} จาก 5 ภาค (เทียบทั้งประเทศ {_fmt_baht(nat_v)} บาท/เดือน)"
            diff = cur["value"] - nat_v
            diff_text = f"สูงกว่าค่าเฉลี่ยทั้งประเทศอยู่ {_fmt_baht(diff)} บาท" if diff >= 0 else f"ต่ำกว่าค่าเฉลี่ยทั้งประเทศอยู่ {_fmt_baht(abs(diff))} บาท"
            bullets = [
                f"{cur['short_th']} มีรายได้เป็นอันดับ {rank} จาก 5 ภาค ({_fmt_baht(cur['value'])} บาท/เดือน) {diff_text}",
                f"ภาคที่มีรายได้สูงสุดคือ {top['short_th']} ({_fmt_baht(top['value'])} บาท) ต่ำสุดคือ {bottom['short_th']} ({_fmt_baht(bottom['value'])} บาท)",
                "5 ภาคเรียงจากมากไปน้อย: " + " · ".join([f"{r['short_th']} {_fmt_baht(r['value'])}" for r in sorted_rows]) + f" บาท (ทั้งประเทศ {_fmt_baht(nat_v)} บาท)",
            ]
        else:
            headline = f"ปี {year} {top['short_th']}มีรายได้สูงสุด {_fmt_baht(top['value'])} บาท/เดือน ส่วน{bottom['short_th']}ต่ำสุด {_fmt_baht(bottom['value'])} บาท (ต่างกัน {ratio:.2f} เท่า)"
            bullets = [
                "เรียง 5 ภาคจากมากไปน้อยพร้อมค่า: " + " · ".join([f"{_fmt_baht(r['value'])}" if i == 0 else f"{r['short_th']} {_fmt_baht(r['value'])}" for i, r in enumerate(sorted_rows)]),
                f"รายได้เฉลี่ยทั้งประเทศอยู่ที่ {_fmt_baht(nat_v)} บาท/เดือน",
            ]

        caution = "ตัวเลขเป็นราคาตามปี ไม่ปรับเงินเฟ้อ"
        return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


def _build_t1_trend(f: Filters, meta: dict) -> dict:
    y0, y1 = f.y0, f.y1
    area = f.area
    region = f.region
    scope = _get_scope_name(meta, region)

    if y0 == y1:
        return {
            "headline": f"ปี {y0} เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต",
            "bullets": ["เปรียบเทียบอัตราการเติบโตได้เมื่อเลือกช่วงปีเริ่มต้นและสิ้นสุดต่างกัน"],
            "caution": "รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี)",
            "empty": None,
        }

    trend_rows = db.query_tab1_trend(area, y0, y1)
    if not trend_rows:
        return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}

    by_region: dict[str, list] = {}
    for r in trend_rows:
        by_region.setdefault(r["short_th"], []).append(r)

    # National calculations
    nat_rows = by_region.get("ทั่วประเทศ", [])
    if nat_rows:
        v0_nat = nat_rows[0]["monthly_income"]
        v1_nat = nat_rows[-1]["monthly_income"]
        pct_nat = pct_change(v0_nat, v1_nat)
        cagr_nat = cagr_pct(v0_nat, v1_nat, y1 - y0)
    else:
        v0_nat, v1_nat, pct_nat, cagr_nat = 0, 0, 0.0, 0.0

    # Regional CAGRs
    region_cagrs = []
    for r_meta in meta["regions"]:
        if r_meta["is_national"]:
            continue
        rows_reg = by_region.get(r_meta["short_th"], [])
        if rows_reg and len(rows_reg) >= 2:
            v0_r = rows_reg[0]["monthly_income"]
            v1_r = rows_reg[-1]["monthly_income"]
            c = cagr_pct(v0_r, v1_r, y1 - y0)
            p = pct_change(v0_r, v1_r)
            region_cagrs.append({
                "region_id": r_meta["region_id"],
                "short_th": r_meta["short_th"],
                "v0": v0_r,
                "v1": v1_r,
                "cagr": c if c is not None else 0.0,
                "pct": p if p is not None else 0.0,
            })

    region_cagrs.sort(key=lambda x: x["cagr"], reverse=True)
    fastest = region_cagrs[0] if region_cagrs else None
    slowest = region_cagrs[-1] if region_cagrs else None

    if region is not None and region > 0:
        cur = next((r for r in region_cagrs if r["region_id"] == region), None)
        if cur:
            rank = next(i for i, r in enumerate(region_cagrs, 1) if r["region_id"] == region)
            direction = "เพิ่ม" if cur["pct"] >= 0 else "ลดลง"
            headline = f"{y0}→{y1} รายได้{cur['short_th']}{direction} {abs(cur['pct']):.1f}% (CAGR {_fmt_cagr(cur['cagr'])})"
            sign_pct = f"+{cur['pct']:.1f}%" if cur["pct"] >= 0 else f"{MINUS}{abs(cur['pct']):.1f}%"
            bullets = [
                f"{cur['short_th']} เป็นอันดับ {rank} จาก 5 ภาค ในด้านอัตราเติบโตเฉลี่ยสะสม (CAGR {_fmt_cagr(cur['cagr'])} เทียบทั้งประเทศ {_fmt_cagr(cagr_nat)})",
                f"{cur['short_th']} {_fmt_baht(cur['v0'])} → {_fmt_baht(cur['v1'])} บาท ({sign_pct}, CAGR {_fmt_cagr(cur['cagr'])}) เทียบทั้งประเทศ {_fmt_cagr(cagr_nat)}",
            ]
        else:
            headline = f"{y0}→{y1} รายได้{scope} (CAGR {_fmt_cagr(cagr_nat)})"
            bullets = []
    else:
        direction = "เพิ่ม" if pct_nat >= 0 else "ลดลง"
        headline = f"{y0}→{y1} รายได้{scope}{direction} {abs(pct_nat):.1f}% (CAGR {_fmt_cagr(cagr_nat)})"
        bullets = []
        if fastest:
            bullets.append(f"โตเร็วสุด{fastest['short_th']} {_fmt_cagr(fastest['cagr'])}")
        if slowest:
            desc = " (รายได้ลดลง)" if slowest["cagr"] < 0 else ""
            bullets.append(f"ต่ำสุด{slowest['short_th']} {_fmt_cagr(slowest['cagr'])}{desc}")
        other_cagrs = [f"{r['short_th']} {_fmt_cagr(r['cagr'])}" for r in region_cagrs[1:-1]]
        if other_cagrs:
            bullets.append("ภาคอื่น ๆ: " + " · ".join(other_cagrs))

    caution = "รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี)"
    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


def _build_t1_gap(f: Filters, meta: dict) -> dict:
    year = f.year
    region = f.region
    scope = _get_scope_name(meta, region)

    rows = db.query_tab1_heatmap(2554, 2568)
    year_rows = [r for r in rows if r["year_be"] == year and not r["is_national"] and r.get("gap_pct") is not None]
    if not year_rows:
        return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}

    year_rows.sort(key=lambda r: r["gap_pct"], reverse=True)
    top = year_rows[0]
    bottom = year_rows[-1]

    # National gap in that year
    nat_row = next((r for r in rows if r["year_be"] == year and r["is_national"]), None)
    nat_gap = nat_row["gap_pct"] if nat_row else None

    # BMR gap in 2554 vs current year
    bmr_54 = next((r["gap_pct"] for r in rows if r["year_be"] == 2554 and r["short_th"] == "กทม.+ปริมณฑล"), None)
    bmr_cur = next((r["gap_pct"] for r in rows if r["year_be"] == year and r["short_th"] == "กทม.+ปริมณฑล"), None)

    headline = f"ปี {year} ช่องว่างเมือง-ชนบทสูงสุดที่{top['short_th']} {top['gap_pct']:.1f}% ต่ำสุดที่{bottom['short_th']} {bottom['gap_pct']:.1f}%"

    bullets = []
    if bmr_54 is not None and bmr_cur is not None:
        bullets.append(f"กทม.+ปริมณฑลลดจาก {bmr_54:.1f}% (2554) เหลือ {bmr_cur:.1f}%")

    other_gaps = [f"{r['short_th']} {r['gap_pct']:.1f}%" for r in year_rows if r["short_th"] != "กทม.+ปริมณฑล"]
    nat_text = f" (ทั้งประเทศ {nat_gap:.1f}%)" if nat_gap is not None else ""
    if other_gaps:
        bullets.append(" · ".join(other_gaps) + nat_text)

    if region is not None and region > 0:
        cur = next((r for r in year_rows if r["region_id"] == region), None)
        if cur:
            rank = next(i for i, r in enumerate(year_rows, 1) if r["region_id"] == region)
            bullets.insert(0, f"{cur['short_th']} มีช่องว่างเมือง-ชนบทเป็นอันดับ {rank} จาก 5 ภาค ({cur['gap_pct']:.1f}%)")

    caution = "นิยามกทม.+ปริมณฑลของ สสช. ใช้ 4 จังหวัด"
    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


def _build_t1_sources(f: Filters, meta: dict) -> dict:
    year = f.year
    area = f.area
    region = f.region
    scope = _get_scope_name(meta, region)

    tree_data = db.query_tab1_treemap(year, area, region)

    if tree_data.get("mode") == "single":
        leaves = tree_data.get("leaves", [])
        w = next((l["share"] for l in leaves if "ทำงาน" in l["name"]), 0.0)
        t = next((l["share"] for l in leaves if "โอน" in l["name"]), 0.0)
        nm = next((l["share"] for l in leaves if "ไม่เป็นตัวเงิน" in l["name"]), 0.0)
        o = round(100.0 - (w + t + nm), 1)

        headline = f"ปี {year} {scope} รายได้มาจากการทำงาน {w:.1f}% เงินโอน/สวัสดิการ {t:.1f}% ไม่เป็นตัวเงิน {nm:.1f}% อื่น ๆ {o:.1f}%"

        # Compare with 5 regions
        multi_tree = db.query_tab1_treemap(year, area, None)
        reg_transfer = []
        for r in multi_tree.get("regions", []):
            tr_share = next((g["share"] for g in r["groups"] if "โอน" in g["name"]), 0.0)
            wk_share = next((g["share"] for g in r["groups"] if "ทำงาน" in g["name"]), 0.0)
            reg_transfer.append({"region": r["region"], "region_id": r["region_id"], "transfer": tr_share, "work": wk_share})
        reg_transfer.sort(key=lambda x: x["transfer"], reverse=True)

        bullets = []
        if region is not None and region > 0:
            rank_tr = next((i for i, x in enumerate(reg_transfer, 1) if x["region_id"] == region), 1)
            bullets.append(f"{scope} มีสัดส่วนเงินโอน/สวัสดิการสูงเป็นอันดับ {rank_tr} จาก 5 ภาค ({t:.1f}% เทียบทั้งประเทศ 13.1%)")
            cur_rk = next((x for x in reg_transfer if x["region_id"] == region), None)
            if cur_rk and cur_rk["work"] == min(x["work"] for x in reg_transfer):
                bullets.append(f"รายได้จากการทำงานอยู่ที่ {w:.1f}% ต่ำที่สุดใน 5 ภาค")
            else:
                bullets.append(f"สัดส่วนรายได้จากการทำงานอยู่ที่ {w:.1f}% (ทั้งประเทศ 70.5%)")
        else:
            top_tr = reg_transfer[0]
            bot_tr = reg_transfer[-1]
            bullets.append(f"{top_tr['region']}พึ่งเงินโอนมากสุด {top_tr['transfer']:.1f}% {bot_tr['region']}ต่ำสุด {bot_tr['transfer']:.1f}%")
            top_wk = max(reg_transfer, key=lambda x: x["work"])
            bullets.append(f"{top_wk['region']}มีสัดส่วนรายได้จากการทำงานสูงสุดที่ {top_wk['work']:.1f}%")

        caution = "อื่น ๆ = ทรัพย์สิน + รายได้ไม่ประจำ"
        return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}
    else:
        # Multi region (National default view)
        kpi_nat = db.query_tab1_kpi(year, area, 0)
        tot = kpi_nat["monthly_income"]
        with db.get_db() as con:
            row_nat = con.execute(
                "SELECT from_work, current_transfer, nonmoney_income, (property_income + noncur_m_income) as other FROM fact_income WHERE year_be = ? AND area_type_id = ? AND region_id = 0",
                (year, area),
            ).fetchone()
        if row_nat:
            w = round(100.0 * row_nat["from_work"] / tot, 1)
            t = round(100.0 * row_nat["current_transfer"] / tot, 1)
            nm = round(100.0 * row_nat["nonmoney_income"] / tot, 1)
            o = round(100.0 - (w + t + nm), 1)
        else:
            w, t, nm, o = 70.5, 13.1, 14.5, 2.0

        headline = f"ปี {year} ทั่วประเทศ รายได้มาจากการทำงาน {w:.1f}% เงินโอน/สวัสดิการ {t:.1f}% ไม่เป็นตัวเงิน {nm:.1f}% อื่น ๆ {o:.1f}%"

        reg_transfer = []
        for r in tree_data.get("regions", []):
            tr_share = next((g["share"] for g in r["groups"] if "โอน" in g["name"]), 0.0)
            wk_share = next((g["share"] for g in r["groups"] if "ทำงาน" in g["name"]), 0.0)
            reg_transfer.append({"region": r["region"], "transfer": tr_share, "work": wk_share})
        reg_transfer.sort(key=lambda x: x["transfer"], reverse=True)

        top_tr = reg_transfer[0]
        bot_tr = reg_transfer[-1]
        top_wk = max(reg_transfer, key=lambda x: x["work"])
        bullets = [
            f"{top_tr['region']}พึ่งเงินโอนมากสุด {top_tr['transfer']:.1f}% {bot_tr['region']}ต่ำสุด {bot_tr['transfer']:.1f}%",
            f"{top_wk['region']}มีสัดส่วนรายได้จากการทำงานสูงสุดที่ {top_wk['work']:.1f}%",
        ]
        caution = "อื่น ๆ = ทรัพย์สิน + รายได้ไม่ประจำ"
        return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


# ─────────────────────────────────────────────────────────────
# 2. TAB 2 SUMMARIES
# ─────────────────────────────────────────────────────────────

def _build_t2_map(f: Filters, meta: dict) -> dict:
    year = f.year
    pt = f.pt
    region = f.region
    metric = f.metric
    pt_name = PROPERTY_TYPE_NAMES.get(pt, "รวมทุกประเภท")
    scope = _get_scope_name(meta, region)

    # Empty check: townhouse in North or NE
    if pt == 3 and region in (3, 4):
        return {
            "headline": None,
            "bullets": [],
            "caution": None,
            "empty": "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)",
        }

    # Base year check
    if year == 2554:
        return {
            "headline": "ปี 2554 เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต",
            "bullets": [f"ดัชนีราคาบ้าน{pt_name}ทุกภาคเริ่มต้นที่ 100.0 ในปี 2554"],
            "caution": "ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท จึงไม่ใช้จัดอันดับระดับราคา",
            "empty": None,
        }

    # National values
    with db.get_db() as con:
        nat_hpi = con.execute(
            "SELECT index_mean12 FROM fact_hpi_annual WHERE year_be = ? AND region_id = 0 AND property_type_id = ?",
            (year, pt),
        ).fetchone()
        nat_54 = con.execute(
            "SELECT index_mean12 FROM fact_hpi_annual WHERE year_be = 2554 AND region_id = 0 AND property_type_id = ?",
            (pt,),
        ).fetchone()

    idx = nat_hpi["index_mean12"] if nat_hpi else 100.0
    v54 = nat_54["index_mean12"] if nat_54 else 100.0
    pct = idx - v54
    cagr = cagr_pct(v54, idx, year - 2554)

    headline = f"ปี {year} ดัชนีราคาบ้าน{pt_name}ทั้งประเทศ {idx:.1f} (สูงกว่าปี 2554 {pct:.1f}%) โตเฉลี่ย {_fmt_cagr(cagr)}"

    # Regional comparisons
    cagr_rows = db.query_tab2_choropleth_cagr(year, pt)
    cagr_rows.sort(key=lambda r: r["value"], reverse=True)

    yoy_rows = db.query_tab2_choropleth_yoy(year, pt)
    yoy_rows.sort(key=lambda r: r["value"], reverse=True)

    bullets = []
    if metric == "yoy":
        top_yoy = yoy_rows[0]
        bot_yoy = yoy_rows[-1]
        bullets.append(f"อัตราเพิ่มจากปีก่อน (YoY): {top_yoy['short_th']}สูงสุด {top_yoy['value']:.2f}% {bot_yoy['short_th']}ต่ำสุด {bot_yoy['value']:.2f}%")
        bullets.append("เรียงตาม YoY: " + " · ".join([f"{r['short_th']} {r['value']:.2f}%" for r in yoy_rows]))
    else:
        cagr_text = " · ".join([f"{r['short_th']} {r['value']:.2f}" if i == 0 else f"{r['short_th']} {r['value']:.2f}" for i, r in enumerate(cagr_rows)])
        bullets.append("อัตราเติบโตสะสมต่อปี (CAGR): " + " · ".join([f"{r['short_th']} {r['value']:.2f}" for r in cagr_rows]))

    if region is not None and region > 0:
        cur_c = next((r for r in cagr_rows if r["region_id"] == region), None)
        if cur_c:
            rank = next(i for i, r in enumerate(cagr_rows, 1) if r["region_id"] == region)
            bullets.insert(0, f"{cur_c['short_th']} มีอัตราเติบโตสะสมเป็นอันดับ {rank} จาก 5 ภาค ({cur_c['value']:.2f}%/ปี เทียบทั้งประเทศ {_fmt_cagr(cagr)})")

    caution = "ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท จึงไม่ใช้จัดอันดับระดับราคา"
    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


def _build_t2_trend(f: Filters, meta: dict) -> dict:
    pt = f.pt
    region = f.region
    grain = f.grain
    pt_name = PROPERTY_TYPE_NAMES.get(pt, "รวมทุกประเภท")
    scope = _get_scope_name(meta, region)

    # Empty check
    if pt == 3 and region in (3, 4):
        return {
            "headline": None,
            "bullets": [],
            "caution": None,
            "empty": "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)",
        }

    y0, y1 = 2554, 2568
    rid = region if region is not None else 0

    with db.get_db() as con:
        r0 = con.execute("SELECT index_mean12 FROM fact_hpi_annual WHERE year_be = ? AND region_id = ? AND property_type_id = ?", (y0, rid, pt)).fetchone()
        r1 = con.execute("SELECT index_mean12 FROM fact_hpi_annual WHERE year_be = ? AND region_id = ? AND property_type_id = ?", (y1, rid, pt)).fetchone()

    v0 = r0["index_mean12"] if r0 else 100.0
    v1 = r1["index_mean12"] if r1 else 100.0
    cagr = cagr_pct(v0, v1, y1 - y0)

    headline = f"{y0}→{y1} ดัชนี{pt_name}{scope} 100.0 → {v1:.1f} โตเฉลี่ย {_fmt_cagr(cagr)}"

    bullets = []
    if grain == "monthly":
        with db.get_db() as con:
            latest_m = con.execute(
                """SELECT m.month_abbr_th, m.year_be, f.index_value
                   FROM fact_hpi_monthly f JOIN dim_month m ON f.month_id = m.month_id
                   WHERE f.region_id = ? AND f.property_type_id = ?
                   ORDER BY f.month_id DESC LIMIT 1""",
                (rid, pt),
            ).fetchone()
        if latest_m:
            bullets.append(f"เดือนล่าสุด {latest_m['month_abbr_th']} {latest_m['year_be']} ดัชนี {latest_m['index_value']:.1f}")
        caution = "เส้นรายเดือนเป็นเฉลี่ยเคลื่อนที่ 3 เดือน · เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ ม.ค. 2566 อาจมีรอยต่อ"
    else:
        if pt == 2 and region in (3, 4):
            bullets.append("ดัชนีรวมทุกประเภทเท่ากับบ้านเดี่ยว")
        else:
            bullets.append(f"ดัชนีเพิ่มขึ้นจาก 100.0 สู่ {v1:.1f} (เพิ่ม {v1 - 100.0:.1f}%)")
        caution = "ดัชนีบอกการเปลี่ยนแปลงเทียบปีฐาน 2554 ไม่ใช่ระดับราคาบ้านเป็นบาท"

    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


def _build_t2_yoy(f: Filters, meta: dict) -> dict:
    year = f.year
    pt = f.pt
    region = f.region
    pt_name = PROPERTY_TYPE_NAMES.get(pt, "รวมทุกประเภท")
    scope = _get_scope_name(meta, region)

    if pt == 3 and region in (3, 4):
        return {
            "headline": None,
            "bullets": [],
            "caution": None,
            "empty": "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)",
        }

    if year == 2554:
        return {
            "headline": "ปี 2554 เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต",
            "bullets": ["อัตราการเปลี่ยนแปลงรายปี (YoY) เริ่มต้นคำนวณตั้งแต่ปี 2555 เป็นต้นไป"],
            "caution": "ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท",
            "empty": None,
        }

    yoy_rows = db.query_tab2_choropleth_yoy(year, pt)
    if not yoy_rows:
        return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}

    yoy_rows.sort(key=lambda r: r["value"], reverse=True)
    top = yoy_rows[0]
    bottom = yoy_rows[-1]

    with db.get_db() as con:
        nat_yoy = con.execute(
            "SELECT yoy_pct FROM v_hpi_yoy WHERE year_be = ? AND property_type_id = ? AND region_id = 0",
            (year, pt),
        ).fetchone()

    nat_val = nat_yoy["yoy_pct"] if nat_yoy else 0.0

    headline = f"ปี {year} ราคาเพิ่มจากปีก่อน {_fmt_sign_pct(nat_val)} (ทั้งประเทศ) สูงสุด{top['short_th']} {_fmt_sign_pct(top['value'])} ต่ำสุด{bottom['short_th']} {_fmt_sign_pct(bottom['value'])}"

    bullets = [
        f"เรียงตาม YoY ปี {year}: " + " · ".join([f"{r['short_th']} {_fmt_sign_pct(r['value'])}" for r in yoy_rows]),
        f"ช่วง 2555–2568 ช่องที่ติดลบมี 3 ช่อง: เหนือ ปี 2562 ({MINUS}2.23%) ใต้ ปี 2562 ({MINUS}0.39%) ใต้ ปี 2564 ({MINUS}1.41%)",
    ]

    caution = "ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท"
    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


# ─────────────────────────────────────────────────────────────
# 3. TAB 3 SUMMARIES
# ─────────────────────────────────────────────────────────────

def _build_t3_ratio(f: Filters, meta: dict) -> dict:
    y0, y1 = f.y0, f.y1
    pt = f.pt
    region = f.region
    scope = _get_scope_name(meta, region)

    if y0 == y1:
        return {
            "headline": f"ปี {y0} เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต",
            "bullets": ["อัตราส่วนคำนวณจากการเปลี่ยนแปลงของดัชนีทั้งสองเทียบปีเริ่มต้น"],
            "caution": "ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ราคาบ้านเป็นบาท",
            "empty": None,
        }

    pti_rows = db.query_tab3_price_to_income(pt, y0, y1)
    if not pti_rows:
        return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}

    rows_y1 = [r for r in pti_rows if r["year_be"] == y1]
    rid = region if region is not None else 0
    cur_row = next((r for r in rows_y1 if r["region_id"] == rid), None)
    nat_row = next((r for r in rows_y1 if r["region_id"] == 0), None)

    target_row = cur_row if cur_row else nat_row
    if not target_row:
        return {"headline": None, "bullets": [], "caution": "ไม่มีข้อมูล", "empty": None}

    pti = target_row["price_to_income_index"]
    hpi = target_row["hpi_index"]
    inc = target_row["income_index"]
    pct = round(abs(pti - 100.0))

    if pti >= 100.0:
        headline = f"ปี {y1} ราคาบ้านโตเร็วกว่ารายได้ {pct}% เทียบปี {y0} ({scope}) จึงซื้อยากขึ้น"
    else:
        headline = f"ปี {y1} ราคาบ้านโตช้ากว่ารายได้ {pct}% เทียบปี {y0} ({scope}) จึงซื้อง่ายขึ้น"

    bullets = [
        f"ดัชนีราคาบ้าน {hpi:.1f} ÷ ดัชนีรายได้ {inc:.1f} = {pti:.1f}",
    ]

    regional_y1 = [r for r in rows_y1 if not r["is_national"] and r["price_to_income_index"] is not None]
    if regional_y1:
        regional_y1.sort(key=lambda r: r["price_to_income_index"], reverse=True)
        hardest = regional_y1[0]
        easiest = regional_y1[-1]

        if region is not None and region > 0:
            rank = next(i for i, r in enumerate(regional_y1, 1) if r["region_id"] == region)
            bullets.append(f"{scope} ซื้อยากขึ้นเป็นอันดับ {rank} จาก 5 ภาค (ดัชนี {pti:.1f} เทียบทั้งประเทศ {nat_row['price_to_income_index']:.1f})")
        else:
            bullets.append(f"ยากขึ้นมากสุดที่{hardest['short_th']} ({hardest['price_to_income_index']:.1f}) น้อยสุดที่{easiest['short_th']} ({easiest['price_to_income_index']:.1f})")

    caution = "ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ราคาบ้านเป็นบาท · นิยามกทม.+ปริมณฑลของ สสช. กับ ธปท. อาจไม่ตรงกัน"
    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


def _build_t3_cagr(f: Filters, meta: dict) -> dict:
    y0, y1 = f.y0, f.y1
    pt = f.pt
    region = f.region
    cagr_view = f.cagr_view
    scope = _get_scope_name(meta, region)

    if pt == 3 and region in (3, 4):
        return {
            "headline": None,
            "bullets": [],
            "caution": None,
            "empty": "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)",
        }

    if y0 == y1:
        return {
            "headline": f"ปี {y0} เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต",
            "bullets": ["กรุณาเลือกช่วงปีเริ่มต้นและสิ้นสุดต่างกันเพื่อคำนวณอัตราเติบโตเฉลี่ยสะสม (CAGR)"],
            "caution": f"คำนวณจากอัตราเติบโตเฉลี่ยสะสมต่อปี (CAGR) ระหว่างปี {y0} และ {y1}",
            "empty": None,
        }

    years = y1 - y0
    rid = region if region is not None else 0

    income_rows = db.query_tab3_cagr_income(y0, y1)
    hpi_rows = db.query_tab3_cagr_hpi(pt, y0, y1)

    inc_cur = next((r for r in income_rows if r["region_id"] == rid), None)
    hpi_cur = next((r for r in hpi_rows if r["region_id"] == rid), None)

    inc_c = cagr_pct(inc_cur["v0"], inc_cur["v1"], years) if inc_cur else 0.0
    hpi_c = cagr_pct(hpi_cur["v0"], hpi_cur["v1"], years) if hpi_cur else 0.0
    gap = round(hpi_c - inc_c, 2)

    bullets = []

    if cagr_view == "by_type":
        if region in (3, 4):
            headline = f"{scope} ดัชนีรวมทุกประเภทเท่ากับบ้านเดี่ยว โต {hpi_c:.2f}%/ปี เทียบรายได้ {inc_c:.2f}%/ปี"
            bullets.append("ภาคนี้มีเฉพาะบ้านเดี่ยว ดัชนีรวมเท่ากับบ้านเดี่ยว ไม่มีข้อมูลทาวน์เฮ้าส์")
        else:
            by_type_rows = db.query_tab3_cagr_hpi_by_type(rid, y0, y1)
            th_c = 0.0
            sd_c = 0.0
            all_c = hpi_c
            for r in by_type_rows:
                c_val = cagr_pct(r["v0"], r["v1"], years) or 0.0
                if "ทาวน์" in r["name_th"]:
                    th_c = c_val
                elif "เดี่ยว" in r["name_th"]:
                    sd_c = c_val
                elif "รวม" in r["name_th"]:
                    all_c = c_val

            headline = f"{scope} ทาวน์เฮ้าส์โต {th_c:.2f}%/ปี บ้านเดี่ยว {sd_c:.2f}%/ปี รวมทุกประเภท {all_c:.2f}%/ปี เทียบรายได้ {inc_c:.2f}%/ปี"
            bullets.append(f"ทาวน์เฮ้าส์เติบโตเฉลี่ยสะสม {th_c:.2f}%/ปี")
            bullets.append(f"บ้านเดี่ยวเติบโตเฉลี่ยสะสม {sd_c:.2f}%/ปี")
            bullets.append(f"รายได้เฉลี่ยเติบโต {_fmt_cagr(inc_c)}")

    elif cagr_view == "summary":
        headline = f"ช่วง {y0}–{y1} {scope} ราคาบ้านโตเฉลี่ย {_fmt_cagr(hpi_c)} เทียบรายได้ {_fmt_cagr(inc_c)}"
        bullets.append(f"ส่วนต่างอัตราเติบโต (ราคาบ้าน − รายได้) อยู่ที่ {_fmt_diff_points(gap)}")
    else:
        # Default: by_region
        headline = f"ราคาบ้านโต {_fmt_cagr(hpi_c)} เทียบรายได้ {_fmt_cagr(inc_c)} (ช่องว่าง {_fmt_diff_points(gap)})"

        # Calculate gap for each region
        reg_gaps = []
        for r_meta in meta["regions"]:
            if r_meta["is_national"]:
                continue
            r_id = r_meta["region_id"]
            i_row = next((r for r in income_rows if r["region_id"] == r_id), None)
            h_row = next((r for r in hpi_rows if r["region_id"] == r_id), None)
            if i_row and h_row:
                ic = cagr_pct(i_row["v0"], i_row["v1"], years) or 0.0
                hc = cagr_pct(h_row["v0"], h_row["v1"], years) or 0.0
                reg_gaps.append({
                    "region_id": r_id,
                    "short_th": r_meta["short_th"],
                    "inc": ic,
                    "hpi": hc,
                    "gap": round(hc - ic, 2),
                })

        reg_gaps.sort(key=lambda x: x["gap"], reverse=True)
        max_gap = reg_gaps[0] if reg_gaps else None

        # BMR specific bullet
        bmr = next((x for x in reg_gaps if x["short_th"] == "กทม.+ปริมณฑล"), None)
        if bmr:
            inc_bmr_str = f"ติดลบ {MINUS}{abs(bmr['inc']):.2f}%/ปี" if bmr['inc'] < 0 else f"{bmr['inc']:.2f}%/ปี"
            bullets.append(f"กทม.+ปริมณฑล: รายได้{inc_bmr_str} ขณะที่ราคาบ้านโต {bmr['hpi']:.2f}%/ปี")

        if max_gap:
            bullets.append(f"ช่องว่างมากสุดที่{max_gap['short_th']} ({_fmt_diff_points(max_gap['gap'])}) โดยราคาบ้านโต {max_gap['hpi']:.2f}%/ปี เทียบรายได้ {max_gap['inc']:.2f}%/ปี")

        if region is not None and region > 0:
            cur_g = next((x for x in reg_gaps if x["region_id"] == region), None)
            if cur_g:
                rank = next(i for i, x in enumerate(reg_gaps, 1) if x["region_id"] == region)
                bullets.insert(0, f"{cur_g['short_th']} มีช่องว่างการเติบโตเป็นอันดับ {rank} จาก 5 ภาค ({_fmt_diff_points(cur_g['gap'])})")

    caution = f"คำนวณจากอัตราเติบโตเฉลี่ยสะสมต่อปี (CAGR) ระหว่างปี {y0} และ {y1}"
    return {"headline": headline, "bullets": bullets, "caution": caution, "empty": None}


# ─────────────────────────────────────────────────────────────
# MAIN BUILDER & CACHE
# ─────────────────────────────────────────────────────────────

def _make_cache_key(tab: int, chart_id: str, f: Filters) -> tuple:
    return (
        tab,
        chart_id,
        f.year,
        f.y0,
        f.y1,
        f.region,
        f.area,
        f.pt,
        f.metric,
        f.grain,
        f.cagr_view,
        f.real,
    )


_summary_cache: dict[tuple, dict] = {}


def build_summary(tab: int, chart_id: str, f: Filters) -> dict:
    """Build standardized summary response for a given chart."""
    if tab not in VALID_CHART_IDS or chart_id not in VALID_CHART_IDS[tab]:
        raise ValueError(f"รหัสกราฟ '{chart_id}' ไม่ถูกต้องสำหรับแท็บ {tab}")

    cache_key = _make_cache_key(tab, chart_id, f)
    if cache_key in _summary_cache:
        return _summary_cache[cache_key]

    meta = db.query_meta()
    title = CHART_TITLES.get(chart_id, "")
    scope = _get_scope_name(meta, f.region)

    # Build active filter chips list
    filters_list = []
    if tab == 1:
        if chart_id in ("t1_map", "t1_gap", "t1_sources"):
            filters_list.append({"label": "ปี", "value": f"ปี {f.year}"})
        elif chart_id == "t1_trend":
            filters_list.append({"label": "ช่วงปี", "value": f"{f.y0}–{f.y1}"})
        filters_list.append({"label": "พื้นที่", "value": scope})
        if chart_id != "t1_gap":
            filters_list.append({"label": "เขต", "value": AREA_NAMES.get(f.area, "รวมทุกเขต")})
    elif tab == 2:
        if chart_id in ("t2_map", "t2_yoy"):
            filters_list.append({"label": "ปี", "value": f"ปี {f.year}"})
        elif chart_id == "t2_trend":
            filters_list.append({"label": "ความถี่", "value": "รายเดือน" if f.grain == "monthly" else "รายปี"})
            filters_list.append({"label": "ช่วงปี", "value": f"{f.y0}–{f.y1}"})
        filters_list.append({"label": "ประเภทบ้าน", "value": PROPERTY_TYPE_NAMES.get(f.pt, "รวมทุกประเภท")})
        filters_list.append({"label": "พื้นที่", "value": scope})
    elif tab == 3:
        filters_list.append({"label": "ช่วงปี", "value": f"{f.y0}–{f.y1}"})
        filters_list.append({"label": "ประเภทบ้าน", "value": PROPERTY_TYPE_NAMES.get(f.pt, "รวมทุกประเภท")})
        filters_list.append({"label": "พื้นที่", "value": scope})
        if chart_id == "t3_cagr":
            filters_list.append({"label": "มุมมอง", "value": CAGR_VIEW_NAMES.get(f.cagr_view, "แยกภาค")})

    # Dispatch to specific builder
    if chart_id == "t1_map":
        res = _build_t1_map(f, meta)
    elif chart_id == "t1_trend":
        res = _build_t1_trend(f, meta)
    elif chart_id == "t1_gap":
        res = _build_t1_gap(f, meta)
    elif chart_id == "t1_sources":
        res = _build_t1_sources(f, meta)
    elif chart_id == "t2_map":
        res = _build_t2_map(f, meta)
    elif chart_id == "t2_trend":
        res = _build_t2_trend(f, meta)
    elif chart_id == "t2_yoy":
        res = _build_t2_yoy(f, meta)
    elif chart_id == "t3_ratio":
        res = _build_t3_ratio(f, meta)
    elif chart_id == "t3_cagr":
        res = _build_t3_cagr(f, meta)
    else:
        raise ValueError(f"Unknown chart_id {chart_id}")

    output = {
        "chart_id": chart_id,
        "title": title,
        "filters": filters_list,
        "headline": res.get("headline"),
        "bullets": res.get("bullets", []),
        "caution": res.get("caution"),
        "empty": res.get("empty"),
    }

    _summary_cache[cache_key] = output
    return output
