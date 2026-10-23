"""Database layer — SQLite queries for all tabs, metadata, and KPI aggregations.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "dashboard.db"


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


@contextmanager
def get_db():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = _row_factory
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
    finally:
        con.close()


def check_cpi_available() -> bool:
    with get_db() as con:
        r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fact_cpi'").fetchone()
        return r is not None


# ──────────────────────────────────────── Meta
def query_meta() -> dict[str, Any]:
    with get_db() as con:
        years = con.execute(
            "SELECT year_be, has_income_survey, has_hpi FROM dim_year ORDER BY year_be"
        ).fetchall()
        regions = con.execute(
            "SELECT region_id, code, short_th, name_th, is_national FROM dim_region ORDER BY map_order"
        ).fetchall()
        area_types = con.execute(
            "SELECT area_type_id, name_th FROM dim_area_type ORDER BY area_type_id"
        ).fetchall()
        property_types = con.execute(
            "SELECT property_type_id, code, name_th FROM dim_property_type ORDER BY property_type_id"
        ).fetchall()
        datasets = con.execute("SELECT * FROM meta_dataset").fetchall()
        income_years = [y["year_be"] for y in years if y["has_income_survey"]]
        hpi_years = [y["year_be"] for y in years if y["has_hpi"]]
        latest_income = max(income_years)
        latest_hpi_month = con.execute(
            "SELECT month_abbr_th, year_be FROM dim_month ORDER BY month_id DESC LIMIT 1"
        ).fetchone()
    return {
        "years": years,
        "income_years": income_years,
        "hpi_years": hpi_years,
        "regions": regions,
        "area_types": area_types,
        "property_types": property_types,
        "datasets": datasets,
        "cpi_available": check_cpi_available(),
        "as_of": {
            "income_latest_wave": latest_income,
            "hpi_latest_month": f"{latest_hpi_month['month_abbr_th']} {latest_hpi_month['year_be']}",
        },
    }


# ──────────────────────────────────────── Tab 1 queries
def query_tab1_choropleth(year: int, area: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th, f.monthly_income AS value
               FROM fact_income f JOIN dim_region r ON r.region_id = f.region_id
               WHERE f.year_be = ? AND f.area_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, area),
        ).fetchall()


def query_tab1_choropleth_index(year: int, area: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th, i.income_index AS value
               FROM v_income_index i JOIN dim_region r ON r.region_id = i.region_id
               WHERE i.year_be = ? AND i.area_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, area),
        ).fetchall()


def query_tab1_choropleth_transfer(year: int, area: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th,
                      100.0 * f.current_transfer / f.monthly_income AS value
               FROM fact_income f JOIN dim_region r ON r.region_id = f.region_id
               WHERE f.year_be = ? AND f.area_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, area),
        ).fetchall()


def query_tab1_treemap(year: int, area: int, region: int | None) -> dict:
    """Return treemap data strictly respecting parent shares (never summing regions together).
    
    If region is None:
      outer = 5 regions (region_id 1..5)
      leaves = 4 groups per region (จากการทำงาน, เงินโอน/สวัสดิการ, ไม่เป็นตัวเงิน, อื่น ๆ)
    If region is not None (e.g. 0 for national or 1..5 for specific region):
      outer = selected region
      leaves = 5 detailed leaf sources
    """
    with get_db() as con:
        if region is not None:
            # Single region: all 5 leaf sources
            row = con.execute(
                """SELECT f.region_id, r.short_th, f.monthly_income, f.from_work,
                          f.current_transfer, f.nonmoney_income, f.property_income, f.noncur_m_income
                   FROM fact_income f JOIN dim_region r ON r.region_id = f.region_id
                   WHERE f.year_be = ? AND f.area_type_id = ? AND f.region_id = ?""",
                (year, area, region),
            ).fetchone()
            if not row:
                return {"mode": "single", "region": "", "monthly_income": 0, "leaves": []}
            tot = row["monthly_income"]
            s1 = round(100.0 * row["from_work"] / tot, 1)
            s2 = round(100.0 * row["current_transfer"] / tot, 1)
            s3 = round(100.0 * row["nonmoney_income"] / tot, 1)
            s4 = round(100.0 * row["property_income"] / tot, 1)
            s5 = round(100.0 - (s1 + s2 + s3 + s4), 1)
            leaves = [
                {"name": "จากการทำงาน", "amount": row["from_work"], "share": s1},
                {"name": "เงินโอน/สวัสดิการ", "amount": row["current_transfer"], "share": s2},
                {"name": "ไม่เป็นตัวเงิน", "amount": row["nonmoney_income"], "share": s3},
                {"name": "ทรัพย์สิน", "amount": row["property_income"], "share": s4},
                {"name": "ไม่ประจำ", "amount": row["noncur_m_income"], "share": s5},
            ]
            return {"mode": "single", "region": row["short_th"], "monthly_income": tot, "leaves": leaves}

        # Multi-region: 5 regions with 4 consolidated groups
        rows = con.execute(
            """SELECT f.region_id, r.short_th, f.monthly_income, f.from_work,
                      f.current_transfer, f.nonmoney_income, (f.property_income + f.noncur_m_income) AS other_income
               FROM fact_income f JOIN dim_region r ON r.region_id = f.region_id
               WHERE f.year_be = ? AND f.area_type_id = ? AND f.region_id > 0
               ORDER BY r.map_order""",
            (year, area),
        ).fetchall()
        regions_data = []
        for r in rows:
            tot = r["monthly_income"]
            s1 = round(100.0 * r["from_work"] / tot, 1)
            s2 = round(100.0 * r["current_transfer"] / tot, 1)
            s3 = round(100.0 * r["nonmoney_income"] / tot, 1)
            s4 = round(100.0 - (s1 + s2 + s3), 1)
            groups = [
                {"name": "จากการทำงาน", "amount": r["from_work"], "share": s1},
                {"name": "เงินโอน/สวัสดิการ", "amount": r["current_transfer"], "share": s2},
                {"name": "ไม่เป็นตัวเงิน", "amount": r["nonmoney_income"], "share": s3},
                {"name": "อื่น ๆ", "amount": r["other_income"], "share": s4},
            ]
            regions_data.append({"region": r["short_th"], "region_id": r["region_id"], "monthly_income": tot, "groups": groups})
        return {"mode": "multi", "regions": regions_data}


def query_tab1_trend(area: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT f.year_be, r.region_id, r.code, r.short_th, r.is_national,
                      f.monthly_income, i.income_index
               FROM fact_income f
               JOIN v_income_index i ON i.year_be = f.year_be AND i.region_id = f.region_id
                    AND i.area_type_id = f.area_type_id
               JOIN dim_region r ON r.region_id = f.region_id
               WHERE f.area_type_id = ? AND f.year_be BETWEEN ? AND ?
               ORDER BY r.map_order, f.year_be""",
            (area, y0, y1),
        ).fetchall()


def query_tab1_heatmap(y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT g.year_be, r.region_id, r.code, r.short_th, r.is_national, g.gap_pct
               FROM v_income_urban_rural_gap g JOIN dim_region r ON r.region_id = g.region_id
               WHERE g.year_be BETWEEN ? AND ? ORDER BY r.map_order, g.year_be""",
            (y0, y1),
        ).fetchall()


def query_tab1_kpi(year: int, area: int, region: int | None) -> dict:
    rid = region if region is not None else 0
    with get_db() as con:
        income = con.execute(
            "SELECT monthly_income, from_work, current_transfer FROM fact_income WHERE year_be = ? AND region_id = ? AND area_type_id = ?",
            (year, rid, area),
        ).fetchone()
        base_income = con.execute(
            "SELECT monthly_income FROM fact_income WHERE year_be = (SELECT MIN(year_be) FROM fact_income) AND region_id = ? AND area_type_id = ?",
            (rid, area),
        ).fetchone()
        transfer_pct = 100.0 * income["current_transfer"] / income["monthly_income"]
        gap = con.execute(
            "SELECT gap_pct FROM v_income_urban_rural_gap WHERE year_be = ? AND region_id = ?",
            (year, rid),
        ).fetchone()
    return {
        "monthly_income": income["monthly_income"],
        "base_income": base_income["monthly_income"],
        "transfer_pct": transfer_pct,
        "gap_pct": gap["gap_pct"] if gap else None,
    }


# ──────────────────────────────────────── Tab 2 queries
def query_tab2_choropleth(year: int, pt: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th, a.index_mean12 AS value
               FROM fact_hpi_annual a JOIN dim_region r ON r.region_id = a.region_id
               WHERE a.year_be = ? AND a.property_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, pt),
        ).fetchall()


def query_tab2_choropleth_yoy(year: int, pt: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th, v.yoy_pct AS value
               FROM v_hpi_yoy v JOIN dim_region r ON r.region_id = v.region_id
               WHERE v.year_be = ? AND v.property_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, pt),
        ).fetchall()


def query_tab2_choropleth_cagr(year: int, pt: int) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """SELECT r.region_id, r.code, r.short_th,
                      b.index_mean12 AS v0, a.index_mean12 AS v1, (a.year_be - b.year_be) AS years
               FROM fact_hpi_annual a
               JOIN fact_hpi_annual b ON b.region_id = a.region_id AND b.property_type_id = a.property_type_id
                    AND b.year_be = 2554
               JOIN dim_region r ON r.region_id = a.region_id
               WHERE a.year_be = ? AND a.property_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, pt),
        ).fetchall()
        result = []
        for r in rows:
            c = ((r["v1"] / r["v0"]) ** (1.0 / r["years"]) - 1.0) * 100.0 if r["years"] > 0 else 0.0
            result.append({"region_id": r["region_id"], "code": r["code"], "short_th": r["short_th"], "value": round(c, 2)})
        return result


def query_tab2_trend_monthly(pt: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT m.month_id, m.year_be, m.month_no, r.region_id, r.code, r.short_th,
                      r.is_national, f.index_value
               FROM fact_hpi_monthly f
               JOIN dim_month m ON m.month_id = f.month_id
               JOIN dim_region r ON r.region_id = f.region_id
               WHERE f.property_type_id = ? AND m.year_be BETWEEN ? AND ?
               ORDER BY r.map_order, m.month_id""",
            (pt, y0, y1),
        ).fetchall()


def query_tab2_trend_annual(pt: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT a.year_be, r.region_id, r.code, r.short_th, r.is_national,
                      a.index_mean12 AS index_value
               FROM fact_hpi_annual a JOIN dim_region r ON r.region_id = a.region_id
               WHERE a.property_type_id = ? AND a.year_be BETWEEN ? AND ?
               ORDER BY r.map_order, a.year_be""",
            (pt, y0, y1),
        ).fetchall()


def query_tab2_heatmap(pt: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT v.year_be, r.region_id, r.code, r.short_th, r.is_national, v.yoy_pct
               FROM v_hpi_yoy v JOIN dim_region r ON r.region_id = v.region_id
               WHERE v.property_type_id = ? AND v.year_be BETWEEN ? AND ?
                 AND v.yoy_pct IS NOT NULL
               ORDER BY r.map_order, v.year_be""",
            (pt, y0, y1),
        ).fetchall()


def query_tab2_kpi(year: int, pt: int, region: int | None) -> dict:
    rid = region if region is not None else 0
    with get_db() as con:
        cur = con.execute(
            "SELECT index_mean12 FROM fact_hpi_annual WHERE year_be = ? AND region_id = ? AND property_type_id = ?",
            (year, rid, pt),
        ).fetchone()
        base = con.execute(
            "SELECT index_mean12 FROM fact_hpi_annual WHERE year_be = (SELECT MIN(year_be) FROM fact_hpi_annual) AND region_id = ? AND property_type_id = ?",
            (rid, pt),
        ).fetchone()
        prev = con.execute(
            "SELECT yoy_pct FROM v_hpi_yoy WHERE year_be = ? AND region_id = ? AND property_type_id = ?",
            (year, rid, pt),
        ).fetchone()
        fastest = con.execute(
            """SELECT r.short_th, a.index_mean12 AS idx,
                      100.0 * ((a.index_mean12 / b.index_mean12) - 1.0) AS growth
               FROM fact_hpi_annual a JOIN dim_region r ON r.region_id = a.region_id
               JOIN fact_hpi_annual b ON b.region_id = a.region_id AND b.property_type_id = a.property_type_id
                    AND b.year_be = (SELECT MIN(year_be) FROM fact_hpi_annual)
               WHERE a.year_be = ? AND a.property_type_id = ? AND r.region_id > 0
               ORDER BY (a.index_mean12 / b.index_mean12) DESC LIMIT 1""",
            (year, pt),
        ).fetchone()
    return {
        "index_value": cur["index_mean12"] if cur else None,
        "base_value": base["index_mean12"] if base else None,
        "yoy_pct": prev["yoy_pct"] if prev else None,
        "fastest_region": fastest["short_th"] if fastest else None,
        "fastest_idx": fastest["idx"] if fastest else None,
    }


# ──────────────────────────────────────── Tab 3 queries
def query_tab3_price_to_income(pt: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT p.year_be, r.region_id, r.code, r.short_th, r.is_national,
                      p.income_index, p.hpi_index, p.price_to_income_index
               FROM v_price_to_income p JOIN dim_region r ON r.region_id = p.region_id
               WHERE p.property_type_id = ? AND p.year_be BETWEEN ? AND ?
               ORDER BY r.map_order, p.year_be""",
            (pt, y0, y1),
        ).fetchall()


def query_tab3_cagr_income(y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th, r.is_national,
                      s.monthly_income AS v0, e.monthly_income AS v1,
                      e.year_be - s.year_be AS years
               FROM fact_income s
               JOIN fact_income e ON e.region_id = s.region_id AND e.area_type_id = s.area_type_id
               JOIN dim_region r ON r.region_id = s.region_id
               WHERE s.year_be = ? AND e.year_be = ? AND s.area_type_id = 0
               ORDER BY r.map_order""",
            (y0, y1),
        ).fetchall()


def query_tab3_cagr_hpi(pt: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        return con.execute(
            """SELECT r.region_id, r.code, r.short_th, r.is_national,
                      s.index_mean12 AS v0, e.index_mean12 AS v1,
                      e.year_be - s.year_be AS years
               FROM fact_hpi_annual s
               JOIN fact_hpi_annual e ON e.region_id = s.region_id
                    AND e.property_type_id = s.property_type_id
               JOIN dim_region r ON r.region_id = s.region_id
               WHERE s.year_be = ? AND e.year_be = ? AND s.property_type_id = ?
               ORDER BY r.map_order""",
            (y0, y1, pt),
        ).fetchall()


def query_tab3_cagr_hpi_by_type(region: int, y0: int, y1: int) -> list[dict]:
    with get_db() as con:
        # North and Northeast have only detached houses (Q-H1)
        if region in (3, 4):
            row = con.execute(
                """SELECT s.index_mean12 AS v0, e.index_mean12 AS v1, e.year_be - s.year_be AS years
                   FROM fact_hpi_annual s
                   JOIN fact_hpi_annual e ON e.region_id = s.region_id AND e.property_type_id = s.property_type_id
                   WHERE s.year_be = ? AND e.year_be = ? AND s.region_id = ? AND s.property_type_id = 1""",
                (y0, y1, region),
            ).fetchone()
            if row:
                return [{
                    "property_type_id": 1,
                    "code": "ALL_DETACHED",
                    "name_th": "ภาพรวม = บ้านเดี่ยว",
                    "v0": row["v0"],
                    "v1": row["v1"],
                    "years": row["years"],
                }]
            return []

        return con.execute(
            """SELECT p.property_type_id, p.code, p.name_th,
                      s.index_mean12 AS v0, e.index_mean12 AS v1,
                      e.year_be - s.year_be AS years
               FROM fact_hpi_annual s
               JOIN fact_hpi_annual e ON e.region_id = s.region_id
                    AND e.property_type_id = s.property_type_id
               JOIN dim_property_type p ON p.property_type_id = s.property_type_id
               WHERE s.year_be = ? AND e.year_be = ? AND s.region_id = ?
               ORDER BY p.property_type_id""",
            (y0, y1, region),
        ).fetchall()
