#!/usr/bin/env python3
"""Build static/regions.geojson (5 region polygons) for the Plotly choropleth.

    python etl/build_regions_geojson.py                 # downloads the province GeoJSON
    python etl/build_regions_geojson.py --src path.json # or use a local copy

Province boundaries: https://github.com/apisit/thailand.json (file thailandwithdensity.json,
76 provinces, feature property "name" in English). Bueng Kan (split from Nong Khai in 2554) is not a
separate polygon in that file; its area appears to be inside the Nong Khai polygon (the region map shows no gap).

Requires: geopandas, shapely, pandas. Output feature properties: region_id, name_th, short_th, code.
Use in Plotly:  px.choropleth(df, geojson=gj, locations="region_id", featureidkey="properties.region_id")
"""
import argparse
import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = "https://raw.githubusercontent.com/apisit/thailand.json/master/thailandwithdensity.json"
REGIONS = {
    1: ("BMR", "กรุงเทพมหานครและปริมณฑล", "กทม.+ปริมณฑล"),
    2: ("CEN", "ภาคกลาง", "กลาง"),
    3: ("NOR", "ภาคเหนือ", "เหนือ"),
    4: ("NES", "ภาคตะวันออกเฉียงเหนือ", "อีสาน"),
    5: ("SOU", "ภาคใต้", "ใต้"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="local province GeoJSON (default: download)")
    ap.add_argument("--tolerance", type=float, default=0.01, help="simplify tolerance in degrees")
    a = ap.parse_args()
    src = Path(a.src) if a.src else ROOT / "data" / "ref" / "thailand_provinces.geojson"
    if not a.src:
        src.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, src)
    gdf = gpd.read_file(src)
    prov = pd.read_csv(ROOT / "data" / "ref" / "ref_province_region.csv")
    gdf = gdf.merge(prov, left_on="name", right_on="province_en", how="left")
    assert gdf["region_id"].notna().all(), gdf[gdf["region_id"].isna()]["name"].tolist()
    reg = gdf.dissolve(by="region_id").reset_index()
    reg["geometry"] = reg.geometry.simplify(a.tolerance, preserve_topology=True)
    reg["code"] = reg.region_id.map(lambda r: REGIONS[int(r)][0])
    reg["name_th"] = reg.region_id.map(lambda r: REGIONS[int(r)][1])
    reg["short_th"] = reg.region_id.map(lambda r: REGIONS[int(r)][2])
    reg["region_id"] = reg.region_id.astype(int)
    gj = json.loads(reg[["region_id", "code", "name_th", "short_th", "geometry"]].to_json())
    for f in gj["features"]:
        f["id"] = f["properties"]["region_id"]
    out = ROOT / "static" / "regions.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    print(f"OK  {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.0f} KB, {len(gj['features'])} features)")


if __name__ == "__main__":
    main()
