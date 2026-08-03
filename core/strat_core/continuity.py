"""Timeframe continuity: are the timeframes pointing the same way?

Full Timeframe Continuity (FTFC) asks one question of each timeframe you are
watching: is its CURRENTLY FORMING candle above or below its own open? If every
one of them is above, you have continuity up. If every one is below, continuity
down. Anything else is a conflict.

Two things to be careful about, because they are the usual sources of a
"why is FTFC wrong" bug:

1. It votes on the FORMING candle, not the last completed one. The open is the
   forming period's open; the close is the price so far.
2. It is a pure sign channel. It has nothing to do with whether a timeframe is
   "in force" - that is a structural question about broken ranges, and it lives
   in `states.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence


class Continuity(str, Enum):
    UP = "up"
    DOWN = "down"
    CONFLICT = "conflict"
    NONE = "none"       # nothing to vote on - no enabled slot had data


@dataclass(frozen=True)
class TimeframeVote:
    """One timeframe's contribution.

    `open_` and `close` come from the forming candle on that timeframe. Either
    may be None when the data is not available; such a slot casts no vote.
    """

    label: str
    open_: Optional[float]
    close: Optional[float]
    enabled: bool = True

    @property
    def votes(self) -> bool:
        return self.enabled and self.open_ is not None and self.close is not None

    @property
    def is_up(self) -> Optional[bool]:
        """True if above its open, False if not, None if it casts no vote.

        Strict `>`: a timeframe sitting exactly at its open counts as NOT up,
        so a doji breaks continuity up rather than being ignored.
        """
        if not self.votes:
            return None
        return self.close > self.open_


@dataclass(frozen=True)
class ContinuityResult:
    state: Continuity
    up: bool
    down: bool
    voting: List[str] = field(default_factory=list)
    dissenting: List[str] = field(default_factory=list)

    @property
    def direction(self) -> int:
        if self.state is Continuity.UP:
            return 1
        if self.state is Continuity.DOWN:
            return -1
        return 0

    def blocks(self, bullish: bool) -> bool:
        """Would continuity veto a signal in this direction?

        Only opposing continuity blocks. A conflict never blocks - it means the
        timeframes disagree, not that they disagree with you.
        """
        return self.down if bullish else self.up

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.state.value


def timeframe_continuity(votes: Sequence[TimeframeVote]) -> ContinuityResult:
    """Compute continuity across a set of timeframes.

    Both flags start true and are only ever cleared, so a set with no voting
    slots would leave both true. That degenerate case is reported as
    `Continuity.NONE` rather than being silently read as "up".
    """
    up = True
    down = True
    voting: List[str] = []
    ups: List[str] = []
    downs: List[str] = []

    for v in votes:
        decided = v.is_up
        if decided is None:
            continue
        voting.append(v.label)
        if decided:
            down = False
            ups.append(v.label)
        else:
            up = False
            downs.append(v.label)

    if not voting:
        return ContinuityResult(Continuity.NONE, False, False, [], [])

    if up:
        state = Continuity.UP
        dissenting: List[str] = []
    elif down:
        state = Continuity.DOWN
        dissenting = []
    else:
        state = Continuity.CONFLICT
        # In a conflict, report the smaller camp - that is the one breaking it.
        dissenting = downs if len(downs) <= len(ups) else ups

    return ContinuityResult(state, up, down, voting, dissenting)


def continuity_from_candles(labelled_candles) -> ContinuityResult:
    """Convenience wrapper: build votes from `(label, forming_candle)` pairs.

    Each candle must be the FORMING bar on that timeframe. Pass None for a
    timeframe whose data you do not have.
    """
    votes = []
    for label, candle in labelled_candles:
        if candle is None:
            votes.append(TimeframeVote(label, None, None))
        else:
            votes.append(TimeframeVote(label, candle.open, candle.close))
    return timeframe_continuity(votes)
