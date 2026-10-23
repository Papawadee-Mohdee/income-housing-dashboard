#!/usr/bin/env python3
"""Build data/dashboard.db from the two raw files.

    python etl/build_db.py            # from the repository root

Inputs  (data/raw):
    household_income_ses.csv                 NSO household income survey, 8 waves 2554-2568
    bot_house_price_index_monthly.xlsx       Bank of Thailand house price index, monthly 2554-2568 (2554 = 100)
    ../ref/ref_province_region.csv           province -> region reference (for the map)
Output:
    data/dashboard.db                        SQLite, schema in sql/schema.sql
    data/expected_values.json                reference numbers for acceptance tests

Requires: pandas, openpyxl (Python 3.9+). No network access.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "dashboard.db"
SCHEMA = ROOT / "sql" / "schema.sql"

INCOME_CSV = RAW / "household_income_ses.csv"
HPI_XLSX = RAW / "bot_house_price_index_monthly.xlsx"
PROVINCE_CSV = ROOT / "data" / "ref" / "ref_province_region.csv"

MONTHS_TH = {"ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
             "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12}

REGIONS = [
    # id, code, name_th, short_th, name_en, is_national, income_label_th, hpi_label_th, map_order
    (0, "TH", "ทั่วราชอาณาจักร", "ทั่วประเทศ", "Whole Kingdom", 1, "ทั่วราชอาณาจักร", "ทั้งประเทศ", 0),
    (1, "BMR", "กรุงเทพมหานครและปริมณฑล", "กทม.+ปริมณฑล", "Bangkok Metropolitan Region", 0,
     "กรุงเทพมหานคร นนทบุรี ปทุมธานี และสมุทรปราการ", "กรุงเทพ ฯ และปริมณฑล", 1),
    (2, "CEN", "ภาคกลาง", "กลาง", "Central", 0, "กลาง / ภาคกลาง", "ภาคกลาง (ไม่รวมกรุงเทพ ฯ และปริมณฑล)", 2),
    (3, "NOR", "ภาคเหนือ", "เหนือ", "North", 0, "เหนือ / ภาคเหนือ", "ภาคเหนือ", 3),
    (4, "NES", "ภาคตะวันออกเฉียงเหนือ", "อีสาน", "Northeast", 0,
     "ตะวันออกเฉียงเหนือ / ภาคตะวันออกเฉียงเหนือ", "ภาคตะวันออกเฉียงเหนือ", 4),
    (5, "SOU", "ภาคใต้", "ใต้", "South", 0, "ใต้ / ภาคใต้", "ภาคใต้", 5),
]
AREA_TYPES = [(0, "รวม", "Total"), (1, "ในเขตเทศบาล", "Municipal"), (2, "นอกเขตเทศบาล", "Non-municipal")]
PROPERTY_TYPES = [
    (1, "ALL", "รวมทุกประเภทที่อยู่อาศัย", "All residential types"),
    (2, "DETACHED", "บ้านเดี่ยวพร้อมที่ดิน", "Detached house with land"),
    (3, "TOWNHOUSE", "ทาวน์เฮ้าส์พร้อมที่ดิน", "Townhouse with land"),
]
INCOME_SOURCES = [
    # id, code, name_th, group_th, is_leaf, sort_order
    (1, "FROM_WORK", "รายได้จากการทำงาน", "รายได้ที่เป็นตัวเงิน", 1, 1),
    (2, "CURRENT_TRANSFER", "เงินโอน/สวัสดิการ", "รายได้ที่เป็นตัวเงิน", 1, 2),
    (3, "PROPERTY_INCOME", "รายได้จากทรัพย์สิน", "รายได้ที่เป็นตัวเงิน", 1, 3),
    (4, "NONMONEY_INCOME", "รายได้ที่ไม่เป็นตัวเงิน", "รายได้ที่ไม่เป็นตัวเงิน", 1, 4),
    (5, "NONCUR_M_INCOME", "รายได้ที่ไม่ใช่รายรับประจำ (เป็นตัวเงิน)", "รายได้ที่ไม่ใช่รายรับประจำ", 1, 5),
    (6, "MONEY_INCOME", "รายได้ที่เป็นตัวเงิน (รวม)", "รวม", 0, 6),
    (7, "CURRENT_INCOME", "รายได้ประจำ (รวม)", "รวม", 0, 7),
    (8, "MONTHLY_INCOME", "รายได้ทั้งสิ้น (รวม)", "รวม", 0, 8),
]
HPI_GROUPS = {
    "ดัชนีราคารวมทุกประเภทที่อยู่อาศัย": "ALL",
    "ดัชนีราคาบ้านเดี่ยวพร้อมที่ดิน": "DETACHED",
    "ดัชนีราคาทาวน์เฮ้าส์พร้อมที่ดิน": "TOWNHOUSE",
}
HPI_REGION_KEYS = {  # label with all whitespace removed -> region_id
    "ทั้งประเทศ": 0,
    "กรุงเทพฯและปริมณฑล": 1,
    "ภาคกลาง(ไม่รวมกรุงเทพฯและปริมณฑล)": 2,
    "ภาคเหนือ": 3,
    "ภาคตะวันออกเฉียงเหนือ": 4,
    "ภาคใต้": 5,
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", str(s))


# ------------------------------------------------------------------ loaders
def load_income() -> pd.DataFrame:
    df = pd.read_csv(INCOME_CSV, encoding="utf-8-sig")
    need = ["YEAR", "CODE_REGION", "CODE_AREA", "MONTHLY_INCOME", "CURRENT_INCOME", "MONEY_INCOME",
            "FROM_WORK", "CURRENT_TRANSFER", "PROPERTY_INCOME", "NONMONEY_INCOME", "NONCUR_M_INCOME"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        sys.exit(f"income csv is missing columns: {missing}")
    return df[need].astype(float).astype({"YEAR": int, "CODE_REGION": int, "CODE_AREA": int})


def load_hpi() -> pd.DataFrame:
    """Return long format: year_be, month_no, region_id, ptype_code, index_value."""
    raw = pd.read_excel(HPI_XLSX, sheet_name="Monthly", header=None)
    month_re = re.compile(r"^[ก-๙\.]+\s+\d{4}$")
    hdr = next(i for i in range(len(raw))
               if isinstance(raw.iat[i, 2], str) and month_re.match(raw.iat[i, 2].strip()))
    periods = []
    for h in raw.iloc[hdr, 2:]:
        m, y = str(h).split()
        periods.append((int(y), MONTHS_TH[m]))
    rows, group = [], None
    for i in range(hdr + 1, len(raw)):
        label = raw.iat[i, 1]
        if pd.isna(label):
            if group is not None:          # first blank line after the table = end of data
                break
            continue
        values = raw.iloc[i, 2:]
        label_clean = str(label).strip()
        if values.isna().all():            # a group header row
            group = HPI_GROUPS.get(label_clean)
            if group is None:
                sys.exit(f"unknown property-type header: {label_clean!r}")
            continue
        region_id = HPI_REGION_KEYS.get(squash(label_clean))
        if region_id is None:
            sys.exit(f"unknown region label: {label_clean!r}")
        for (y, m), v in zip(periods, values):
            rows.append((y, m, region_id, group, float(v)))
    return pd.DataFrame(rows, columns=["year_be", "month_no", "region_id", "ptype", "index_value"])


# ------------------------------------------------------------------ build
def main() -> None:
    income = load_income()
    hpi = load_hpi()
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    cur = con.cursor()

    years = sorted(set(income.YEAR) | set(hpi.year_be))
    survey_years = set(income.YEAR)
    cur.executemany("INSERT INTO dim_year VALUES (?,?,?,?)",
                    [(y, y - 543, int(y in survey_years), int(y in set(hpi.year_be))) for y in years])
    months = sorted(set(zip(hpi.year_be, hpi.month_no)))
    inv_m = {v: k for k, v in MONTHS_TH.items()}
    cur.executemany("INSERT INTO dim_month VALUES (?,?,?,?,?,?)",
                    [(y * 100 + m, y, m, inv_m[m], (m - 1) // 3 + 1, int(m % 3 == 0)) for y, m in months])
    cur.executemany("INSERT INTO dim_region VALUES (?,?,?,?,?,?,?,?,?)", REGIONS)
    cur.executemany("INSERT INTO dim_area_type VALUES (?,?,?)", AREA_TYPES)
    cur.executemany("INSERT INTO dim_property_type VALUES (?,?,?,?)", PROPERTY_TYPES)
    cur.executemany("INSERT INTO dim_income_source VALUES (?,?,?,?,?,?)", INCOME_SOURCES)
    prov = pd.read_csv(PROVINCE_CSV)
    cur.executemany("INSERT INTO ref_province_region VALUES (?,?)", list(prov.itertuples(index=False, name=None)))

    cur.executemany(
        "INSERT INTO fact_income VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(int(r.YEAR), int(r.CODE_REGION), int(r.CODE_AREA), r.MONTHLY_INCOME, r.CURRENT_INCOME, r.MONEY_INCOME,
          r.FROM_WORK, r.CURRENT_TRANSFER, r.PROPERTY_INCOME, r.NONMONEY_INCOME, r.NONCUR_M_INCOME)
         for r in income.itertuples(index=False)])

    pt_id = {code: pid for pid, code, *_ in PROPERTY_TYPES}
    cur.executemany(
        "INSERT INTO fact_hpi_monthly VALUES (?,?,?,?)",
        [(int(r.year_be) * 100 + int(r.month_no), int(r.region_id), pt_id[r.ptype], r.index_value)
         for r in hpi.itertuples(index=False)])

    # annual index = mean of 12 months (default) and BoT footnote method (mean of quarter-end months)
    ann = []
    for (y, rid, pt), g in hpi.groupby(["year_be", "region_id", "ptype"]):
        if len(g) != 12:
            continue
        qend = g[g.month_no.isin([3, 6, 9, 12])].index_value.mean()
        ann.append((int(y), int(rid), pt_id[pt], float(g.index_value.mean()), float(qend)))
    cur.executemany("INSERT INTO fact_hpi_annual VALUES (?,?,?,?,?)", ann)

    cur.executemany("INSERT INTO meta_dataset VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
        ("income_ses", "รายได้เฉลี่ยต่อเดือนของครัวเรือน จำแนกตามแหล่งที่มาของรายได้",
         "สำนักงานสถิติแห่งชาติ (NSO) การสำรวจภาวะเศรษฐกิจและสังคมของครัวเรือน", "SES_41_01",
         "household_income_ses.csv", "biennial", "บาท/ครัวเรือน/เดือน", None,
         int(income.YEAR.min()), int(income.YEAR.max()),
         "เก็บทุก 2 ปี (8 รอบ) ใช้ CODE_REGION/CODE_AREA เป็นคีย์ ไม่ใช้ชื่อ REGION/AREA เพราะสะกดต่างกันตามปี"),
        ("hpi_bot", "ดัชนีราคาที่อยู่อาศัย", "ธนาคารแห่งประเทศไทย (BoT)", "EC_EI_008_S4",
         "bot_house_price_index_monthly.xlsx", "monthly", "ดัชนี (2554 = 100)", 2554,
         int(hpi.year_be.min()), int(hpi.year_be.max()),
         "Hedonic regression, rolling window + time dummy (เฉลี่ยเคลื่อนที่ 3 เดือน) จากฐานข้อมูลสินเชื่อที่มีที่อยู่อาศัยเป็นหลักประกัน; "
         "เพิ่มสถาบันการเงินเฉพาะกิจตั้งแต่ ม.ค. 2566 (อาจมีรอยต่อของข้อมูล); ทาวน์เฮ้าส์มีเพียง 4 พื้นที่ (ไม่มีเหนือ/อีสาน); "
         "ภาคเหนือและอีสาน: ดัชนีรวมทุกประเภทมีค่าเท่ากับดัชนีบ้านเดี่ยวทุกเดือน (180/180) จึงไม่ควรเทียบประเภทบ้านในสองภาคนี้"),
    ])
    con.commit()
    self_test(con)
    con.close()
    print(f"OK  database written to {DB.relative_to(ROOT)}")


# ------------------------------------------------------------------ tests + reference values
def cagr(v0: float, v1: float, years: int) -> float:
    return (v1 / v0) ** (1.0 / years) - 1.0


def self_test(con: sqlite3.Connection) -> None:
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    assert q("PRAGMA integrity_check")[0][0] == "ok"
    assert q("PRAGMA foreign_key_check") == []
    n = {t: q(f"SELECT COUNT(*) FROM {t}")[0][0] for t in
         ["dim_year", "dim_month", "dim_region", "fact_income", "fact_hpi_monthly", "fact_hpi_annual",
          "ref_province_region"]}
    expect = {"dim_year": 15, "dim_month": 180, "dim_region": 6, "fact_income": 144,
              "fact_hpi_monthly": 180 * 16, "fact_hpi_annual": 15 * 16, "ref_province_region": 76}
    assert n == expect, (n, expect)

    # income rows add up (source rounds to whole baht)
    worst = q("""SELECT MAX(ABS(monthly_income - (from_work + current_transfer + property_income
                                                  + nonmoney_income + noncur_m_income))) FROM fact_income""")[0][0]
    assert worst <= 5, worst
    # the 12-month mean of 2554 is the index base (=100)
    lo, hi = q("SELECT MIN(index_mean12), MAX(index_mean12) FROM fact_hpi_annual WHERE year_be = 2554")[0]
    assert 99.9 <= lo and hi <= 100.1, (lo, hi)
    # North / North-East have no townhouse series: "ALL types" equals "detached" in every month
    for rid in (3, 4):
        same = q("""SELECT COUNT(*) FROM fact_hpi_monthly a
                    JOIN fact_hpi_monthly d ON d.month_id = a.month_id AND d.region_id = a.region_id
                         AND d.property_type_id = 2
                    WHERE a.property_type_id = 1 AND a.region_id = ? AND ABS(a.index_value - d.index_value) < 1e-9""",
                 rid)[0][0]
        assert same == 180, (rid, same)
    assert q("SELECT COUNT(*) FROM v_price_to_income")[0][0] == 16 * 8
    assert q("SELECT ABS(MAX(price_to_income_index) - MIN(price_to_income_index)) FROM v_price_to_income WHERE year_be = 2554")[0][0] < 1e-9
    assert q("SELECT COUNT(*) FROM v_income_urban_rural_gap")[0][0] == 6 * 8

    # reference numbers for acceptance tests (window 2554 -> 2566 = 12 years)
    y0, y1, span = 2554, 2566, 12
    inc = {(r, y): v for r, y, v in q("SELECT region_id, year_be, monthly_income FROM fact_income WHERE area_type_id = 0")}
    hpi = {(r, p, y): v for r, p, y, v in q("SELECT region_id, property_type_id, year_be, index_mean12 FROM fact_hpi_annual")}
    ref = {"window": [y0, y1], "years_span": span, "rule": "annual HPI = mean of 12 months; CAGR = (end/start)^(1/years)-1",
           "income_cagr_pct": {}, "hpi_all_cagr_pct": {}, "hpi_cagr_pct_national_by_type": {},
           "price_to_income_index_2566_all": {}, "urban_rural_gap_pct_2566": {}, "treemap_shares_2566_national_pct": {}}
    for rid, code in [(r[0], r[1]) for r in q("SELECT region_id, code FROM dim_region ORDER BY region_id")]:
        ref["income_cagr_pct"][code] = round(100 * cagr(inc[(rid, y0)], inc[(rid, y1)], span), 2)
        ref["hpi_all_cagr_pct"][code] = round(100 * cagr(hpi[(rid, 1, y0)], hpi[(rid, 1, y1)], span), 2)
        # rebased at the window start: 100 * (HPI_t / HPI_start) / (Inc_t / Inc_start)
        ref["price_to_income_index_2566_all"][code] = round(
            100 * (hpi[(rid, 1, y1)] / hpi[(rid, 1, y0)]) / (inc[(rid, y1)] / inc[(rid, y0)]), 1)
    for pid, code in [(1, "ALL"), (2, "DETACHED"), (3, "TOWNHOUSE")]:
        ref["hpi_cagr_pct_national_by_type"][code] = round(100 * cagr(hpi[(0, pid, y0)], hpi[(0, pid, y1)], span), 2)
    for code, v in q("SELECT r.code, g.gap_pct FROM v_income_urban_rural_gap g JOIN dim_region r USING(region_id) WHERE g.year_be = 2566"):
        ref["urban_rural_gap_pct_2566"][code] = round(v, 1)
    for code, amt, tot in q("""SELECT source_code, amount_baht, monthly_income FROM v_income_long
                               WHERE year_be = 2566 AND region_id = 0 AND area_type_id = 0"""):
        ref["treemap_shares_2566_national_pct"][code] = round(100 * amt / tot, 1)
    out = ROOT / "data" / "expected_values.json"
    out.write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
    print("row counts:", n)
    print("max |income - sum of 5 sources| =", worst, "baht")
    print(json.dumps(ref, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
