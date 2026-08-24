"""The core types. See SPEC.md sections 1-4."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Structure(str, Enum):
    """What a candle did to the prior candle's range. SPEC.md section 2."""

    INSIDE = "1"
    TWO_UP = "2u"
    TWO_DOWN = "2d"
    OUTSIDE = "3"

    @property
    def is_directional(self) -> bool:
        """Only directional structures can fail: they broke exactly one side."""
        return self in (Structure.TWO_UP, Structure.TWO_DOWN)


class FailedMethod(str, Enum):
    """How a rejected break is detected. SPEC.md section 4."""

    RECLAIM = "reclaim"
    OPEN = "open"
    RECLAIM_AND_OPEN = "reclaim_and_open"
    RECLAIM_OR_OPEN = "reclaim_or_open"


class PatternMethod(str, Enum):
    """Hammer / shooter definitions. SPEC.md section 6."""

    BROAD = "broad"
    CLASSIC = "classic"
    PIN_BAR = "pin_bar"


class Continuity(str, Enum):
    """Full Timeframe Continuity reading. SPEC.md section 7."""

    UP = "up"
    DOWN = "down"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class Candle:
    """One OHLC bar. Timestamp is optional and never affects classification."""

    open: float
    high: float
    low: float
    close: float
    timestamp: int | None = None

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(f"high {self.high} is below low {self.low}")

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def above_open(self) -> bool:
        """Sign channel. A close exactly at the open is NOT above; it buckets down."""
        return self.close > self.open


@dataclass(frozen=True)
class State:
    """The four-field tuple that is the whole model. SPEC.md section 1."""

    structure: Structure
    above_open: bool
    failed: bool
    live: bool = False

    def notation(self, *, dashes: bool = False) -> str:
        """Render conventional Strat notation.

        The u/d suffix means different things per structure: on a 2 it names the
        side that broke, on a 1 or 3 it reports close versus open. That overload
        lives here, at the display boundary, and nowhere else.
        """
        sign = "u" if self.above_open else "d"
        if self.structure is Structure.INSIDE:
            token = f"1{sign}"
        elif self.structure is Structure.OUTSIDE:
            token = f"3{sign}"
        else:
            token = self.structure.value  # 2u / 2d already carry the break side
            if self.failed:
                token = f"F{token}"
        return token

    def display(self) -> str:
        """Glyph-notation token: the structure with no sign, then '>' or '<'.

        The token never carries sign in this projection, so a red 2u renders as
        '2u<' with break side and sign visibly separate. This is the form
        programmatic surfaces should emit (and the form priceactionapi serves).
        """
        if self.structure in (Structure.TWO_UP, Structure.TWO_DOWN):
            base = ("F" if self.failed else "") + self.structure.value
        else:
            base = self.structure.value
        return base + sign_glyph(self.above_open)

    def as_dict(self) -> dict:
        return {
            "structure": self.structure.value,
            "above_open": self.above_open,
            "failed": self.failed,
            "live": self.live,
        }


def sign_glyph(above_open: bool) -> str:
    """'>' when the close is above the open, '<' otherwise."""
    return ">" if above_open else "<"
