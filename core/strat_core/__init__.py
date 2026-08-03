"""strat_core - the canonical TheStrat definitions, as plain Python.

This package is the definitions layer shared by everything in this repository:
the TheStrat Suite indicator, the sibling tools, and any port. No dependencies,
no I/O, no network, no plotting - give it OHLC, get back classifications.

    from strat_core import Candle, classify, combo, timeframe_continuity

    c2 = Candle(open=100, high=104, low=99,  close=100)
    c1 = Candle(open=100, high=103, low=99.5, close=102)   # inside c2
    cc = Candle(open=102, high=105, low=101, close=104.5)  # broke c1's high

    classify(c1, cc).token      # '2u'
    combo([classify(c2, c1), classify(c1, cc)])

The model everything reduces to is a four-field tuple:

    structure   1 | 2u | 2d | 3     what the candle did to the prior range
    above_open  bool                close vs its own open
    failed      bool                a directional break that got reclaimed
    live        bool                still forming, or closed

The tuple is the truth; the notations are projections of it.

Scope: this package covers the vocabulary - bar classification, combos,
timeframe continuity, and the proportion patterns. It deliberately does not
decide what to trade, size a position, or backtest anything.

Nothing here is financial advice.
"""

from .candles import (
    Candle,
    CandleMetrics,
    is_inside,
    metrics,
    rolling_mean_body,
)
from .combos import Scenario, combo, describe, trigger_levels
from .continuity import (
    Continuity,
    ContinuityResult,
    TimeframeVote,
    continuity_from_candles,
    timeframe_continuity,
)
from .patterns import (
    HammerMethod,
    PowerBar,
    hammer_shooter,
    powerbar_core,
)
from .states import (
    BarState,
    FailedMethod,
    Structure,
    attach_patterns,
    classify,
    classify_series,
)

__version__ = "1.0.0"

__all__ = [
    # candles
    "Candle", "CandleMetrics", "metrics", "is_inside", "rolling_mean_body",
    # states
    "Structure", "FailedMethod", "BarState",
    "classify", "classify_series", "attach_patterns",
    # patterns
    "HammerMethod", "hammer_shooter", "PowerBar", "powerbar_core",
    # combos
    "combo", "describe", "Scenario", "trigger_levels",
    # continuity
    "Continuity", "ContinuityResult", "TimeframeVote",
    "timeframe_continuity", "continuity_from_candles",
    "__version__",
]
