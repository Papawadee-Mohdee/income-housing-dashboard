-- income-housing-dashboard : relational schema (SQLite 3; ANSI-style so it ports to PostgreSQL)
-- Years are Buddhist Era (พ.ศ.). Base year of every index = 2554 (=100).
-- Rebuild everything with:  python etl/build_db.py

PRAGMA foreign_keys = ON;

-- ============================================================
-- 0. Dataset registry (lineage)
-- ============================================================
CREATE TABLE meta_dataset (
    dataset_id        TEXT PRIMARY KEY,           -- 'income_ses' | 'hpi_bot'
    name_th           TEXT NOT NULL,
    source_org        TEXT NOT NULL,
    source_ref        TEXT,                       -- table/series code
    file_name         TEXT NOT NULL,
    frequency         TEXT NOT NULL,              -- 'biennial' | 'monthly'
    unit              TEXT NOT NULL,
    base_year_be      INTEGER,                    -- index base year, NULL for money values
    coverage_start_be INTEGER NOT NULL,
    coverage_end_be   INTEGER NOT NULL,
    notes             TEXT
);

-- ============================================================
-- 1. Dimensions
-- ============================================================
CREATE TABLE dim_year (
    year_be           INTEGER PRIMARY KEY,
    year_ce           INTEGER NOT NULL,
    has_income_survey INTEGER NOT NULL CHECK (has_income_survey IN (0,1)),
    has_hpi           INTEGER NOT NULL CHECK (has_hpi IN (0,1))
);

CREATE TABLE dim_month (
    month_id       INTEGER PRIMARY KEY,           -- year_be*100 + month_no, e.g. 255401
    year_be        INTEGER NOT NULL REFERENCES dim_year(year_be),
    month_no       INTEGER NOT NULL CHECK (month_no BETWEEN 1 AND 12),
    month_abbr_th  TEXT    NOT NULL,
    quarter_no     INTEGER NOT NULL CHECK (quarter_no BETWEEN 1 AND 4),
    is_quarter_end INTEGER NOT NULL CHECK (is_quarter_end IN (0,1)),
    UNIQUE (year_be, month_no)
);

-- One region list shared by both datasets. region_id = SES CODE_REGION.
CREATE TABLE dim_region (
    region_id       INTEGER PRIMARY KEY,          -- 0 national, 1 BMR, 2 central, 3 north, 4 north-east, 5 south
    code            TEXT NOT NULL UNIQUE,         -- TH BMR CEN NOR NES SOU
    name_th         TEXT NOT NULL,
    short_th        TEXT NOT NULL,
    name_en         TEXT NOT NULL,
    is_national     INTEGER NOT NULL CHECK (is_national IN (0,1)),
    income_label_th TEXT NOT NULL,                -- wording used in the SES file
    hpi_label_th    TEXT NOT NULL,                -- wording used in the BoT file
    map_order       INTEGER NOT NULL
);

CREATE TABLE dim_area_type (                      -- income dataset only
    area_type_id INTEGER PRIMARY KEY,             -- 0 total, 1 municipal, 2 non-municipal
    name_th      TEXT NOT NULL,
    name_en      TEXT NOT NULL
);

CREATE TABLE dim_property_type (                  -- house price dataset only
    property_type_id INTEGER PRIMARY KEY,
    code             TEXT NOT NULL UNIQUE,        -- ALL | DETACHED | TOWNHOUSE
    name_th          TEXT NOT NULL,
    name_en          TEXT NOT NULL
);

CREATE TABLE dim_income_source (                  -- leaf sources add up to monthly_income
    source_id  INTEGER PRIMARY KEY,
    code       TEXT NOT NULL UNIQUE,              -- column name in the SES file
    name_th    TEXT NOT NULL,
    group_th   TEXT NOT NULL,                     -- treemap parent
    is_leaf    INTEGER NOT NULL CHECK (is_leaf IN (0,1)),
    sort_order INTEGER NOT NULL
);

-- Map helper: province polygons -> region (for dissolving region shapes)
CREATE TABLE ref_province_region (
    province_en TEXT PRIMARY KEY,                 -- GeoJSON property "name"
    region_id   INTEGER NOT NULL REFERENCES dim_region(region_id)
);

-- ============================================================
-- 2. Facts
-- ============================================================
CREATE TABLE fact_income (                        -- baht / household / month, 8 survey waves
    year_be          INTEGER NOT NULL REFERENCES dim_year(year_be),
    region_id        INTEGER NOT NULL REFERENCES dim_region(region_id),
    area_type_id     INTEGER NOT NULL REFERENCES dim_area_type(area_type_id),
    monthly_income   REAL NOT NULL,               -- = current_income + noncur_m_income
    current_income   REAL NOT NULL,               -- = money_income + nonmoney_income
    money_income     REAL NOT NULL,               -- = from_work + current_transfer + property_income
    from_work        REAL NOT NULL,
    current_transfer REAL NOT NULL,
    property_income  REAL NOT NULL,
    nonmoney_income  REAL NOT NULL,
    noncur_m_income  REAL NOT NULL,
    PRIMARY KEY (year_be, region_id, area_type_id)
);

CREATE TABLE fact_hpi_monthly (                   -- index, 2554 = 100
    month_id         INTEGER NOT NULL REFERENCES dim_month(month_id),
    region_id        INTEGER NOT NULL REFERENCES dim_region(region_id),
    property_type_id INTEGER NOT NULL REFERENCES dim_property_type(property_type_id),
    index_value      REAL NOT NULL,
    PRIMARY KEY (month_id, region_id, property_type_id)
);

-- Derived by the ETL from fact_hpi_monthly (full years only)
CREATE TABLE fact_hpi_annual (
    year_be           INTEGER NOT NULL REFERENCES dim_year(year_be),
    region_id         INTEGER NOT NULL REFERENCES dim_region(region_id),
    property_type_id  INTEGER NOT NULL REFERENCES dim_property_type(property_type_id),
    index_mean12      REAL NOT NULL,              -- DEFAULT: average of the 12 monthly values (2554 = 100.0)
    index_bot_qtr_end REAL NOT NULL,              -- BoT footnote method: average of Mar/Jun/Sep/Dec values
    PRIMARY KEY (year_be, region_id, property_type_id)
);

CREATE INDEX ix_hpi_monthly_region ON fact_hpi_monthly(region_id, property_type_id);
CREATE INDEX ix_income_region      ON fact_income(region_id, area_type_id);

-- ============================================================
-- 3. Views (one per chart family)
-- ============================================================

-- Treemap: leaf income sources in long form with share of the row total
CREATE VIEW v_income_long AS
SELECT f.year_be, f.region_id, f.area_type_id,
       s.source_id, s.code AS source_code, s.name_th AS source_name_th, s.group_th,
       CASE s.code
            WHEN 'FROM_WORK'        THEN f.from_work
            WHEN 'CURRENT_TRANSFER' THEN f.current_transfer
            WHEN 'PROPERTY_INCOME'  THEN f.property_income
            WHEN 'NONMONEY_INCOME'  THEN f.nonmoney_income
            WHEN 'NONCUR_M_INCOME'  THEN f.noncur_m_income
       END AS amount_baht,
       f.monthly_income
FROM fact_income f
CROSS JOIN dim_income_source s
WHERE s.is_leaf = 1;

-- Income index (base = first survey year, 2554 = 100), per region and area type
CREATE VIEW v_income_index AS
SELECT f.year_be, f.region_id, f.area_type_id, f.monthly_income,
       100.0 * f.monthly_income / b.monthly_income AS income_index
FROM fact_income f
JOIN fact_income b
  ON b.year_be = (SELECT MIN(year_be) FROM fact_income)
 AND b.region_id = f.region_id
 AND b.area_type_id = f.area_type_id;

-- Heat map: urban premium over rural, in percent
CREATE VIEW v_income_urban_rural_gap AS
SELECT u.year_be, u.region_id,
       100.0 * (u.monthly_income - r.monthly_income) / r.monthly_income AS gap_pct
FROM fact_income u
JOIN fact_income r
  ON r.year_be = u.year_be AND r.region_id = u.region_id AND r.area_type_id = 2
WHERE u.area_type_id = 1;

-- Year-on-year change of the annual house price index
CREATE VIEW v_hpi_yoy AS
SELECT a.year_be, a.region_id, a.property_type_id,
       a.index_mean12,
       100.0 * (a.index_mean12 / p.index_mean12 - 1.0) AS yoy_pct
FROM fact_hpi_annual a
LEFT JOIN fact_hpi_annual p
  ON p.year_be = a.year_be - 1 AND p.region_id = a.region_id AND p.property_type_id = a.property_type_id;

-- Tab 3: price-to-income index. >100 = house prices grew faster than income since 2554 (harder to buy).
-- hpi_index is rebased so the first survey year (2554) = exactly 100, like income_index.
-- Only years with an income survey wave exist here (no interpolation).
CREATE VIEW v_price_to_income AS
SELECT i.year_be, i.region_id, h.property_type_id,
       i.income_index,
       100.0 * h.index_mean12 / b.index_mean12 AS hpi_index,
       100.0 * (h.index_mean12 / b.index_mean12) / (i.income_index / 100.0) AS price_to_income_index
FROM v_income_index i
JOIN fact_hpi_annual h
  ON h.year_be = i.year_be AND h.region_id = i.region_id
JOIN fact_hpi_annual b
  ON b.year_be = (SELECT MIN(year_be) FROM fact_income)
 AND b.region_id = h.region_id AND b.property_type_id = h.property_type_id
WHERE i.area_type_id = 0;
