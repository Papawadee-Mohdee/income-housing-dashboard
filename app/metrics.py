"""Metrics calculations — CAGR, rebase, index ratios.

These are pure functions; no DB access.  Used by the API layer and by tests.
"""
from __future__ import annotations

from typing import Optional


def cagr(v0: float, v1: float, years: int) -> Optional[float]:
    """Compound Annual Growth Rate as a fraction (not percent).

    Returns None if years == 0 or v0 == 0.
    """
    if years == 0 or v0 == 0:
        return None
    return (v1 / v0) ** (1.0 / years) - 1.0


def cagr_pct(v0: float, v1: float, years: int) -> Optional[float]:
    """CAGR as percent, rounded to 2 decimal places."""
    c = cagr(v0, v1, years)
    return round(c * 100, 2) if c is not None else None


def pct_change(v0: float, v1: float) -> Optional[float]:
    """Percent change (v1 relative to v0), rounded to 1 decimal."""
    if v0 == 0:
        return None
    return round(100.0 * (v1 / v0 - 1.0), 1)


def rebase(values: dict[int, float], base_year: int) -> dict[int, float]:
    """Rebase a time-series dict {year: value} so that base_year = 100.

    Returns a new dict.
    """
    b = values.get(base_year)
    if b is None or b == 0:
        return values
    return {y: 100.0 * v / b for y, v in values.items()}


def price_to_income_index(
    hpi: dict[int, float],
    inc: dict[int, float],
    years: list[int],
) -> dict[int, float]:
    """Price-to-income index, rebased so the first year = 100.

    `hpi` and `inc` are {year: index_value} dicts.
    """
    y0 = years[0]
    hpi_base = hpi.get(y0, 1)
    inc_base = inc.get(y0, 1)
    if hpi_base == 0 or inc_base == 0:
        return {}
    return {
        y: 100.0 * (hpi[y] / hpi_base) / (inc[y] / inc_base)
        for y in years
        if y in hpi and y in inc
    }


def income_index(income: float, base_income: float) -> Optional[float]:
    """Income index (base year = 100)."""
    if base_income == 0:
        return None
    return 100.0 * income / base_income


def format_number(value: float, decimals: int = 0) -> str:
    """Format number with comma separators (Thai style)."""
    if decimals == 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def delta_direction(value: float) -> str:
    """Return 'up', 'down', or 'flat'."""
    if value > 0.05:
        return "up"
    elif value < -0.05:
        return "down"
    return "flat"
