"""Plotly color palette and layout configuration for dark/light themes (v2 design).

Single source of truth for all chart colors, fonts, and layout defaults.
"""
from __future__ import annotations

# Font family for both UI and Plotly
FONT_FAMILY = "Anuphan, Noto Sans Thai, Sarabun, system-ui, sans-serif"

# ──────────────────────────────────────── Region colors (constant across charts)
REGION_COLORS = {
    "dark": {
        "กทม.+ปริมณฑล": "#5B8CFF",
        "กลาง": "#3CCBE8",
        "เหนือ": "#A99DFF",
        "อีสาน": "#FFC04D",
        "ใต้": "#FF8A3D",
        "ทั่วประเทศ": "#8FA0BC",
    },
    "light": {
        "กทม.+ปริมณฑล": "#2F6BFF",
        "กลาง": "#18B8D8",
        "เหนือ": "#8B7CF6",
        "อีสาน": "#F5A524",
        "ใต้": "#FF7A1A",
        "ทั่วประเทศ": "#8FA0BC",
    },
}

# ──────────────────────────────────────── Treemap income source colors (4 groups)
INCOME_SOURCE_COLORS = {
    "dark": {
        "จากการทำงาน": "#3B63D9",
        "เงินโอน/สวัสดิการ": "#5B8CFF",
        "ไม่เป็นตัวเงิน": "#8FB0FF",
        "อื่น ๆ": "#2A3A5E",
    },
    "light": {
        "จากการทำงาน": "#173DA8",
        "เงินโอน/สวัสดิการ": "#2F6BFF",
        "ไม่เป็นตัวเงิน": "#85B2FF",
        "อื่น ๆ": "#D6E6FF",
    },
}

# ──────────────────────────────────────── Semantic Colors
SEMANTIC_COLORS = {
    "dark": {
        "income": "#5B8CFF",
        "housing": "#FF8A3D",
        "positive": "#34D399",
        "negative": "#F87171",
        "neutral": "#8FA0BC",
    },
    "light": {
        "income": "#2F6BFF",
        "housing": "#FF7A1A",
        "positive": "#0E9F6E",
        "negative": "#E5484D",
        "neutral": "#5E6C84",
    },
}

# ──────────────────────────────────────── Choropleth Scales
# Tab 1: blue #EAF2FF -> #2F6BFF -> #0F2A75
CHOROPLETH_INCOME_SCALE = [
    [0.0, "#EAF2FF"],
    [0.5, "#2F6BFF"],
    [1.0, "#0F2A75"],
]

# Tab 2: orange #FFF1E6 -> #FF8A3D -> #B3470A
CHOROPLETH_HOUSING_SCALE = [
    [0.0, "#FFF1E6"],
    [0.5, "#FF8A3D"],
    [1.0, "#B3470A"],
]

# ──────────────────────────────────────── Heatmap Scales
# Tab 1: Urban-rural gap (0-65% single blue gradient #EAF2FF -> #2F6BFF -> #0F2A75)
HEATMAP_GAP_SCALE = [
    [0.0, "#EAF2FF"],
    [0.5, "#2F6BFF"],
    [1.0, "#0F2A75"],
]

# Tab 2: YoY diverging at 0 (negative = teal #14B8A6, 0 = light gray #F3F4F6 / dark #1F2937, positive = orange up to #B3470A)
def get_heatmap_yoy_scale(theme: str = "dark"):
    zero_color = "#1F2937" if theme == "dark" else "#F3F4F6"
    return [
        [0.0, "#14B8A6"],
        [0.5, zero_color],
        [1.0, "#B3470A"],
    ]

# ──────────────────────────────────────── Tokens
TOKENS = {
    "dark": {
        "bg_from": "#0A0F1A",
        "bg_to": "#0D1424",
        "surface": "#111827",
        "surface_2": "#1A2336",
        "border": "rgba(255,255,255,0.08)",
        "text": "#EAF0FA",
        "text_muted": "#8FA0BC",
        "blue": "#5B8CFF",
        "orange": "#FF8A3D",
        "positive": "#34D399",
        "negative": "#F87171",
        "grid": "rgba(120,140,170,0.18)",
    },
    "light": {
        "bg_from": "#F5F8FD",
        "bg_to": "#EAF0FA",
        "surface": "#FFFFFF",
        "surface_2": "#F1F5FB",
        "border": "rgba(11,27,52,0.08)",
        "text": "#0B1B34",
        "text_muted": "#5E6C84",
        "blue": "#2F6BFF",
        "orange": "#FF7A1A",
        "positive": "#0E9F6E",
        "negative": "#E5484D",
        "grid": "rgba(120,140,170,0.18)",
    },
}


def get_base_layout(theme: str = "dark") -> dict:
    """Return Plotly base layout adhering strictly to v2 specifications."""
    t = TOKENS.get(theme, TOKENS["dark"])
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "title": {"text": ""},  # Requirement: layout.title must be empty for all charts
        "font": {
            "family": FONT_FAMILY,
            "color": t["text_muted"],
            "size": 12.5,
        },
        "xaxis": {
            "gridcolor": "rgba(0,0,0,0)",
            "showgrid": False,
            "zeroline": False,
            "showline": False,
            "tickfont": {"family": FONT_FAMILY, "color": t["text_muted"], "size": 12},
        },
        "yaxis": {
            "gridcolor": t["grid"],
            "showgrid": True,
            "zeroline": False,
            "showline": False,
            "tickfont": {"family": FONT_FAMILY, "color": t["text_muted"], "size": 12},
            "tickformat": ",.0f",  # Requirement: full formatted numbers, no '36k'
        },
        "hoverlabel": {
            "bgcolor": t["surface"],
            "bordercolor": t["text_muted"],
            "font": {"family": FONT_FAMILY, "color": t["text"], "size": 12.5},
        },
        "margin": {"l": 16, "r": 16, "t": 8, "b": 28},
        "separators": ",.",
        "showlegend": False,  # Region buttons act as legend
    }


def get_plotly_config(is_map: bool = False) -> dict:
    """Standard Plotly config."""
    cfg = {
        "displayModeBar": False,
        "displaylogo": False,
        "responsive": True,
    }
    if is_map:
        cfg["scrollZoom"] = True
    return cfg


def region_color(short_th: str, theme: str = "dark") -> str:
    """Get the color for a region name."""
    palette = REGION_COLORS.get(theme, REGION_COLORS["dark"])
    return palette.get(short_th, "#8FA0BC")


def region_dash(is_national: bool) -> str:
    """National line is dashed, regional lines are solid."""
    return "dash" if is_national else "solid"
