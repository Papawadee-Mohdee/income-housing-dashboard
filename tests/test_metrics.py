"""Test metrics and calculations against expected_values.json.

Verification:
- CAGR of household income 2554 -> 2566
- CAGR of HPI (all residential types) 2554 -> 2566
- CAGR of HPI by property type (national)
- Price to income index (2566, base 2554)
- Urban-rural gap 2566
- Income sources shares (national 2566)
- Filter validation rules
"""
import json
import sqlite3
from pathlib import Path
import pytest

from app.metrics import cagr_pct, price_to_income_index, rebase, income_index, pct_change
from app.filters import Filters
from app.db import (
    query_meta,
    query_tab1_kpi,
    query_tab2_kpi,
    query_tab3_cagr_income,
    query_tab3_cagr_hpi,
    query_tab3_cagr_hpi_by_type,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILE = ROOT / "data" / "expected_values.json"


@pytest.fixture(scope="module")
def expected():
    with open(EXPECTED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def db_conn():
    db_path = ROOT / "data" / "dashboard.db"
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    yield con
    con.close()


def test_income_cagr(expected, db_conn):
    """Test income CAGR for all regions between 2554 and 2566."""
    y0, y1 = expected["window"]
    span = expected["years_span"]
    
    cur = db_conn.cursor()
    cur.execute("""
        SELECT r.code, s.monthly_income, e.monthly_income
        FROM fact_income s
        JOIN fact_income e ON e.region_id = s.region_id AND e.area_type_id = s.area_type_id
        JOIN dim_region r ON r.region_id = s.region_id
        WHERE s.year_be = ? AND e.year_be = ? AND s.area_type_id = 0
        ORDER BY r.map_order
    """, (y0, y1))
    rows = cur.fetchall()
    
    for code, v0, v1 in rows:
        calculated = cagr_pct(v0, v1, span)
        exp = expected["income_cagr_pct"][code]
        assert calculated == exp, f"Income CAGR mismatch for {code}: got {calculated}, expected {exp}"


def test_hpi_all_cagr(expected, db_conn):
    """Test HPI (ALL types) CAGR for all regions between 2554 and 2566."""
    y0, y1 = expected["window"]
    span = expected["years_span"]

    cur = db_conn.cursor()
    cur.execute("""
        SELECT r.code, s.index_mean12, e.index_mean12
        FROM fact_hpi_annual s
        JOIN fact_hpi_annual e ON e.region_id = s.region_id AND e.property_type_id = s.property_type_id
        JOIN dim_region r ON r.region_id = s.region_id
        WHERE s.year_be = ? AND e.year_be = ? AND s.property_type_id = 1
        ORDER BY r.map_order
    """, (y0, y1))
    rows = cur.fetchall()

    for code, v0, v1 in rows:
        calculated = cagr_pct(v0, v1, span)
        exp = expected["hpi_all_cagr_pct"][code]
        assert calculated == exp, f"HPI ALL CAGR mismatch for {code}: got {calculated}, expected {exp}"


def test_hpi_cagr_by_type(expected, db_conn):
    """Test national HPI CAGR by property type."""
    y0, y1 = expected["window"]
    span = expected["years_span"]

    cur = db_conn.cursor()
    cur.execute("""
        SELECT p.code, s.index_mean12, e.index_mean12
        FROM fact_hpi_annual s
        JOIN fact_hpi_annual e ON e.region_id = s.region_id AND e.property_type_id = s.property_type_id
        JOIN dim_property_type p ON p.property_type_id = s.property_type_id
        WHERE s.year_be = ? AND e.year_be = ? AND s.region_id = 0
        ORDER BY p.property_type_id
    """, (y0, y1))
    rows = cur.fetchall()

    for code, v0, v1 in rows:
        calculated = cagr_pct(v0, v1, span)
        exp = expected["hpi_cagr_pct_national_by_type"][code]
        assert calculated == exp, f"HPI CAGR by type mismatch for {code}: got {calculated}, expected {exp}"


def test_price_to_income_index_2566(expected, db_conn):
    """Test price-to-income index 2566 matches expected_values.json."""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT r.code, p.price_to_income_index
        FROM v_price_to_income p
        JOIN dim_region r ON r.region_id = p.region_id
        WHERE p.year_be = 2566 AND p.property_type_id = 1
        ORDER BY r.map_order
    """)
    rows = cur.fetchall()

    for code, pti in rows:
        calculated = round(pti, 1)
        exp = expected["price_to_income_index_2566_all"][code]
        assert calculated == exp, f"PTI mismatch for {code}: got {calculated}, expected {exp}"


def test_urban_rural_gap_2566(expected, db_conn):
    """Test urban-rural gap % in 2566 matches expected_values.json."""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT r.code, g.gap_pct
        FROM v_income_urban_rural_gap g
        JOIN dim_region r ON r.region_id = g.region_id
        WHERE g.year_be = 2566
        ORDER BY r.map_order
    """)
    rows = cur.fetchall()

    for code, gap in rows:
        calculated = round(gap, 1)
        exp = expected["urban_rural_gap_pct_2566"][code]
        assert calculated == exp, f"Gap mismatch for {code}: got {calculated}, expected {exp}"


def test_treemap_shares_2566(expected, db_conn):
    """Test 5 leaf income source shares national 2566."""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT source_code, 100.0 * amount_baht / monthly_income AS share
        FROM v_income_long
        WHERE year_be = 2566 AND region_id = 0 AND area_type_id = 0
    """)
    rows = cur.fetchall()

    for code, share in rows:
        calculated = round(share, 1)
        exp = expected["treemap_shares_2566_national_pct"][code]
        assert calculated == exp, f"Share mismatch for {code}: got {calculated}, expected {exp}"


def test_filter_validation():
    """Test filter validation rules."""
    # Valid default filters
    f = Filters.from_params(tab=1)
    assert f.year == 2568
    assert f.y0 == 2554
    assert f.y1 == 2568

    # Valid custom
    f2 = Filters.from_params(tab=2, year=2567, pt=2, theme="light", grain="monthly")
    assert f2.year == 2567
    assert f2.pt == 2
    assert f2.theme == "light"
    assert f2.grain == "monthly"

    # Invalid tab
    with pytest.raises(ValueError, match="แท็บ 4 ไม่ถูกต้อง"):
        Filters.from_params(tab=4)

    # Invalid area
    with pytest.raises(ValueError, match="ประเภทเขต 5 ไม่ถูกต้อง"):
        Filters.from_params(tab=1, area=5)

    # Invalid property type
    with pytest.raises(ValueError, match="ประเภทบ้าน 9 ไม่ถูกต้อง"):
        Filters.from_params(tab=2, pt=9)

    # Invalid survey year for tab 1
    with pytest.raises(ValueError, match="ไม่มีข้อมูลสำรวจรายได้"):
        Filters.from_params(tab=1, year=2567)  # 2567 has no income survey

    # Year out of range
    with pytest.raises(ValueError, match="ไม่อยู่ในช่วง"):
        Filters.from_params(tab=2, year=2570)

    # y0 > y1
    with pytest.raises(ValueError, match="ปีเริ่มต้น .* ต้องไม่มากกว่าปีสิ้นสุด"):
        Filters.from_params(tab=1, y0=2566, y1=2556)
