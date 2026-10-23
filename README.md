# Income × Housing Dashboard

> แดชบอร์ดภาษาไทยบนเว็บสำหรับวิเคราะห์ **รายได้ครัวเรือน** (สสช.) เทียบกับ **ดัชนีราคาที่อยู่อาศัย** (ธปท.) ช่วงปี **พ.ศ. 2554–2566**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.20+-3F4F75?logo=plotly&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.45-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🎯 เป้าหมาย

ตอบ 3 คำถามหลักผ่าน 3 แท็บ:

| แท็บ | คำถาม | ข้อมูล |
|------|--------|--------|
| **1 — รายได้ครัวเรือน** | โครงสร้างและทิศทางรายได้ครัวเรือนไทยเป็นอย่างไร? ใครอยู่ตรงไหนของความเหลื่อมล้ำทางพื้นที่? | สสช. SES (`income_ses`) |
| **2 — ดัชนีราคาบ้าน** | ราคาบ้านในแต่ละพื้นที่เปลี่ยนไปอย่างไร? ภาคไหนและประเภทบ้านไหนโตเร็ว? | ธปท. HPI (`hpi_bot`) |
| **3 — รายได้ vs ราคาบ้าน** | ซื้อบ้านยากขึ้นหรือง่ายขึ้น เมื่อเทียบการเติบโตของรายได้กับราคาบ้าน? | ทั้งสองชุด |

### ประเภทกราฟ
- **Choropleth** — แผนที่ภาคแสดงตัวชี้วัดแบบไล่เฉดสี
- **Treemap** — สัดส่วนแหล่งที่มาของรายได้
- **Linear Trend** — แนวโน้มรายได้ / ดัชนีราคาตามเวลา
- **Heat Map** — เปรียบเทียบภาค × ปี (ช่องว่างเมือง-ชนบท, YoY)
- **แท่งคู่ / CAGR** — เปรียบเทียบอัตราเติบโตรายได้ vs ราคาบ้าน

---

## 📊 ชุดข้อมูล

| รหัส | ข้อมูล | หน่วยงาน | ความถี่ | ช่วงเวลา |
|------|--------|----------|---------|----------|
| `income_ses` | รายได้เฉลี่ยต่อเดือนของครัวเรือน (บาท) จำแนกตามแหล่งที่มา | สำนักงานสถิติแห่งชาติ (สสช.) | ทุก 2 ปี (8 รอบ) | 2554–2568 |
| `hpi_bot` | ดัชนีราคาที่อยู่อาศัย (2554 = 100) แยกภาค/ประเภทบ้าน | ธนาคารแห่งประเทศไทย (ธปท.) | รายเดือน (180 เดือน) | ม.ค. 2554 – ธ.ค. 2568 |
| `ref_geo` | ขอบเขตภาค 5 พื้นที่ สำหรับแผนที่ Choropleth | สร้างจากขอบเขต 76 จังหวัด | คงที่ | — |

> **ช่วงวิเคราะห์เริ่มต้น: 2554–2566** ฐานข้อมูลมีถึง 2568 สำหรับตัวเลือกเพิ่มเติม

---

## 🏗️ สถาปัตยกรรม

```
Browser (HTML + CSS tokens + vanilla JS/Alpine + Plotly.js)
   │  GET /api/tab/{1|2|3}?filters…&theme=dark|light
   ▼
FastAPI (app/main.py)  →  filters.py  →  db.py (sqlite3)  →  metrics.py
                 └→ figures/*.py (plotly.graph_objects)  └→ summaries.py
   ▼
data/dashboard.db   (สร้างโดย etl/build_db.py)
```

### เทคโนโลยีหลัก
- **Backend:** Python 3.11+, FastAPI, Uvicorn, sqlite3, pandas
- **กราฟ:** Plotly (สร้างฝั่ง Python ด้วย `plotly.graph_objects` → JSON → Plotly.js ฝั่งเว็บ)
- **Frontend:** HTML + CSS Design Tokens + Vanilla JS/Alpine.js
- **ฐานข้อมูล:** SQLite 3 (star schema: dim + fact tables + views)

---

## 📁 โครงสร้างโปรเจกต์

```
income-housing-dashboard/
├── app/                        # แอปพลิเคชัน FastAPI
│   ├── main.py                 # entry point & routes
│   ├── db.py                   # database connection & queries
│   ├── filters.py              # filter validation
│   ├── metrics.py              # CAGR, rebase, aggregation
│   ├── summaries.py            # Thai-language auto-summary templates
│   └── figures/                # Plotly figure builders
│       ├── theme.py            # color palette (dark/light)
│       ├── tab1.py             # household income figures
│       ├── tab2.py             # house price index figures
│       └── tab3.py             # income vs housing figures
├── static/                     # Static assets
│   ├── css/tokens.css          # design tokens (dark/light)
│   ├── css/app.css             # app styles
│   ├── js/app.js               # client logic
│   └── regions.geojson         # 5 region polygons (provided)
├── data/                       # Data directory
│   ├── raw/                    # raw source files
│   │   ├── household_income_ses.csv
│   │   └── bot_house_price_index_monthly.xlsx
│   ├── ref/                    # reference tables
│   │   └── ref_province_region.csv
│   ├── dashboard.db            # SQLite database (built by ETL)
│   └── expected_values.json    # acceptance test reference values
├── etl/                        # ETL pipeline
│   ├── build_db.py             # CSV/XLSX → SQLite (with self-test)
│   └── build_regions_geojson.py
├── sql/
│   └── schema.sql              # full DDL (tables + views)
├── tests/                      # pytest tests
│   ├── test_metrics.py         # CAGR & rebase vs expected_values.json
│   └── test_api.py             # API integration tests
├── docs/                       # project documentation
│   ├── 01_PROJECT_SPEC.md      # full specification
│   ├── 02_DATASET_DESCRIPTIONS.md
│   └── 03_DATABASE_SCHEMA.md
├── requirements.txt            # runtime dependencies
├── requirements-dev.txt        # dev/test dependencies
├── HANDOFF.html                # handoff tracker & status
├── PROJECT_STATUS.md           # milestone progress tracker
├── LICENSE                     # MIT License
└── README.md                   # this file
```

---

## 🚀 เริ่มต้นใช้งาน

### 1. ติดตั้ง
```bash
# สร้าง virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# ติดตั้ง dependencies
pip install -r requirements-dev.txt
```

### 2. สร้างฐานข้อมูล (ETL)
```bash
python etl/build_db.py
# ต้องจบด้วย "OK database written" (self-test ผ่าน)
```

### 3. รันเซิร์ฟเวอร์
```bash
uvicorn app.main:app --reload --port 8000
```

เปิดเบราว์เซอร์ที่ `http://localhost:8000`

### 4. ทดสอบ
```bash
pytest tests/
```

---

## 🎨 ระบบดีไซน์

- **สี:** ฟ้า = รายได้ · ส้ม = ราคาบ้าน (ทุกกราฟ)
- **ธีม:** มืด/สว่างสลับได้ (CSS custom properties)
- **ฟอนต์:** IBM Plex Sans Thai
- **สไตล์:** Modern, มุมโค้ง 20px, กริด 8px, รองรับ responsive (≥1280px / 1024px / <768px)

---

## 🗺️ แผนงาน (Milestones)

| # | งาน | สถานะ |
|---|------|-------|
| M0 | ตั้งโปรเจกต์ ติดตั้ง รัน ETL | ⬜ |
| M1 | ชั้นข้อมูล (`db.py`, `filters.py`, `metrics.py`) | ⬜ |
| M2 | API Tab 1 + figures + summaries | ⬜ |
| M3 | โครงหน้าเว็บ: เมนู แถบบน ธีมมืด/สว่าง tokens | ⬜ |
| M4 | Tab 1 ครบ: เชื่อมกราฟ ปุ่มสรุป ตาราง CSV | ⬜ |
| M5 | Tab 2 | ⬜ |
| M6 | Tab 3 | ⬜ |
| M7 | ขัดเกลา: a11y, responsive, README | ⬜ |

> ดูรายละเอียดความคืบหน้าที่ [`PROJECT_STATUS.md`](PROJECT_STATUS.md)

---

## 📐 ค่าอ้างอิงที่ต้องตรงกัน (2554→2566)

| ภาค | CAGR รายได้ | CAGR ราคาบ้าน | ดัชนีราคา÷รายได้ | ช่องว่างเมือง-ชนบท |
|-----|------------|---------------|------------------|-------------------|
| ทั่วประเทศ | 1.87% | 4.40% | 134.2 | 33.8% |
| กทม.+ปริมณฑล | −0.52% | 4.25% | 175.5 | 9.0% |
| กลาง | 3.15% | 4.79% | 120.8 | 14.6% |
| เหนือ | 2.75% | 5.06% | 130.5 | 26.2% |
| อีสาน | 1.78% | 4.73% | 140.8 | 25.4% |
| ใต้ | 0.36% | 3.21% | 139.9 | 15.5% |

---

## ⚠️ ข้อควรระวังสำคัญ

- **ไม่มีราคาบ้านเป็นบาท** — ห้ามแสดง "ราคาบ้านเฉลี่ย" หรือ "กี่ปีของรายได้"
- **ทาวน์เฮ้าส์ไม่มีภาคเหนือ/อีสาน** — แผนที่แสดง "ไม่มีข้อมูล" สีเทา
- **รายได้มีเฉพาะ 8 ปีสำรวจ** — ไม่ interpolate ปีที่ขาด
- **นิยาม กทม.+ปริมณฑล ของ สสช. กับ ธปท. อาจไม่ตรงกัน** — มีหมายเหตุใต้กราฟ Tab 3
- **ตัวเลขเป็นราคาตามปี (nominal)** — ไม่ปรับเงินเฟ้อ

---

## 📄 เอกสาร

- [`docs/01_PROJECT_SPEC.md`](docs/01_PROJECT_SPEC.md) — ข้อกำหนดโปรเจกต์ฉบับเต็ม
- [`docs/02_DATASET_DESCRIPTIONS.md`](docs/02_DATASET_DESCRIPTIONS.md) — คำอธิบายชุดข้อมูลและ Data Quality
- [`docs/03_DATABASE_SCHEMA.md`](docs/03_DATABASE_SCHEMA.md) — ER diagram, views, สูตร, SQL queries

---

## 📝 License

MIT — see [LICENSE](LICENSE)
