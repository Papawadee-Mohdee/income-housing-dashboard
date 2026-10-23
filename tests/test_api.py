"""API Integration Tests using FastAPI TestClient."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILE = ROOT / "data" / "expected_values.json"


@pytest.fixture(scope="module")
def expected():
    with open(EXPECTED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_index_page():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Income × Housing Dashboard" in res.text
    assert "data-theme" in res.text


def test_meta():
    res = client.get("/api/meta")
    assert res.status_code == 200
    data = res.json()
    assert "years" in data
    assert "income_years" in data
    assert "regions" in data
    assert "as_of" in data
    assert data["as_of"]["income_latest_wave"] == 2568
    assert len(data["regions"]) == 6


def test_tab1_default(expected):
    res = client.get("/api/tab/1")
    assert res.status_code == 200
    data = res.json()

    # Check structure
    assert "filters" in data
    assert "headline" in data
    assert "kpis" in data
    assert "ring" in data
    assert "charts" in data
    assert "insights" in data

    # Default year is 2566
    assert data["filters"]["year"] == 2566

    # 4 charts required
    for chart_key in ["choropleth", "treemap", "trend", "heatmap"]:
        assert chart_key in data["charts"]
        assert "figure" in data["charts"][chart_key]
        assert "summary" in data["charts"][chart_key]
        assert "table" in data["charts"][chart_key]

    # Verify KPI values against expected
    kpis = {k["id"]: k for k in data["kpis"]}
    assert kpis["income"]["value"] == 29030
    assert kpis["income"]["delta"]["vs"] == "2554"
    assert round(kpis["income"]["delta"]["value"], 1) == 24.9
    assert kpis["cagr"]["value"] == expected["income_cagr_pct"]["TH"]
    assert kpis["transfer"]["value"] == expected["treemap_shares_2566_national_pct"]["CURRENT_TRANSFER"]
    assert kpis["gap"]["value"] == expected["urban_rural_gap_pct_2566"]["TH"]

    # Ring value
    assert data["ring"]["value"] == expected["treemap_shares_2566_national_pct"]["FROM_WORK"]


def test_tab2_default(expected):
    res = client.get("/api/tab/2")
    assert res.status_code == 200
    data = res.json()

    assert "charts" in data
    for chart_key in ["choropleth", "trend", "heatmap"]:
        assert chart_key in data["charts"]

    kpis = {k["id"]: k for k in data["kpis"]}
    assert kpis["cagr"]["value"] == expected["hpi_all_cagr_pct"]["TH"]

    # Monthly grain test
    res_monthly = client.get("/api/tab/2?grain=monthly")
    assert res_monthly.status_code == 200

    # Townhouse in North/NE test
    res_th = client.get("/api/tab/2?pt=3&region=3")
    assert res_th.status_code == 200
    assert res_th.json()["charts"]["choropleth"]["empty"] is not None


def test_tab3_default(expected):
    res = client.get("/api/tab/3")
    assert res.status_code == 200
    data = res.json()

    assert "charts" in data
    for chart_key in ["price_to_income", "paired_bars", "cagr_comparison", "cagr_by_region"]:
        assert chart_key in data["charts"]

    kpis = {k["id"]: k for k in data["kpis"]}
    assert kpis["pti"]["value"] == expected["price_to_income_index_2566_all"]["TH"]
    assert kpis["inc_cagr"]["value"] == expected["income_cagr_pct"]["TH"]
    assert kpis["hpi_cagr"]["value"] == expected["hpi_all_cagr_pct"]["TH"]


def test_tab3_rebase_2558():
    res = client.get("/api/tab/3?y0=2558&y1=2566")
    assert res.status_code == 200
    data = res.json()

    # Check that in table 3A, all rows for year 2558 have price_to_income_index == 100.0
    table_rows = data["charts"]["price_to_income"]["table"]["rows"]
    rows_2558 = [r for r in table_rows if r[0] == 2558]
    assert len(rows_2558) == 6  # 1 national + 5 regions
    for r in rows_2558:
        pti_val = r[4]
        assert round(pti_val, 1) == 100.0, f"Expected 100.0 at y0=2558, got {pti_val} for {r[1]}"

    # Also check figure traces start at 100.0
    traces = data["charts"]["price_to_income"]["figure"]["data"]
    for trace in traces:
        assert trace["x"][0] == 2558
        assert round(trace["y"][0], 1) == 100.0


def test_invalid_filters():
    # Invalid tab
    res = client.get("/api/tab/4")
    assert res.status_code == 422

    # Invalid year for tab 1
    res = client.get("/api/tab/1?year=2567")
    assert res.status_code == 422
    assert "ไม่มีข้อมูลสำรวจรายได้" in res.json()["detail"]


def test_csv_export():
    res = client.get("/api/export/1/choropleth.csv?year=2566")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    content = res.content
    assert content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    text = content.decode("utf-8-sig")
    assert "ภาค" in text
