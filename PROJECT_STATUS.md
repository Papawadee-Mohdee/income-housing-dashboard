# 📋 Project Status — Income × Housing Dashboard

> อัปเดตล่าสุด: 2026-10-23

---

## สรุปภาพรวม

| รายการ | สถานะ |
|--------|-------|
| Milestones สำเร็จ | 0 / 8 |
| สถานะปัจจุบัน | 🚧 เริ่มต้น — กำลังตั้งค่าโปรเจกต์ |

---

## Milestone Tracker

### M0 — ตั้งโปรเจกต์ ติดตั้ง รัน ETL
**สถานะ:** ⬜ กำลังดำเนินการ
**เกณฑ์ผ่าน:** `python etl/build_db.py` จบด้วย "OK database written"

| งาน | สถานะ |
|-----|-------|
| คัดลอกโครงสร้างโปรเจกต์จาก handoff | ✅ เสร็จ |
| สร้าง README.md จากเอกสาร spec | ✅ เสร็จ |
| สร้าง PROJECT_STATUS.md | ✅ เสร็จ |
| ตั้ง virtual environment | ⬜ รอดำเนินการ |
| ติดตั้ง dependencies | ⬜ รอดำเนินการ |
| รัน `etl/build_db.py` ให้ผ่าน self-test | ⬜ รอดำเนินการ |
| สร้าง `.gitignore` | ⬜ รอดำเนินการ |
| Commit M0 | ⬜ รอดำเนินการ |

---

### M1 — ชั้นข้อมูล (`db.py`, `filters.py`, `metrics.py`)
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** `tests/test_metrics.py` ผ่าน — CAGR และ rebase ตรงกับ `expected_values.json`

| งาน | สถานะ |
|-----|-------|
| สร้าง `app/db.py` — database connection & queries | ⬜ |
| สร้าง `app/filters.py` — filter validation | ⬜ |
| สร้าง `app/metrics.py` — CAGR, rebase, aggregation | ⬜ |
| สร้าง `tests/test_metrics.py` | ⬜ |
| ทดสอบผ่าน | ⬜ |

---

### M2 — API Tab 1 + figures + summaries
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** `/api/tab/1` คืน 4 กราฟ, KPI ครบ, สรุปตรงตัวอย่าง

| งาน | สถานะ |
|-----|-------|
| สร้าง `app/main.py` — FastAPI entry point | ⬜ |
| สร้าง `app/figures/theme.py` — color palette | ⬜ |
| สร้าง `app/figures/tab1.py` — choropleth, treemap, trend, heatmap | ⬜ |
| สร้าง `app/summaries.py` — Thai template summaries | ⬜ |
| สร้าง `tests/test_api.py` | ⬜ |

---

### M3 — โครงหน้าเว็บ: เมนู แถบบน ธีมมืด/สว่าง
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** สลับธีมไม่กะพริบ คอนทราสต์ผ่าน AA ทั้งสองโหมด

| งาน | สถานะ |
|-----|-------|
| สร้าง `static/css/tokens.css` — design tokens | ⬜ |
| สร้าง `static/css/app.css` — app styles | ⬜ |
| สร้าง `app/templates/index.html` — base layout | ⬜ |
| สร้าง `static/js/app.js` — theme toggle, filter chips | ⬜ |

---

### M4 — Tab 1 ครบ: เชื่อมกราฟ ปุ่มสรุป ตาราง CSV
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** คลิกภาค/ปีแล้วทุกกราฟ KPI สรุปอัปเดตตามกติกา

---

### M5 — Tab 2 (ดัชนีราคาบ้าน)
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** ทาวน์เฮ้าส์ + เหนือ/อีสาน แสดงข้อความไม่มีข้อมูล ไม่ error

---

### M6 — Tab 3 (รายได้ vs ราคาบ้าน)
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** ค่า CAGR และดัชนีราคา÷รายได้ตรงตาราง rebase ถูกเมื่อเริ่มช่วงที่ 2558

---

### M7 — ขัดเกลา: a11y, responsive, README
**สถานะ:** ⬜ ยังไม่เริ่ม
**เกณฑ์ผ่าน:** ผ่านรายการตรวจก่อนส่งมอบทั้งหมด

---

## บันทึกการเปลี่ยนแปลง

| วันที่ | เหตุการณ์ |
|--------|----------|
| 2026-10-23 | เริ่มต้นโปรเจกต์ — คัดลอกโครงสร้างจาก handoff, สร้าง README.md, สร้าง PROJECT_STATUS.md |
