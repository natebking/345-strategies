"""Candle geometry: the raw OHLC container and the derived proportions.

Everything in this module is pure arithmetic on one candle. Nothing here looks
at a neighbouring bar - that is `states.py`.

Ported from `calcMetrics` in the Pine source (TheStrat Suite v3.0.0). Where the
Pine makes a comparison strict rather than inclusive, this module keeps it
strict and says why; those choices are load-bearing, not accidents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Candle:
    """One OHLC bar.

    `timestamp` is optional and carried through untouched - the engine never
    reasons about time. Feeding a timeframe's bars in order is the caller's job.
    """

    open: float
    high: float
    low: float
    close: float
    timestamp: Optional[object] = None

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(f"high {self.high} is below low {self.low}")

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def above_open(self) -> bool:
        """The sign channel: did this candle close above its open?

        Strict `>`. A close exactly at the open counts as NOT above, so it
        buckets down (1d, 3d). This tie-break is deliberate and is relied on by
        timeframe continuity, the data-table colors, and the u/d suffix on 1s
        and 3s.
        """
        return self.close > self.open

    @classmethod
    def from_mapping(cls, row: dict) -> "Candle":
        """Build a Candle from a dict-like row with o/h/l/c keys.

        Accepts either short (`o`, `h`, `l`, `c`) or long (`open`, `high`, ...)
        key names, so rows out of a CSV reader or a dataframe `.to_dict()` drop
        straight in.
        """
        def pick(*names):
            for n in names:
                if n in row:
                    return row[n]
            raise KeyError(f"row is missing all of {names}")

        return cls(
            open=float(pick("open", "o", "Open")),
            high=float(pick("high", "h", "High")),
            low=float(pick("low", "l", "Low")),
            close=float(pick("close", "c", "Close")),
            timestamp=row.get("timestamp", row.get("time", row.get("t"))),
        )


@dataclass(frozen=True)
class CandleMetrics:
    """Proportions of a single candle, all ratios normalized by its range.

    Every ratio is in [0, 1] for well-formed OHLC. When the range is exactly
    zero (`is_flat`), all ratios are 0 and no pattern detector will fire - each
    one short-circuits on `is_flat` first.
    """

    body: float
    body_pct: float
    upper_wick: float
    lower_wick: float
    upper_wick_pct: float
    lower_wick_pct: float
    close_from_high: float
    close_from_low: float
    open_from_high: float
    open_from_low: float
    body_center_from_high: float
    body_center_from_low: float
    is_bullish: bool
    is_flat: bool

    @property
    def total_wick_pct(self) -> float:
        return self.upper_wick_pct + self.lower_wick_pct

    @property
    def max_wick_pct(self) -> float:
        return max(self.upper_wick_pct, self.lower_wick_pct)


def metrics(candle: Candle) -> CandleMetrics:
    """Derive the proportions of one candle.

    A zero-range candle (high == low) is reported as flat with every ratio at
    zero. That is the only degenerate case; it is tested with exact equality,
    matching the Pine, and there is no epsilon anywhere in this function.
    """
    rng = candle.high - candle.low
    if rng == 0:
        return CandleMetrics(
            body=0.0, body_pct=0.0,
            upper_wick=0.0, lower_wick=0.0,
            upper_wick_pct=0.0, lower_wick_pct=0.0,
            close_from_high=0.0, close_from_low=0.0,
            open_from_high=0.0, open_from_low=0.0,
            body_center_from_high=0.0, body_center_from_low=0.0,
            is_bullish=True, is_flat=True,
        )

    body = abs(candle.close - candle.open)
    body_center = (candle.open + candle.close) / 2.0
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low

    return CandleMetrics(
        body=body,
        body_pct=body / rng,
        upper_wick=upper_wick,
        lower_wick=lower_wick,
        upper_wick_pct=upper_wick / rng,
        lower_wick_pct=lower_wick / rng,
        close_from_high=(candle.high - candle.close) / rng,
        close_from_low=(candle.close - candle.low) / rng,
        open_from_high=(candle.high - candle.open) / rng,
        open_from_low=(candle.open - candle.low) / rng,
        body_center_from_high=(candle.high - body_center) / rng,
        body_center_from_low=(body_center - candle.low) / rng,
        # Strict: a close exactly at the open is not bullish.
        is_bullish=candle.close > candle.open,
        is_flat=False,
    )


def is_inside(prev: Candle, curr: Candle) -> bool:
    """Did `curr` stay entirely within `prev`'s range?

    Both comparisons are inclusive: a high exactly equal to the prior high has
    not crossed it, so the bar is still inside. This is the direct encoding of
    the "equal is not a break" rule.
    """
    return curr.high <= prev.high and curr.low >= prev.low


def rolling_mean_body(candles: Sequence[Candle], length: int) -> Optional[float]:
    """Mean absolute body over the last `length` candles, or None if short.

    This is the "expected body" used by the PowerBar core test. It is a plain
    rolling mean; the PowerBar indicator additionally normalizes by session and
    time of day, which this engine does not attempt (see docs/tools/powerbar.md).
    """
    if length <= 0:
        raise ValueError("length must be positive")
    if len(candles) < length:
        return None
    window = candles[-length:]
    return sum(abs(c.close - c.open) for c in window) / length
