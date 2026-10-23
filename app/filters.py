"""Filter validation and defaults for the dashboard API."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Filters:
    """Validated filter set — shared across all tabs."""
    tab: int = 1
    year: int = 2566
    y0: int = 2554
    y1: int = 2566
    region: Optional[int] = None   # None = all regions
    area: int = 0                  # 0=total, 1=municipal, 2=non-municipal
    pt: int = 1                    # property_type_id: 1=ALL, 2=DETACHED, 3=TOWNHOUSE
    metric: str = "income"         # choropleth metric
    grain: str = "yearly"          # yearly | monthly
    theme: str = "dark"

    # Valid ranges
    VALID_TABS = {1, 2, 3}
    VALID_AREAS = {0, 1, 2}
    VALID_PTS = {1, 2, 3}
    VALID_METRICS = {"income", "index", "transfer", "hpi", "yoy", "cagr"}
    VALID_GRAINS = {"yearly", "monthly"}
    VALID_THEMES = {"dark", "light"}
    INCOME_YEARS = {2554, 2556, 2558, 2560, 2562, 2564, 2566, 2568}
    ALL_YEARS = set(range(2554, 2569))

    @classmethod
    def from_params(cls, tab: int, **kwargs) -> "Filters":
        """Create from raw query parameters with validation."""
        f = cls(tab=tab)

        if "year" in kwargs and kwargs["year"] is not None:
            f.year = int(kwargs["year"])
        if "y0" in kwargs and kwargs["y0"] is not None:
            f.y0 = int(kwargs["y0"])
        if "y1" in kwargs and kwargs["y1"] is not None:
            f.y1 = int(kwargs["y1"])
        if "region" in kwargs and kwargs["region"] is not None:
            f.region = int(kwargs["region"])
        if "area" in kwargs and kwargs["area"] is not None:
            f.area = int(kwargs["area"])
        if "pt" in kwargs and kwargs["pt"] is not None:
            f.pt = int(kwargs["pt"])
        if "metric" in kwargs and kwargs["metric"] is not None:
            f.metric = str(kwargs["metric"])
        if "grain" in kwargs and kwargs["grain"] is not None:
            f.grain = str(kwargs["grain"])
        if "theme" in kwargs and kwargs["theme"] is not None:
            f.theme = str(kwargs["theme"])

        f.validate()
        return f

    def validate(self) -> None:
        """Raise ValueError with Thai message if filters are invalid."""
        errors = []
        if self.tab not in self.VALID_TABS:
            errors.append(f"แท็บ {self.tab} ไม่ถูกต้อง (ต้องเป็น 1, 2, หรือ 3)")
        if self.area not in self.VALID_AREAS:
            errors.append(f"ประเภทเขต {self.area} ไม่ถูกต้อง (ต้องเป็น 0, 1, หรือ 2)")
        if self.pt not in self.VALID_PTS:
            errors.append(f"ประเภทบ้าน {self.pt} ไม่ถูกต้อง (ต้องเป็น 1, 2, หรือ 3)")
        if self.theme not in self.VALID_THEMES:
            errors.append(f"ธีม '{self.theme}' ไม่ถูกต้อง (ต้องเป็น dark หรือ light)")
        if self.grain not in self.VALID_GRAINS:
            errors.append(f"ความละเอียด '{self.grain}' ไม่ถูกต้อง (ต้องเป็น yearly หรือ monthly)")
        if self.region is not None and self.region not in range(0, 6):
            errors.append(f"ภาค {self.region} ไม่ถูกต้อง (ต้องเป็น 0-5 หรือไม่ระบุ)")
        if self.year not in self.ALL_YEARS:
            errors.append(f"ปี {self.year} ไม่อยู่ในช่วง 2554-2568")
        if self.y0 not in self.ALL_YEARS:
            errors.append(f"ปีเริ่มต้น {self.y0} ไม่อยู่ในช่วง 2554-2568")
        if self.y1 not in self.ALL_YEARS:
            errors.append(f"ปีสิ้นสุด {self.y1} ไม่อยู่ในช่วง 2554-2568")
        if self.y0 > self.y1:
            errors.append(f"ปีเริ่มต้น ({self.y0}) ต้องไม่มากกว่าปีสิ้นสุด ({self.y1})")
        # Tab 1 and 3: year must be a survey year
        if self.tab in (1, 3) and self.year not in self.INCOME_YEARS:
            errors.append(f"แท็บ {self.tab} ปี {self.year} ไม่มีข้อมูลสำรวจรายได้ (มีเฉพาะปีคี่)")
        if errors:
            raise ValueError(" · ".join(errors))

    def to_dict(self) -> dict:
        return {
            "tab": self.tab,
            "year": self.year,
            "y0": self.y0,
            "y1": self.y1,
            "region": self.region,
            "area": self.area,
            "pt": self.pt,
            "metric": self.metric,
            "grain": self.grain,
            "theme": self.theme,
        }
