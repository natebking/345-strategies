"""Proportion patterns: hammers, shooters, and the PowerBar core shape.

These are not bar types. A hammer is a hammer whether the candle is a 1, a 2 or
a 3 - the pattern describes where the body sits inside the range, and it layers
on top of whatever the structure test said.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .candles import Candle, CandleMetrics, metrics


class HammerMethod(str, Enum):
    """Which hammer/shooter definition to apply.

    BROAD is the default and the loosest: open and close both in the upper half
    (hammer) or both in the lower half (shooter).
    """

    BROAD = "broad"
    CLASSIC = "classic"
    PIN_BAR = "pin_bar"


# --- Broad -----------------------------------------------------------------

def _broad_hammer(m: CandleMetrics) -> bool:
    # Strict `>` on both sides, deliberately. A body centered exactly at the
    # midpoint satisfies neither this nor the shooter test, so a perfectly
    # centered doji is neither - which is the point. An earlier inclusive
    # version made such a candle satisfy BOTH and draw a spurious level.
    return not m.is_flat and m.open_from_low > 0.50 and m.close_from_low > 0.50


def _broad_shooter(m: CandleMetrics) -> bool:
    return not m.is_flat and m.open_from_low < 0.50 and m.close_from_low < 0.50


# --- Classic ---------------------------------------------------------------

def _classic_hammer(m: CandleMetrics) -> bool:
    if m.is_flat:
        return False
    # The guard tests body_pct (a ratio) but the ratio below divides by body
    # (absolute). That asymmetry is intentional and has a real consequence:
    # a candle whose body is <= 0.1% of its range - the most extreme, most
    # hammer-like doji there is - gets wick_ratio forced to 0 and therefore
    # fails the >= 3.0 test. Keep it; do not "fix" it to `body > 0`.
    wick_ratio = (m.lower_wick / m.body) if m.body_pct > 0.001 else 0.0
    return (
        m.body_pct <= 0.30
        and wick_ratio >= 3.0
        and m.upper_wick_pct <= 0.35
        and m.body_center_from_high <= 0.33
        and m.close_from_high <= 0.25
    )


def _classic_shooter(m: CandleMetrics) -> bool:
    if m.is_flat:
        return False
    wick_ratio = (m.upper_wick / m.body) if m.body_pct > 0.001 else 0.0
    return (
        m.body_pct <= 0.30
        and wick_ratio >= 3.0
        and m.lower_wick_pct <= 0.35
        and m.body_center_from_low <= 0.33
        and m.close_from_low <= 0.25
    )


# --- Pin bar ---------------------------------------------------------------

def _pin_hammer(m: CandleMetrics) -> bool:
    # Inclusive, despite the "strict" name: a body exactly on the 25% boundary
    # qualifies.
    return not m.is_flat and m.close_from_high <= 0.25 and m.open_from_high <= 0.25


def _pin_shooter(m: CandleMetrics) -> bool:
    return not m.is_flat and m.close_from_low <= 0.25 and m.open_from_low <= 0.25


_DETECTORS = {
    HammerMethod.BROAD: (_broad_hammer, _broad_shooter),
    HammerMethod.CLASSIC: (_classic_hammer, _classic_shooter),
    HammerMethod.PIN_BAR: (_pin_hammer, _pin_shooter),
}


def hammer_shooter(
    candle: Candle,
    *,
    method: HammerMethod = HammerMethod.BROAD,
    match_color: bool = False,
) -> Tuple[bool, bool]:
    """Test one candle for a hammer and a shooter.

    Returns `(is_hammer, is_shooter)`.

    With `match_color=True`, a hammer additionally has to be green and a
    shooter red. The color filter is applied after the shape test, so it can
    only ever subtract. Since "bullish" is a strict `close > open`, a candle
    closing exactly at its open can still be a shooter but can never be a
    hammer under that filter.
    """
    m = metrics(candle)
    hammer_fn, shooter_fn = _DETECTORS.get(method, _DETECTORS[HammerMethod.BROAD])
    raw_hammer = hammer_fn(m)
    raw_shooter = shooter_fn(m)
    is_hammer = raw_hammer and ((not match_color) or m.is_bullish)
    is_shooter = raw_shooter and ((not match_color) or (not m.is_bullish))
    return is_hammer, is_shooter


# --- PowerBar --------------------------------------------------------------

# Canonical PowerBar core thresholds. See docs/tools/powerbar.md.
POWERBAR_MIN_BODY_PCT = 0.70
POWERBAR_MAX_TOTAL_WICK_PCT = 0.30
POWERBAR_MAX_SINGLE_WICK_PCT = 0.20
POWERBAR_MIN_BODY_VS_EXPECTED = 1.00


@dataclass(frozen=True)
class PowerBar:
    """The PowerBar core assessment of one candle."""

    is_powerbar: bool
    score: float
    direction: int          # +1 bullish body, -1 bearish body, 0 flat
    body_pct: float
    total_wick_pct: float
    max_wick_pct: float
    body_vs_expected: Optional[float]

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.is_powerbar


def powerbar_core(candle: Candle, expected_body: Optional[float] = None) -> PowerBar:
    """Score one candle against the PowerBar core shape.

    A PowerBar is a candle that is nearly all body: a large body relative to
    its own range, neither wick long, and a body that is large relative to the
    NORMAL body for that instrument and timeframe.

        is_powerbar = body_pct           >= 0.70
                  and total_wick_pct     <= 0.30
                  and max_wick_pct       <= 0.20
                  and body_vs_expected   >= 1.00

        score = body_pct
              * clip(body_vs_expected, 0, 3)
              * (1 - total_wick_pct)
              * (1 - max_wick_pct)

    `expected_body` is the normal absolute body size for this instrument and
    timeframe - typically a rolling mean (see `candles.rolling_mean_body`).
    Pass None when you have no baseline: the shape tests still run, the
    body-vs-expected term is skipped, and `is_powerbar` stays False because
    that clause cannot be satisfied.

    This is a shape description. It says nothing about what price does next.
    """
    m = metrics(candle)
    if m.is_flat:
        return PowerBar(False, 0.0, 0, 0.0, 0.0, 0.0, None)

    bve: Optional[float] = None
    if expected_body is not None and expected_body > 0:
        bve = m.body / expected_body

    shape_ok = (
        m.body_pct >= POWERBAR_MIN_BODY_PCT
        and m.total_wick_pct <= POWERBAR_MAX_TOTAL_WICK_PCT
        and m.max_wick_pct <= POWERBAR_MAX_SINGLE_WICK_PCT
    )
    size_ok = bve is not None and bve >= POWERBAR_MIN_BODY_VS_EXPECTED

    score = (
        m.body_pct
        * min(max(bve if bve is not None else 0.0, 0.0), 3.0)
        * (1.0 - m.total_wick_pct)
        * (1.0 - m.max_wick_pct)
    )

    if candle.close > candle.open:
        direction = 1
    elif candle.close < candle.open:
        direction = -1
    else:
        direction = 0

    return PowerBar(
        is_powerbar=shape_ok and size_ok,
        score=score,
        direction=direction,
        body_pct=m.body_pct,
        total_wick_pct=m.total_wick_pct,
        max_wick_pct=m.max_wick_pct,
        body_vs_expected=bve,
    )
