"""Database layer — all SQLite queries live here.

Usage:
    from app.db import get_db, query_tab1, query_tab2, query_tab3, query_meta

All functions return plain Python dicts/lists; no ORM objects leak out.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "dashboard.db"


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Return rows as dicts."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


@contextmanager
def get_db():
    """Yield a read-only connection with dict rows."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = _row_factory
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
    finally:
        con.close()


# ──────────────────────────────────────── Meta
def query_meta() -> dict[str, Any]:
    """Filter options, dataset metadata, latest-data labels."""
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
        latest_hpi_year = max(hpi_years)
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


def query_tab1_treemap(year: int, area: int, region: int | None) -> list[dict]:
    with get_db() as con:
        if region is not None:
            return con.execute(
                """SELECT r.short_th AS region, l.group_th, l.source_name_th, l.amount_baht,
                          100.0 * l.amount_baht / l.monthly_income AS share_pct
                   FROM v_income_long l JOIN dim_region r ON r.region_id = l.region_id
                   WHERE l.year_be = ? AND l.area_type_id = ? AND l.region_id = ?""",
                (year, area, region),
            ).fetchall()
        return con.execute(
            """SELECT r.short_th AS region, l.group_th, l.source_name_th, l.amount_baht,
                      100.0 * l.amount_baht / l.monthly_income AS share_pct
               FROM v_income_long l JOIN dim_region r ON r.region_id = l.region_id
               WHERE l.year_be = ? AND l.area_type_id = ? AND r.region_id > 0
               ORDER BY r.map_order""",
            (year, area),
        ).fetchall()


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
    """KPI data for Tab 1."""
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
        work_pct = 100.0 * income["from_work"] / income["monthly_income"]
        # urban-rural gap
        gap = con.execute(
            "SELECT gap_pct FROM v_income_urban_rural_gap WHERE year_be = ? AND region_id = ?",
            (year, rid),
        ).fetchone()
    return {
        "monthly_income": income["monthly_income"],
        "base_income": base_income["monthly_income"],
        "transfer_pct": transfer_pct,
        "work_pct": work_pct,
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
        # fastest growing region
        fastest = con.execute(
            """SELECT r.short_th, a.index_mean12 AS idx
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


def query_tab3_kpi(year: int, pt: int, y0: int, y1: int, region: int | None) -> dict:
    rid = region if region is not None else 0
    with get_db() as con:
        pti = con.execute(
            "SELECT price_to_income_index FROM v_price_to_income WHERE year_be = ? AND region_id = ? AND property_type_id = ?",
            (year, rid, pt),
        ).fetchone()
        # count regions where HPI grew faster than income
        rows = con.execute(
            """SELECT r.region_id,
                      100.0 * (h_e.index_mean12 / h_s.index_mean12) / (i_e.monthly_income / i_s.monthly_income) AS pti
               FROM dim_region r
               JOIN fact_income i_s ON i_s.region_id = r.region_id AND i_s.year_be = ? AND i_s.area_type_id = 0
               JOIN fact_income i_e ON i_e.region_id = r.region_id AND i_e.year_be = ? AND i_e.area_type_id = 0
               JOIN fact_hpi_annual h_s ON h_s.region_id = r.region_id AND h_s.year_be = ? AND h_s.property_type_id = ?
               JOIN fact_hpi_annual h_e ON h_e.region_id = r.region_id AND h_e.year_be = ? AND h_e.property_type_id = ?
               WHERE r.region_id > 0""",
            (y0, y1, y0, pt, y1, pt),
        ).fetchall()
        harder = sum(1 for r in rows if r["pti"] > 100)
    return {
        "price_to_income_index": pti["price_to_income_index"] if pti else None,
        "regions_harder": harder,
        "total_regions": 5,
    }
