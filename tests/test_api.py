"""API Integration & Regression Tests for Income × Housing Dashboard v2."""
import glob
import json
from pathlib import Path
import re
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILE = ROOT / "data" / "expected_values.json"

BANNED_EMOJI_PATTERN = re.compile(
    r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u2190-\u2191\u2193-\u21FF"
    r"\u25B2\u25BC\u2726\u25A4\u2913\u21BA]"
)


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
    assert "control-bar" in res.text
    assert "insights-sidebar" not in res.text
    assert "headline-banner" not in res.text


def test_meta():
    res = client.get("/api/meta")
    assert res.status_code == 200
    data = res.json()
    assert "years" in data
    assert "income_years" in data
    assert "hpi_years" in data
    assert "regions" in data
    assert "property_types" in data
    assert "area_types" in data
    assert "as_of" in data
    assert data["as_of"]["income_latest_wave"] == 2568
    assert len(data["regions"]) == 6


# ──────────────── 7.2 API Cleanliness ────────────────
def test_api_cleanliness():
    for tab in [1, 2, 3]:
        res = client.get(f"/api/tab/{tab}")
        assert res.status_code == 200
        data = res.json()

        # Banned fields from v1
        for banned_field in ["summary", "insights", "table", "headline", "ring"]:
            assert banned_field not in data, f"Found banned field '{banned_field}' in tab {tab} root"

        # Charts structure: only figure, read_guide, note (and optional empty)
        assert "charts" in data
        for cname, cobj in data["charts"].items():
            assert "figure" in cobj, f"Missing 'figure' in chart {cname}"
            assert "read_guide" in cobj, f"Missing 'read_guide' in chart {cname}"
            assert "note" in cobj, f"Missing 'note' in chart {cname}"
            for banned_sub in ["summary", "table", "insights"]:
                assert banned_sub not in cobj, f"Found banned subfield '{banned_sub}' in chart {cname}"

    # Export endpoints must return 404
    export_urls = [
        "/api/export/1/choropleth.csv",
        "/api/export/1/treemap.csv",
        "/api/export/2/trend.csv",
        "/api/export/3/hero.csv",
    ]
    for url in export_urls:
        res = client.get(url)
        assert res.status_code == 404, f"Expected 404 for removed endpoint {url}, got {res.status_code}"


# ──────────────── 7.1 & 7.4 Tab 1 Regression & Base Year ────────────────
def test_tab1_values(expected):
    res = client.get("/api/tab/1?year=2566")
    assert res.status_code == 200
    data = res.json()

    # 4 KPI cards
    assert len(data["kpis"]) == 4
    kpis = {k["id"]: k for k in data["kpis"]}

    # Nominal Income 2566
    assert kpis["income"]["value"] == 29030
    assert kpis["income"]["delta"]["vs"] == "2554"
    assert round(kpis["income"]["delta"]["value"], 1) == 24.9

    # Income CAGR (2554-2566)
    assert kpis["cagr"]["value"] == expected["income_cagr_pct"]["TH"]
    assert kpis["cagr"]["delta"]["vs"] == "2554"

    # Current Transfer Share
    assert kpis["transfer"]["value"] == expected["treemap_shares_2566_national_pct"]["CURRENT_TRANSFER"]

    # Urban-Rural Gap
    assert kpis["gap"]["value"] == expected["urban_rural_gap_pct_2566"]["TH"]

    # Charts present
    for chart_key in ["choropleth", "trend", "heatmap", "treemap"]:
        assert chart_key in data["charts"]


def test_tab1_base_year_2554():
    res = client.get("/api/tab/1?year=2554")
    assert res.status_code == 200
    data = res.json()
    kpis = {k["id"]: k for k in data["kpis"]}

    # When year=2554, CAGR KPI must show "—" and delta must be None
    assert kpis["cagr"]["value"] == "—"
    assert kpis["cagr"]["delta"] is None

    # Income delta should also be None on base year
    assert kpis["income"]["delta"] is None


# ──────────────── 7.3 Treemap Shares Rule ────────────────
def test_treemap_shares_rules(expected):
    # 1. National scope single box (region=0)
    res_nat = client.get("/api/tab/1?year=2566&region=0")
    assert res_nat.status_code == 200
    tree_fig_nat = res_nat.json()["charts"]["treemap"]["figure"]
    trace_nat = tree_fig_nat["data"][0]
    customdata_nat = trace_nat.get("customdata", [])

    # Check work share value = 70.5% (from expected_values.json)
    work_shares = [cd[0] for cd in customdata_nat if "ทำงาน" in str(cd[1])]
    assert len(work_shares) > 0
    assert round(work_shares[0], 1) == expected["treemap_shares_2566_national_pct"]["FROM_WORK"]

    # Sum of shares for national must be 100 ± 0.1%
    total_share = sum(cd[0] for cd in customdata_nat)
    assert 99.9 <= total_share <= 100.1, f"Expected 100%, got {total_share}%"

    # 2. Test each individual region (1 to 5)
    for reg_id in range(1, 6):
        res_reg = client.get(f"/api/tab/1?year=2566&region={reg_id}")
        assert res_reg.status_code == 200
        tree_fig_reg = res_reg.json()["charts"]["treemap"]["figure"]
        cd_reg = tree_fig_reg["data"][0].get("customdata", [])
        total_reg = sum(cd[0] for cd in cd_reg)
        assert 99.9 <= total_reg <= 100.1, f"Region {reg_id} sum of shares was {total_reg}%"

    # 3. Default view (5 regions): each region's groups sum to 100 ± 0.1%
    res_def = client.get("/api/tab/1?year=2566")
    assert res_def.status_code == 200
    trace_def = res_def.json()["charts"]["treemap"]["figure"]["data"][0]
    parents_def = trace_def["parents"]
    cd_def = trace_def["customdata"]
    # Group children by parent
    by_parent = {}
    for p, cd in zip(parents_def, cd_def):
        if p != "":  # child group
            by_parent.setdefault(p, []).append(cd[0])
    for parent_id, shares in by_parent.items():
        assert 99.9 <= sum(shares) <= 100.1, f"Parent {parent_id} sum was {sum(shares)}%"


# ──────────────── Tab 2 Regression & Features ────────────────
def test_tab2_values(expected):
    res = client.get("/api/tab/2?year=2566")
    assert res.status_code == 200
    data = res.json()

    assert len(data["kpis"]) == 4
    kpis = {k["id"]: k for k in data["kpis"]}

    # HPI 2566
    assert kpis["hpi"]["value"] == 167.7
    # CAGR
    assert kpis["cagr"]["value"] == expected["hpi_all_cagr_pct"]["TH"]

    # Charts present
    for chart_key in ["choropleth", "trend", "heatmap"]:
        assert chart_key in data["charts"]

    # Monthly grain
    res_m = client.get("/api/tab/2?grain=monthly")
    assert res_m.status_code == 200
    assert len(res_m.json()["charts"]["trend"]["figure"]["data"]) > 0

    # Townhouse in North/NE: empty chart notification
    res_th = client.get("/api/tab/2?pt=3&region=3")
    assert res_th.status_code == 200
    assert res_th.json()["charts"]["choropleth"].get("empty") is not None


def test_tab2_base_year_2554():
    res = client.get("/api/tab/2?year=2554")
    assert res.status_code == 200
    data = res.json()
    kpis = {k["id"]: k for k in data["kpis"]}
    assert kpis["cagr"]["value"] == "—"
    assert kpis["cagr"]["delta"] is None


# ──────────────── Tab 3 Regression & Rebase ────────────────
def test_tab3_values(expected):
    res = client.get("/api/tab/3?y0=2554&y1=2566")
    assert res.status_code == 200
    data = res.json()

    assert len(data["kpis"]) == 4
    kpis = {k["id"]: k for k in data["kpis"]}

    assert kpis["pti"]["value"] == expected["price_to_income_index_2566_all"]["TH"]
    assert kpis["inc_cagr"]["value"] == expected["income_cagr_pct"]["TH"]
    assert kpis["hpi_cagr"]["value"] == expected["hpi_all_cagr_pct"]["TH"]

    # Charts present (All 4 charts in Tab 3)
    assert "hero" in data["charts"]
    assert "cagr" in data["charts"]
    assert "gap_area" in data["charts"]
    assert "scatter" in data["charts"]

    # Test CAGR view modes
    for mode in ["summary", "by_region", "by_type"]:
        res_mode = client.get(f"/api/tab/3?y0=2554&y1=2566&cagr_view={mode}")
        assert res_mode.status_code == 200
        assert len(res_mode.json()["charts"]["cagr"]["figure"]["data"]) >= 2


def test_tab3_rebase_2558():
    res = client.get("/api/tab/3?y0=2558&y1=2566")
    assert res.status_code == 200
    data = res.json()

    hero_traces = data["charts"]["hero"]["figure"]["data"]
    # Verify that in all region line traces, the value at x=2558 is exactly 100.0
    line_traces = [t for t in hero_traces if t.get("mode") and "lines" in t.get("mode")]
    assert len(line_traces) >= 6
    for trace in line_traces:
        idx_2558 = list(trace["x"]).index("2558") if "2558" in trace["x"] else list(trace["x"]).index(2558)
        assert round(trace["y"][idx_2558], 1) == 100.0


# ──────────────── 7.6 Plotly Layout Requirements ────────────────
def test_plotly_layouts():
    for tab in [1, 2, 3]:
        res = client.get(f"/api/tab/{tab}")
        assert res.status_code == 200
        charts = res.json()["charts"]
        for cname, cobj in charts.items():
            fig = cobj["figure"]
            layout = fig.get("layout", {})

            # layout.title must be None or empty
            title = layout.get("title")
            if title is not None:
                if isinstance(title, dict):
                    assert not title.get("text"), f"Tab {tab} chart {cname} has non-empty title.text: {title.get('text')}"
                else:
                    assert not title, f"Tab {tab} chart {cname} has non-empty title: {title}"

            # layout.font.family must start with Anuphan
            font = layout.get("font", {})
            family = font.get("family", "")
            assert "Anuphan" in family, f"Tab {tab} chart {cname} font.family does not contain Anuphan: {family}"

            # yaxis grid on, xaxis grid off (or not present)
            if "yaxis" in layout:
                assert layout["yaxis"].get("showgrid") is True, f"Tab {tab} chart {cname} yaxis.showgrid is not True"
            if "xaxis" in layout:
                assert layout["xaxis"].get("showgrid") in (False, None), f"Tab {tab} chart {cname} xaxis.showgrid is not False/None"


# ──────────────── Section 11 Emoji Check ────────────────
def test_no_banned_emojis():
    # 1. Check template files
    files = (
        glob.glob(str(ROOT / "app" / "templates" / "**/*"), recursive=True)
        + glob.glob(str(ROOT / "static" / "**/*"), recursive=True)
        + glob.glob(str(ROOT / "app" / "**/*"), recursive=True)
    )

    for f in files:
        if f.endswith((".html", ".js", ".css", ".py")) and "pycache" not in f:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
                matches = BANNED_EMOJI_PATTERN.findall(content)
                assert not matches, f"Found banned emojis/symbols in file {f}: {matches}"

    # 2. Check API responses
    endpoints = ["/healthz", "/api/meta", "/api/tab/1", "/api/tab/2", "/api/tab/3"]
    for ep in endpoints:
        res = client.get(ep)
        matches = BANNED_EMOJI_PATTERN.findall(res.text)
        assert not matches, f"Found banned emojis/symbols in response of {ep}: {matches}"
