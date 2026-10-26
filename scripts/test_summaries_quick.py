import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.filters import Filters
from app.summaries import build_summary

f1 = Filters(tab=1, year=2566, area=0, y0=2554, y1=2566)
for cid in ['t1_map', 't1_trend', 't1_gap', 't1_sources']:
    s = build_summary(1, cid, f1)
    print(f"=== {cid} ===")
    print("Title:", s["title"])
    print("Headline:", s["headline"])
    for b in s["bullets"]:
        print(" -", b)
    print("Caution:", s["caution"])

f2 = Filters(tab=2, year=2568, pt=1, y0=2554, y1=2568)
for cid in ['t2_map', 't2_trend', 't2_yoy']:
    s = build_summary(2, cid, f2)
    print(f"=== {cid} ===")
    print("Title:", s["title"])
    print("Headline:", s["headline"])
    for b in s["bullets"]:
        print(" -", b)
    print("Caution:", s["caution"])

f3 = Filters(tab=3, y0=2554, y1=2566, pt=1)
for cid in ['t3_ratio', 't3_cagr']:
    s = build_summary(3, cid, f3)
    print(f"=== {cid} ===")
    print("Title:", s["title"])
    print("Headline:", s["headline"])
    for b in s["bullets"]:
        print(" -", b)
    print("Caution:", s["caution"])

# Test base year 2554
f_base = Filters(tab=2, year=2554, pt=1)
s_base = build_summary(2, "t2_map", f_base)
print("Base year 2554 headline:", s_base["headline"])
assert "ปี 2554 เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต" in s_base["headline"]

# Test townhouse + North empty
f_empty = Filters(tab=2, year=2566, pt=3, region=3)
s_empty = build_summary(2, "t2_map", f_empty)
print("Empty check:", s_empty["empty"])
assert s_empty["empty"] is not None
assert s_empty["headline"] is None
assert s_empty["bullets"] == []

# Test Isan selected Tab 1
f_isan = Filters(tab=1, year=2566, area=0, region=4)
s_isan = build_summary(1, "t1_map", f_isan)
print("Isan Tab 1 headline:", s_isan["headline"])
print("Isan Tab 1 bullet 0:", s_isan["bullets"][0])
assert "อันดับ 5 จาก 5" in s_isan["bullets"][0] or "อันดับที่ 5 จาก 5" in s_isan["headline"]
assert "22,524" in s_isan["headline"]

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
