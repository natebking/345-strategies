"""Hammer and shooter proportion patterns. See SPEC.md section 6.

These are not structures. They describe where the body sits inside the range
and layer on top of any structure.
"""

from __future__ import annotations

from .model import Candle, PatternMethod


def _fractions(c: Candle) -> tuple[float, float, float, float, float]:
    """Body/wick geometry as fractions of the candle's range."""
    r = c.range
    upper_wick = c.high - max(c.open, c.close)
    lower_wick = min(c.open, c.close) - c.low
    body_center = (c.open + c.close) / 2
    return (
        c.body / r,                      # body as a fraction of range
        upper_wick / r,
        lower_wick / r,
        (c.high - body_center) / r,      # body center measured from the high
        (c.high - c.close) / r,          # close measured from the high
    )


def is_hammer(c: Candle, method: PatternMethod = PatternMethod.BROAD,
              require_color: bool = False) -> bool:
    """A candle that rejected its low."""
    if c.range == 0:
        return False
    if require_color and not c.above_open:
        return False

    low_frac_open = (c.open - c.low) / c.range
    low_frac_close = (c.close - c.low) / c.range

    if method is PatternMethod.BROAD:
        # Strictly above the midpoint. A body centered exactly at the midpoint
        # is neither pattern, so a doji at dead center cannot be both.
        return low_frac_open > 0.5 and low_frac_close > 0.5
    if method is PatternMethod.PIN_BAR:
        return low_frac_open >= 0.75 and low_frac_close >= 0.75
    if method is PatternMethod.CLASSIC:
        body_pct, upper_pct, _lower_pct, center_from_high, close_from_high = _fractions(c)
        # A near-zero body does not qualify: the ratio test needs a real body.
        # Matches the reference implementation (bodyPct > 0.001, else ratio 0).
        body_pct2 = c.body / c.range
        wick_ratio = (min(c.open, c.close) - c.low) / c.body if body_pct2 > 0.001 else 0.0
        return (
            body_pct <= 0.30
            and wick_ratio >= 3.0
            and upper_pct <= 0.35
            and center_from_high <= 0.33
            and close_from_high <= 0.25
        )
    raise ValueError(f"unknown method: {method}")


def is_shooter(c: Candle, method: PatternMethod = PatternMethod.BROAD,
               require_color: bool = False) -> bool:
    """A candle that rejected its high."""
    if c.range == 0:
        return False
    if require_color and c.above_open:
        return False

    low_frac_open = (c.open - c.low) / c.range
    low_frac_close = (c.close - c.low) / c.range

    if method is PatternMethod.BROAD:
        return low_frac_open < 0.5 and low_frac_close < 0.5
    if method is PatternMethod.PIN_BAR:
        return low_frac_open <= 0.25 and low_frac_close <= 0.25
    if method is PatternMethod.CLASSIC:
        body_pct, _upper_pct, lower_pct, _center_from_high, _close_from_high = _fractions(c)
        body_pct2 = c.body / c.range
        wick_ratio = (c.high - max(c.open, c.close)) / c.body if body_pct2 > 0.001 else 0.0
        center_from_low = ((c.open + c.close) / 2 - c.low) / c.range
        close_from_low = (c.close - c.low) / c.range
        return (
            body_pct <= 0.30
            and wick_ratio >= 3.0
            and lower_pct <= 0.35
            and center_from_low <= 0.33
            and close_from_low <= 0.25
        )
    raise ValueError(f"unknown method: {method}")
