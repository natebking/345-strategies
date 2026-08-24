"""Full Timeframe Continuity. See SPEC.md section 7."""

from __future__ import annotations

from collections.abc import Iterable

from .model import Candle, Continuity


def continuity(candles: Iterable[Candle]) -> Continuity:
    """Read continuity across timeframes, from the sign channel only.

    Do not reconstruct this from structure: a 2u can close red, so the u/d in
    a structure token is not a sign. Pass the current candle of each monitored
    timeframe, all sampled at the same moment.
    """
    signs = [c.above_open for c in candles]
    if not signs:
        return Continuity.CONFLICT
    if all(signs):
        return Continuity.UP
    if not any(signs):
        return Continuity.DOWN
    return Continuity.CONFLICT
