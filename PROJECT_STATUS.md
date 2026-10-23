# 📋 Project Status — Income × Housing Dashboard

> อัปเดตล่าสุด: 2026-10-23 15:30

---

## สรุปภาพรวม

| รายการ | สถานะ |
|--------|-------|
| Milestones สำเร็จ | **8 / 8** (100% ครบถ้วนสมบูรณ์) |
| สถานะปัจจุบัน | 🚀 พัฒนาเสร็จสิ้น พร้อมใช้งานและทดสอบผ่านทั้งหมด 16/16 tests |
| เซิร์ฟเวอร์ | ทำงานอยู่ที่ `http://localhost:8000` |

---

## Milestone Tracker

### M0 — ตั้งโปรเจกต์ ติดตั้ง รัน ETL
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** `python etl/build_db.py` จบด้วย "OK database written"

| งาน | สถานะ |
|-----|-------|
| คัดลอกโครงสร้างโปรเจกต์จาก handoff | ✅ เสร็จ |
| สร้าง README.md จากเอกสาร spec | ✅ เสร็จ |
| สร้าง PROJECT_STATUS.md | ✅ เสร็จ |
| ตั้ง virtual environment (.venv) | ✅ เสร็จ |
| ติดตั้ง dependencies (`requirements-dev.txt`) | ✅ เสร็จ |
| รัน `etl/build_db.py` ผ่าน self-test ครบทุกตารางและ view | ✅ เสร็จ |
| สร้าง `.gitignore` และ `pyproject.toml` | ✅ เสร็จ |
| Commit M0 ใน git | ✅ เสร็จ |

---

### M1 — ชั้นข้อมูล (`db.py`, `filters.py`, `metrics.py`)
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** `tests/test_metrics.py` ผ่าน — CAGR และ rebase ตรงกับ `expected_values.json`

| งาน | สถานะ |
|-----|-------|
| สร้าง `app/db.py` — SQLite connection (read-only), query helpers ทุก Tab | ✅ เสร็จ |
| สร้าง `app/filters.py` — filter validation พร้อมข้อความภาษาไทยเมื่อผิดพลาด | ✅ เสร็จ |
| สร้าง `app/metrics.py` — CAGR, rebase, delta, income index, formatters | ✅ เสร็จ |
| สร้าง `tests/test_metrics.py` — ทดสอบเทียบ `expected_values.json` (7 tests) | ✅ เสร็จ |
| รัน `pytest tests/test_metrics.py` ผ่าน 100% | ✅ เสร็จ |

---

### M2 — API Tab 1 + figures + summaries
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** `/api/tab/1` คืน 4 กราฟ, KPI ครบ, สรุปตรงตัวอย่าง

| งาน | สถานะ |
|-----|-------|
| สร้าง `app/main.py` — FastAPI routes (`/`, `/healthz`, `/api/meta`, `/api/tab/{id}`, `/api/export/{tab}/{chart}.csv`) | ✅ เสร็จ |
| สร้าง `app/figures/theme.py` — Dark/Light palette และ Plotly layout ตามข้อกำหนด | ✅ เสร็จ |
| สร้าง `app/figures/tab1.py` — Choropleth (เฉดฟ้า), Treemap, Linear Trend, Heatmap | ✅ เสร็จ |
| สร้าง `app/summaries.py` — ข้อความสรุปภาษาไทยแบบ deterministic ตามเทมเพลต | ✅ เสร็จ |
| สร้าง `tests/test_api.py` — ทดสอบ endpoints และความถูกต้องของข้อมูล (9 tests) | ✅ เสร็จ |

---

### M3 — โครงหน้าเว็บ: เมนู แถบบน ธีมมืด/สว่าง
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** สลับธีมไม่กะพริบ คอนทราสต์ผ่าน AA ทั้งสองโหมด

| งาน | สถานะ |
|-----|-------|
| สร้าง `static/css/tokens.css` — CSS design tokens (Dark/Light mode) | ✅ เสร็จ |
| สร้าง `static/css/app.css` — Modern UI layout, sidebar, topbar, cards, responsive | ✅ เสร็จ |
| ป้องกันการกะพริบของหน้าจอ (Anti-flicker script ใน `<head>`) | ✅ เสร็จ |
| สลับธีม ☀️/🌙 พร้อมบันทึกลง `localStorage` และปรับสีกราฟ Plotly ทันที | ✅ เสร็จ |

---

### M4 — Tab 1 ครบ: เชื่อมกราฟ ปุ่มสรุป ตาราง CSV
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** คลิกภาค/ปีแล้วทุกกราฟ KPI สรุปอัปเดตตามกติกา

| งาน | สถานะ |
|-----|-------|
| ปุ่ม 3 ตัวในทุกการ์ดกราฟ: ✦ สรุป, ▤ ตาราง, ⤓ CSV | ✅ เสร็จ |
| แผงสรุปพับเก็บได้ พร้อมจำสถานะใน `sessionStorage` | ✅ เสร็จ |
| คลิกภาคใน Choropleth / Bar / Treemap แล้วกรองภาคทั้งหน้า | ✅ เสร็จ |
| คลิกปีใน Trend / Heatmap / ชิปปีด้านขวา แล้วอัปเดตปีทั้งหน้า | ✅ เสร็จ |
| ดาวน์โหลด CSV มี UTF-8 BOM สำหรับ Excel ภาษาไทย | ✅ เสร็จ |

---

### M5 — Tab 2 (ดัชนีราคาบ้าน)
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** ทาวน์เฮ้าส์ + เหนือ/อีสาน แสดงข้อความไม่มีข้อมูล ไม่ error

| งาน | สถานะ |
|-----|-------|
| สร้าง `app/figures/tab2.py` — Choropleth (เฉดส้ม), Trend (รายปี/รายเดือน), Heatmap (YoY) | ✅ เสร็จ |
| เส้นอ้างอิง ม.ค. 2566 ในกราฟรายเดือน (เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ) | ✅ เสร็จ |
| รองรับการเลือกประเภทบ้าน: รวมทุกประเภท / บ้านเดี่ยว / ทาวน์เฮ้าส์ | ✅ เสร็จ |
| กรณีทาวน์เฮ้าส์ในภาคเหนือ/อีสาน แสดงข้อความ "ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้" ป้องกัน error | ✅ เสร็จ |

---

### M6 — Tab 3 (รายได้ vs ราคาบ้าน)
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** ค่า CAGR และดัชนีราคา÷รายได้ตรงตาราง rebase ถูกเมื่อเริ่มช่วงที่ 2558

| งาน | สถานะ |
|-----|-------|
| สร้าง `app/figures/tab3.py` — เส้นอัตราส่วนดัชนี (พร้อมแถบซื้อยากขึ้น/ง่ายขึ้น), แท่งคู่, แท่ง CAGR ตลอดช่วง, แท่ง CAGR แยกภาค | ✅ เสร็จ |
| Rebase อัตโนมัติใน Python เมื่อเลือกปีเริ่มต้น `y0 > 2554` (เช่น เริ่ม 2558 ได้ดัชนีปี 2558 = 100 พอดี) | ✅ เสร็จ |
| ทดสอบ `test_tab3_rebase_2558` ผ่านการยืนยัน | ✅ เสร็จ |
| บ่งชี้สถานะ "ซื้อยากขึ้น" (>100) หรือ "ง่ายขึ้น" (<100) ชัดเจน | ✅ เสร็จ |

---

### M7 — ขัดเกลา: a11y, responsive, README
**สถานะ:** ✅ เสร็จสมบูรณ์
**เกณฑ์ผ่าน:** ผ่านรายการตรวจก่อนส่งมอบทั้งหมด

| งาน | สถานะ |
|-----|-------|
| Accessibility: มีโฟกัสริงก์ `:focus-visible`, รองรับคีย์บอร์ด, คอนทราสต์สีผ่านเกณฑ์ | ✅ เสร็จ |
| Responsive Layout: รองรับ Desktop (≥1280px), Tablet (1024px), Mobile (<768px) | ✅ เสร็จ |
| Modal ข้อมูลและระเบียบวิธีวิจัย | ✅ เสร็จ |
| Sync URL query parameters รองรับการคัดลอกและแชร์ลิงก์ | ✅ เสร็จ |
| ผ่านการทดสอบ automated tests ครบ 16/16 รายการ | ✅ เสร็จ |

---

## บันทึกการเปลี่ยนแปลง

| วันที่ / เวลา | เหตุการณ์ |
|--------------|----------|
| 2026-10-23 15:10 | เริ่มต้นโปรเจกต์ — คัดลอกโครงสร้างจาก handoff, สร้าง README.md, สร้าง PROJECT_STATUS.md และ commit M0 |
| 2026-10-23 15:16 | ติดตั้ง dependencies เข้าสู่ `.venv` |
| 2026-10-23 15:19 | รัน `etl/build_db.py` สำเร็จ สร้าง `data/dashboard.db` พร้อม self-test ผ่าน 100% |
| 2026-10-23 15:21 | สร้างชั้นข้อมูล (`db.py`, `filters.py`, `metrics.py`), สร้าง `tests/test_metrics.py` (7 passed) |
| 2026-10-23 15:23 | สร้าง API backend (`main.py`, `summaries.py`, `tab1.py`, `tab2.py`, `tab3.py`) |
| 2026-10-23 15:26 | สร้าง Design tokens (`tokens.css`), สไตล์ (`app.css`), Frontend logic (`app.js`), หน้าเว็บ (`index.html`) |
| 2026-10-23 15:28 | เพิ่มการคำนวณ rebase Tab 3 ตามเงื่อนไข M6 และเพิ่ม `tests/test_api.py` (16 passed) |
| 2026-10-23 15:30 | รันเซิร์ฟเวอร์ Uvicorn สำเร็จที่พอร์ต 8000 และอัปเดต PROJECT_STATUS.md |
