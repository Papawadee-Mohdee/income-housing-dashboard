"""Automated test suite for chart summaries (v2 Appendix 2 Section 12).

Tests:
- All 9 chart summaries return correct structure
- Fixed Thai templates match §12.6 exact figures
- Zero forbidden causal words (เพราะ, เนื่องจาก, ส่งผลให้, สาเหตุ)
- Zero forbidden comparative/living-cost words (แพงที่สุด, แพงกว่า, ค่าครองชีพ, รายได้จริง)
- Negative numbers use mathematical minus U+2212 (MINUS)
- Base year 2554 returns standard base year explanation
- Empty townhouse for North/Isan returns clear explanation without bullets
- Fast response time (< 150 ms)
- HTTP 422 on invalid chart IDs and filters
"""
import time
from fastapi import HTTPException
import pytest

from app.filters import Filters
from app.main import get_summary
from app.summaries import MINUS, VALID_CHART_IDS, build_summary

FORBIDDEN_WORDS = [
    "เพราะ",
    "เนื่องจาก",
    "ส่งผลให้",
    "สาเหตุ",
    "แพงที่สุด",
    "แพงกว่า",
    "ค่าครองชีพ",
    "รายได้จริง",
]

CHART_SPECS = [
    (1, "t1_map"),
    (1, "t1_trend"),
    (1, "t1_gap"),
    (1, "t1_sources"),
    (2, "t2_map"),
    (2, "t2_trend"),
    (2, "t2_yoy"),
    (3, "t3_ratio"),
    (3, "t3_cagr"),
]


def _check_forbidden_text(text: str | None, context: str):
    if not text:
        return
    for w in FORBIDDEN_WORDS:
        assert w not in text, f"Found forbidden word '{w}' in {context}: {text}"


def _check_negative_minus(text: str | None, context: str):
    if not text:
        return
    # Any negative sign in front of a number or percentage should be MINUS (\u2212)
    # Check ASCII hyphen before a digit (e.g. -2.5% or -100)
    for part in text.split():
        if part.startswith("-") and len(part) > 1 and part[1].isdigit():
            raise AssertionError(f"Found ASCII hyphen instead of Unicode MINUS in {context}: {part}")


@pytest.mark.parametrize("tab,chart_id", CHART_SPECS)
def test_default_summary_structure_and_rules(tab, chart_id):
    f = Filters.from_params(tab=tab, year=2566, y0=2554, y1=2568)
    res = build_summary(tab, chart_id, f)

    assert res["chart_id"] == chart_id
    assert res["title"]
    assert isinstance(res["filters"], list)
    assert len(res["filters"]) >= 2

    # Check text rules
    _check_forbidden_text(res["headline"], f"{chart_id}.headline")
    _check_negative_minus(res["headline"], f"{chart_id}.headline")

    for i, b in enumerate(res["bullets"]):
        _check_forbidden_text(b, f"{chart_id}.bullets[{i}]")
        _check_negative_minus(b, f"{chart_id}.bullets[{i}]")

    if res["caution"]:
        _check_forbidden_text(res["caution"], f"{chart_id}.caution")
        _check_negative_minus(res["caution"], f"{chart_id}.caution")


def test_t1_map_default_values_2566():
    f = Filters.from_params(tab=1, year=2566, area=0, region=0, metric="income")
    res = build_summary(1, "t1_map", f)

    assert "39,087" in res["headline"]
    assert "22,524" in res["headline"]
    assert "1.74" in res["headline"]
    assert "กทม.+ปริมณฑล" in res["headline"]
    assert "อีสาน" in res["headline"]
    assert len(res["bullets"]) >= 2
    assert "39,087" in res["bullets"][0]


def test_t1_map_region_selection_rank():
    # Isan (region 4) should be ranked 5 of 5
    f = Filters.from_params(tab=1, year=2566, region=4)
    res = build_summary(1, "t1_map", f)
    assert "อันดับที่ 5" in res["headline"]
    assert "อีสาน" in res["headline"]
    assert "22,524" in res["headline"]


def test_t1_sources_proportions_sum():
    f = Filters.from_params(tab=1, year=2566, area=0, region=0)
    res = build_summary(1, "t1_sources", f)
    # Check headline proportions
    headline = res["headline"]
    assert "70.5%" in headline
    assert "13.1%" in headline
    assert "14.5%" in headline


def test_t2_map_townhouse_empty_north_isan():
    # North (region 3), Townhouse (pt 3)
    f_north = Filters.from_params(tab=2, year=2566, pt=3, region=3)
    res_north = build_summary(2, "t2_map", f_north)
    assert res_north["empty"] == "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)"
    assert res_north["headline"] is None
    assert len(res_north["bullets"]) == 0

    # Isan (region 4), Townhouse (pt 3)
    f_isan = Filters.from_params(tab=2, year=2566, pt=3, region=4)
    res_isan = build_summary(2, "t2_map", f_isan)
    assert res_isan["empty"] == "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)"


def test_base_year_2554_explanations():
    base_msg = "ปี 2554 เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต"

    # t1_trend with y0 == y1 == 2554
    f1 = Filters.from_params(tab=1, y0=2554, y1=2554)
    r1 = build_summary(1, "t1_trend", f1)
    assert r1["headline"] == base_msg

    # t2_map with year 2554
    f2 = Filters.from_params(tab=2, year=2554)
    r2 = build_summary(2, "t2_map", f2)
    assert r2["headline"] == base_msg

    # t2_yoy with year 2554
    f3 = Filters.from_params(tab=2, year=2554)
    r3 = build_summary(2, "t2_yoy", f3)
    assert r3["headline"] == base_msg

    # t3_ratio with y0 == y1 == 2554
    f4 = Filters.from_params(tab=3, y0=2554, y1=2554)
    r4 = build_summary(3, "t3_ratio", f4)
    assert r4["headline"] == base_msg

    # t3_cagr with y0 == y1 == 2554
    f5 = Filters.from_params(tab=3, y0=2554, y1=2554)
    r5 = build_summary(3, "t3_cagr", f5)
    assert r5["headline"] == base_msg


def test_t2_yoy_negative_minus_sign():
    f = Filters.from_params(tab=2, year=2566)
    res = build_summary(2, "t2_yoy", f)
    # Bullet 2 mentions negative YoY values
    b2 = res["bullets"][1]
    assert MINUS in b2
    assert f"{MINUS}2.23%" in b2
    assert f"{MINUS}0.39%" in b2
    assert f"{MINUS}1.41%" in b2


def test_api_summary_endpoint():
    data = get_summary(tab=1, chart_id="t1_map", year=2566)
    assert data["chart_id"] == "t1_map"
    assert "39,087" in data["headline"]
    assert len(data["bullets"]) >= 2


def test_api_summary_invalid_chart_422():
    with pytest.raises(HTTPException) as exc_info:
        get_summary(tab=1, chart_id="invalid_chart")
    assert exc_info.value.status_code == 422


def test_api_summary_response_time():
    # Performance benchmark: must answer under 150ms
    t0 = time.perf_counter()
    data = get_summary(tab=1, chart_id="t1_map", year=2566)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert data["chart_id"] == "t1_map"
    assert elapsed_ms < 150, f"Summary response time {elapsed_ms:.1f}ms exceeds 150ms threshold"
