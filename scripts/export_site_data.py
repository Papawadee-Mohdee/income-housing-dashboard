"""Export SQLite database to JSON and JavaScript bundle for static site."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "dashboard.db"
GEOJSON_PATH = ROOT / "static" / "regions.geojson"
SITE_DIR = ROOT / "site"
DATA_DIR = SITE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def row_factory(cursor, row):
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}

def export():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = row_factory

    # 1. Meta
    years = con.execute("SELECT year_be, has_income_survey, has_hpi FROM dim_year ORDER BY year_be").fetchall()
    regions = con.execute("SELECT region_id, code, short_th, name_th, is_national, map_order FROM dim_region ORDER BY map_order").fetchall()
    area_types = con.execute("SELECT area_type_id, name_th FROM dim_area_type ORDER BY area_type_id").fetchall()
    property_types = con.execute("SELECT property_type_id, code, name_th FROM dim_property_type ORDER BY property_type_id").fetchall()
    income_years = [y["year_be"] for y in years if y["has_income_survey"]]
    hpi_years = [y["year_be"] for y in years if y["has_hpi"]]
    latest_income = max(income_years)
    latest_hpi_month = con.execute("SELECT month_abbr_th, year_be FROM dim_month ORDER BY month_id DESC LIMIT 1").fetchone()
    
    meta = {
        "years": years,
        "income_years": income_years,
        "hpi_years": hpi_years,
        "regions": regions,
        "area_types": area_types,
        "property_types": property_types,
        "cpi_available": False,
        "as_of": {
            "income_latest_wave": latest_income,
            "hpi_latest_month": f"{latest_hpi_month['month_abbr_th']} {latest_hpi_month['year_be']}",
        },
    }

    # 2. Fact tables
    income = con.execute("""
        SELECT year_be, region_id, area_type_id, monthly_income,
               from_work, current_transfer, property_income, nonmoney_income, noncur_m_income
        FROM fact_income
        ORDER BY region_id, area_type_id, year_be
    """).fetchall()

    hpi_annual = con.execute("""
        SELECT year_be, region_id, property_type_id, index_mean12, index_bot_qtr_end
        FROM fact_hpi_annual
        ORDER BY region_id, property_type_id, year_be
    """).fetchall()

    hpi_monthly = con.execute("""
        SELECT f.month_id, m.year_be, m.month_no, f.region_id, f.property_type_id, f.index_value
        FROM fact_hpi_monthly f
        JOIN dim_month m ON m.month_id = f.month_id
        ORDER BY f.region_id, f.property_type_id, f.month_id
    """).fetchall()

    con.close()

    # 3. GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # Write individual JSONs
    with open(DATA_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    with open(DATA_DIR / "income.json", "w", encoding="utf-8") as f:
        json.dump(income, f, ensure_ascii=False)

    with open(DATA_DIR / "hpi_annual.json", "w", encoding="utf-8") as f:
        json.dump(hpi_annual, f, ensure_ascii=False)

    with open(DATA_DIR / "hpi_monthly.json", "w", encoding="utf-8") as f:
        json.dump(hpi_monthly, f, ensure_ascii=False)

    with open(DATA_DIR / "regions.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    bundle = {
        "meta": meta,
        "income": income,
        "hpi_annual": hpi_annual,
        "hpi_monthly": hpi_monthly,
        "geojson": geojson,
    }

    with open(DATA_DIR / "dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False)

    # Write data.js for direct file:// access without CORS
    js_content = "window.DASHBOARD_DATA = " + json.dumps(bundle, ensure_ascii=False) + ";"
    with open(DATA_DIR / "data.js", "w", encoding="utf-8") as f:
        f.write(js_content)

    print("OK: Data exported to", DATA_DIR)

if __name__ == "__main__":
    export()
