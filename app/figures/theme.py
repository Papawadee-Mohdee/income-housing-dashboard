"""Plotly color palette and layout configuration for dark/light themes.

This is the SINGLE SOURCE OF TRUTH for all chart colors and layout defaults.
"""
from __future__ import annotations

# ──────────────────────────────────────── Region colors (constant across tabs/themes)
REGION_COLORS = {
    "dark": {
        "กทม.+ปริมณฑล": "#4F8FF7",
        "กลาง": "#22D3EE",
        "เหนือ": "#A78BFA",
        "อีสาน": "#FFB347",
        "ใต้": "#FF7A2E",
        "ทั่วประเทศ": "#94A3B8",
    },
    "light": {
        "กทม.+ปริมณฑล": "#2563EB",
        "กลาง": "#0891B2",
        "เหนือ": "#7C3AED",
        "อีสาน": "#D97706",
        "ใต้": "#E8590C",
        "ทั่วประเทศ": "#64748B",
    },
}

# Income = blue, Housing = orange
SEMANTIC_COLORS = {
    "dark": {"income": "#4F8FF7", "housing": "#FF7A2E", "positive": "#34D399", "negative": "#F87171", "warning": "#FBBF24"},
    "light": {"income": "#2563EB", "housing": "#E8590C", "positive": "#059669", "negative": "#DC2626", "warning": "#B45309"},
}

# Choropleth color scales
CHOROPLETH_INCOME = [  # blue shades
    [0, "#C7DBFF"], [0.25, "#8BB8FF"], [0.5, "#4F8FF7"], [0.75, "#2F6FEB"], [1, "#1D4ED8"],
]
CHOROPLETH_HOUSING = [  # orange shades
    [0, "#FFE4CC"], [0.25, "#FFBF85"], [0.5, "#FF7A2E"], [0.75, "#E8590C"], [1, "#C2410C"],
]

CHOROPLETH_INCOME_LIGHT = [
    [0, "#DBEAFE"], [0.25, "#93C5FD"], [0.5, "#3B82F6"], [0.75, "#2563EB"], [1, "#1D4ED8"],
]
CHOROPLETH_HOUSING_LIGHT = [
    [0, "#FED7AA"], [0.25, "#FDBA74"], [0.5, "#F97316"], [0.75, "#EA580C"], [1, "#C2410C"],
]

# Heatmap diverging (blue → neutral → orange, no red/green)
HEATMAP_DIVERGING = [
    [0, "#2563EB"], [0.5, "#F2F5FA"], [1, "#FF7A2E"],
]
HEATMAP_DIVERGING_DARK = [
    [0, "#4F8FF7"], [0.5, "#1D232C"], [1, "#FF7A2E"],
]

# ──────────────────────────────────────── Tokens
TOKENS = {
    "dark": {
        "bg": "#0E1116",
        "surface": "#161B22",
        "surface_2": "#1D232C",
        "border": "#2B3340",
        "text": "#EEF1F6",
        "text_muted": "#9AA6B8",
        "blue": "#4F8FF7",
        "orange": "#FF7A2E",
        "font_family": "IBM Plex Sans Thai, Noto Sans Thai, Sarabun, system-ui, sans-serif",
    },
    "light": {
        "bg": "#F2F5FA",
        "surface": "#FFFFFF",
        "surface_2": "#EDF1F8",
        "border": "#D9E0EC",
        "text": "#0F1B2D",
        "text_muted": "#546178",
        "blue": "#2563EB",
        "orange": "#E8590C",
        "font_family": "IBM Plex Sans Thai, Noto Sans Thai, Sarabun, system-ui, sans-serif",
    },
}


def get_base_layout(theme: str = "dark") -> dict:
    """Return a Plotly layout dict for the given theme."""
    t = TOKENS[theme]
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": t["font_family"],
            "color": t["text_muted"],
            "size": 13,
        },
        "title": {"font": {"color": t["text"], "size": 16}},
        "xaxis": {
            "gridcolor": t["border"],
            "zerolinecolor": t["border"],
            "tickfont": {"color": t["text_muted"]},
        },
        "yaxis": {
            "gridcolor": t["border"],
            "zerolinecolor": t["border"],
            "tickfont": {"color": t["text_muted"]},
        },
        "coloraxis": {"colorbar": {"tickfont": {"color": t["text_muted"]}}},
        "margin": {"l": 50, "r": 30, "t": 50, "b": 40},
        "hoverlabel": {
            "bgcolor": t["surface"],
            "font": {"color": t["text"], "family": t["font_family"]},
            "bordercolor": t["border"],
        },
        "legend": {
            "font": {"color": t["text_muted"]},
            "bgcolor": "rgba(0,0,0,0)",
        },
        "separators": ",.",
    }


def get_plotly_config() -> dict:
    """Standard Plotly config for all charts."""
    return {
        "displaylogo": False,
        "responsive": True,
        "locale": "th",
    }


def region_color(short_th: str, theme: str = "dark") -> str:
    """Get the color for a region name."""
    return REGION_COLORS.get(theme, REGION_COLORS["dark"]).get(short_th, "#94A3B8")


def region_dash(is_national: bool) -> str:
    """National line is dashed, regional lines are solid."""
    return "dash" if is_national else "solid"
