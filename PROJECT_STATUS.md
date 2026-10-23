# 📋 Project Status — Income × Housing Dashboard

> อัปเดตล่าสุด: 2026-10-23 16:30 (งานแก้ไขรอบ 2 สำเร็จครบ 100%)

---

## สรุปภาพรวม

| รายการ | สถานะ |
|--------|-------|
| งานแก้ไขรอบ 2 (v2 Redesign & Bug Fixes) | **10 / 10 บั๊ก & 5 ข้อกำหนดหลัก** (100% ครบถ้วนสมบูรณ์) |
| สถานะการทดสอบอัตโนมัติ (pytest) | 🚀 ผ่านทั้งหมด **20 / 20 tests** (100% Pass) |
| ตรวจรับทางสายตา (Visual Verification) | 📸 บันทึกภาพหน้าจอขนาด 1440×900 ครบทั้ง 6 ภาพใน `docs/screenshots/` |
| ความสะอาดของสัญลักษณ์ | ✨ ตรวจสอบไม่พบอีโมจิหรือสัญลักษณ์ต้องห้ามในโค้ดทั้งหมด (Zero Emojis, 100% Inline Lucide SVGs) |

---

## ผลการดำเนินงานแก้ไขรอบ 2 (Round 2 Fixes)

### 1. แก้ไข 10 บั๊กจากรอบ 1 (ครบทุกข้อ)
1. **ปีเริ่มต้นและ CAGR ปีฐาน:** ค่าเริ่มต้นเป็น `year=2566` (ช่วง 2554–2566) เมื่อเลือกปี 2554 KPI CAGR แสดง `"—"` (ปีฐาน) และซ่อนชิป delta
2. **สัดส่วน Treemap:** คำนวณเป็นส่วน ÷ ยอดรวมของ parent เดียวกันโดยตรง ขอบเขตทั่วประเทศใช้แถว `region_id = 0` ไม่มีการบวกสัดส่วน 5 ภาค ผลรวมหมวดหมู่ = 100.0% (สัดส่วนรายได้จากการทำงานทั่วประเทศปี 2566 = 70.5% ตรงตาม `expected_values.json`)
3. **ชื่อกราฟไม่ซ้ำซ้อน:** กำหนด `layout.title = None` ทุกกราฟของ Plotly ใช้หัวการ์ด HTML อย่างเดียว
4. **Header ไม่ถูกตัด:** แก้ไข `padding-top` และ sticky header ให้แสดงผล "1 · รายได้ครัวเรือน (สสช.)" สมบูรณ์ ไม่ทับเนื้อหา
5. **แผนที่ขนาดใหญ่สมส่วน:** ใช้ `go.Choroplethmap` (carto-positron / carto-darkmatter) พร้อม Overlay ป้ายชื่อภาคด้วย `go.Scattermap` ขนาดแผนที่กินพื้นที่ ≥ 75% ของการ์ด
6. **Treemap ดีไซน์ใหม่:** กล่องภาค outline โค้งมน ใบย่อยแบ่ง 4 หมวด (จากการทำงาน, เงินโอน/สวัสดิการ, ไม่เป็นตัวเงิน, อื่น ๆ) ใช้เฉดสีฟ้า 4 ระดับตามแหล่งรายได้
7. **Heatmap สีอ่านง่าย:** Tab 1 ใช้ Single Blue Gradient (`#EAF2FF` → `#2F6BFF` → `#0F2A75`); Tab 2 ใช้ Diverging Scale รอบค่า 0 (ติดลบ = สีเขียวหัวเป็ด `#14B8A6`, ขยายตัว = สีส้ม `#FF7A1A` → `#B3470A`)
8. **ฟอนต์เอกภาพ:** ใช้ Google Font **Anuphan** ฟอนต์เดียวทั้งระบบ (UI, Plotly `layout.font.family`, `hoverlabel`) พร้อมตัวเลข `tabular-nums`
9. **ไอคอน Lucide SVG แทนอีโมจิ:** เปลี่ยนไอคอนเมนูและปุ่มทั้งหมดเป็น inline SVG (stroke 1.75, 18–20px) ไร้อีโมจิ 100%
10. **การ์ด KPI ได้สัดส่วน:** หัวข้อ 12.5px บรรทัดเดียว, ตัวเลข 34px/700, หน่วยอยู่ใต้ตัวเลข, ชิปแสดงการเปลี่ยนแปลงอยู่ด้านล่างสุด ไม่มีการตัดบรรทัดผิดตำแหน่ง

---

### 2. ตัดส่วนที่ไม่จำเป็นออก (Clean Minimal v2)
- นำปุ่ม ✦สรุป ▤ตาราง ⤓CSV และแผงสรุปในการ์ดออก
- นำแผง Insights ด้านขวา, แบนเนอร์ 💡 และวงแหวน % ออก
- Backend: ลบ `app/summaries.py`, ลบฟิลด์ `summary`, `insights`, `table` ใน API responses, ลบ endpoints `/api/export/*` ทั้งหมด (คืนค่า 404)

---

### 3. แถบควบคุม Sticky Control Bar ใหม่
- **แผงเลือกภูมิภาค (Radio Group):** [ทั้งประเทศ] [กทม.+ปริมณฑล] [กลาง] [เหนือ] [อีสาน] [ใต้] มีจุดสีประจำภาค กดซ้ำที่ภาคเดิมจะย้อนกลับ "ทั้งประเทศ"
- **ชิปเลือกปี:** แถบเลื่อนชิปปี (Tab 1: 8 รอบสำรวจ, Tab 2: 15 ปี, Tab 3: เลือกปีเริ่มต้นและปีสิ้นสุด)
- **ตัวเลือกเฉพาะแท็บ:** Tab 1 เลือกประเภทเขต, Tab 2/3 เลือกประเภทที่อยู่อาศัย
- **ปุ่ม Ghost "ล้างตัวกรอง":** ปรากฏเฉพาะเมื่อตัวกรองต่างจากค่าเริ่มต้น

---

### 4. Tab 3 ปรับดีไซน์ตาม Section 10
- **Hero Price-to-Income Line Chart (ความสูง 420px):** Rebase ให้ปีเริ่มต้น = 100 เสมอ มีเส้นอ้างอิง 100 พร้อมแรเงาสีส้มด้านบน ("ซื้อยากขึ้น") และสีฟ้าด้านล่าง ("ซื้อง่ายขึ้น") เส้นของภาคที่เลือกหนา 4px
- **CAGR Comparison Chart (ความสูง 360px):** Segmented switch สลับระหว่าง [แยกตามภาค | แยกตามประเภทบ้าน] พร้อมเส้นแบ่งภาพรวมทั้งประเทศ
- **CPI Availability Check:** ตรวจสอบตาราง `fact_cpi` หากไม่มีจะส่ง `cpi_available: false` พร้อมแสดงหมายเหตุชี้แจง

---

### 5. การตรวจรับทางสายตา (Visual Screenshots)
ภาพหน้าจอขนาด 1440×900 บันทึกไว้ใน `docs/screenshots/`:
1. `01_tab1_light_default.png` — Tab 1 โหมดสว่าง ค่าเริ่มต้น (ปี 2566)
2. `02_tab1_light_isan.png` — Tab 1 โหมดสว่าง เลือกภาคอีสาน
3. `03_tab1_dark_default.png` — Tab 1 โหมดมืด ค่าเริ่มต้น
4. `04_tab2_light_default.png` — Tab 2 โหมดสว่าง ค่าเริ่มต้น
5. `05_tab2_dark_default.png` — Tab 2 โหมดมืด ค่าเริ่มต้น
6. `06_tab3_dark_default.png` — Tab 3 โหมดมืด ค่าเริ่มต้น

---

### 6. ผลการทดสอบ (Automated Test Suite)
รัน `pytest -v` ครบถ้วน 20 รายการ:
```
tests/test_api.py::test_healthz PASSED
tests/test_api.py::test_index_page PASSED
tests/test_api.py::test_meta PASSED
tests/test_api.py::test_api_cleanliness PASSED
tests/test_api.py::test_tab1_values PASSED
tests/test_api.py::test_tab1_base_year_2554 PASSED
tests/test_api.py::test_treemap_shares_rules PASSED
tests/test_api.py::test_tab2_values PASSED
tests/test_api.py::test_tab2_base_year_2554 PASSED
tests/test_api.py::test_tab3_values PASSED
tests/test_api.py::test_tab3_rebase_2558 PASSED
tests/test_api.py::test_plotly_layouts PASSED
tests/test_api.py::test_no_banned_emojis PASSED
tests/test_metrics.py::test_income_cagr PASSED
tests/test_metrics.py::test_hpi_all_cagr PASSED
tests/test_metrics.py::test_hpi_cagr_by_type PASSED
tests/test_metrics.py::test_price_to_income_index_2566 PASSED
tests/test_metrics.py::test_urban_rural_gap_2566 PASSED
tests/test_metrics.py::test_treemap_shares_2566 PASSED
tests/test_metrics.py::test_filter_validation PASSED
======================== 20 passed, 1 warning in 2.72s ========================
```
