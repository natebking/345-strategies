"""Bar state: the four-field tuple, and how to derive and render it.

The model
--------
Every classification the Suite draws is a rendering of one tuple:

    structure   1 | 2u | 2d | 3     what the candle did to the prior range
    above_open  bool                close vs its own open
    failed      bool                a directional break that got reclaimed
    live        bool                still forming, or closed

The tuple is the truth; notations are projections. When two displays seem to
disagree, resolve them back to the tuple before assuming a bug.

Note that the u/d suffix means two different things depending on the digit:
on a `2` it names WHICH SIDE BROKE, on a `1` or `3` it names close-vs-open.
Those are two independent channels about the same candle, and this module keeps
them separate internally so callers never have to guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Sequence

from .candles import Candle


class Structure(str, Enum):
    """What the candle did to the previous candle's range."""

    INSIDE = "1"        # broke neither side
    TWO_UP = "2u"       # took out the prior high only
    TWO_DOWN = "2d"     # took out the prior low only
    OUTSIDE = "3"       # broke both sides

    @property
    def digit(self) -> str:
        """The bare Strat digit: 1, 2 or 3."""
        return self.value[0]

    @property
    def is_directional(self) -> bool:
        return self in (Structure.TWO_UP, Structure.TWO_DOWN)


class FailedMethod(str, Enum):
    """How a directional break is judged to have failed.

    RECLAIM is the default, and is the definition to reach for unless you have
    a reason not to: the bar closed back inside the prior candle's range.
    """

    RECLAIM = "reclaim"
    OPEN = "open"
    RECLAIM_AND_OPEN = "reclaim+open"
    RECLAIM_OR_OPEN = "reclaim|open"


@dataclass(frozen=True)
class BarState:
    """One candle's classification relative to the candle before it."""

    structure: Structure
    above_open: bool
    failed: bool = False
    live: bool = False
    potential_failed: bool = False
    is_hammer: bool = False
    is_shooter: bool = False

    @property
    def digit(self) -> str:
        """1, 2 or 3 - direction-blind. This is what combo digits use."""
        return self.structure.digit

    @property
    def token(self) -> str:
        """The canonical on-chart token.

        Inside and outside bars take their u/d from close-vs-open; directional
        bars take it from the side that broke, and gain an `F` prefix when the
        break was reclaimed.

        Returns one of: 1u 1d 2u 2d F2u F2d 3u 3d
        """
        if self.structure is Structure.INSIDE:
            return "1u" if self.above_open else "1d"
        if self.structure is Structure.OUTSIDE:
            return "3u" if self.above_open else "3d"
        return ("F" + self.structure.value) if self.failed else self.structure.value

    @property
    def direction(self) -> int:
        """Directional implication: +1 bullish, -1 bearish, 0 neither.

        A Failing 2 flips: an F2u is a failed UPSIDE break, so it reads bearish.
        Inside bars have no directional implication from structure alone.
        """
        if self.structure is Structure.TWO_UP:
            return -1 if self.failed else 1
        if self.structure is Structure.TWO_DOWN:
            return 1 if self.failed else -1
        if self.structure is Structure.OUTSIDE:
            return 1 if self.above_open else -1
        return 0

    def render(self, *, universal: bool = False) -> str:
        """Render for display, optionally with the HAM/SHO suffix.

        `universal=True` swaps the Strat token for plain words, for readers who
        do not read Strat notation.
        """
        if universal:
            base = {
                Structure.INSIDE: "INSIDE",
                Structure.OUTSIDE: "EXPANSION",
                Structure.TWO_UP: "FAILING UP" if self.failed else "UP",
                Structure.TWO_DOWN: "FAILING DOWN" if self.failed else "DOWN",
            }[self.structure]
        else:
            base = self.token
        if self.is_hammer:
            base += " HAM"
        elif self.is_shooter:
            base += " SHO"
        return base

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.render()


def classify(
    prev: Candle,
    curr: Candle,
    *,
    method: FailedMethod = FailedMethod.RECLAIM,
    detect_failed: bool = True,
    live: bool = False,
) -> BarState:
    """Classify `curr` against `prev`.

    The structure test is the whole of it: did the candle take out the prior
    high, the prior low, both, or neither? Gaps get no special case - a gap-up
    open above the prior high already makes the bar at least a 2u by the range
    test, and if it also trades below the prior low it is a 3.

    Comparison rules, both load-bearing:

    - The BROKEN side is strict (`>` / `<`). Equal is not a break.
    - The HELD side is inclusive (`>=` / `<=`). An exact touch of the opposite
      extreme keeps the bar a 2, not a 3.

    Failure is only ever graded on directional bars. An outside bar that closes
    back inside the prior range is still reported as a 3 - the Suite has no F3
    token, and neither does this engine.
    """
    is_three = curr.high > prev.high and curr.low < prev.low
    is_two_up = curr.high > prev.high and curr.low >= prev.low and not is_three
    is_two_down = curr.low < prev.low and curr.high <= prev.high and not is_three

    if is_three:
        structure = Structure.OUTSIDE
    elif is_two_up:
        structure = Structure.TWO_UP
    elif is_two_down:
        structure = Structure.TWO_DOWN
    else:
        structure = Structure.INSIDE

    failed = False
    potential = False

    if detect_failed and structure.is_directional:
        # Inclusive on both edges: a close exactly at the prior high or low
        # counts as back inside the range.
        inside_prior = prev.low <= curr.close <= prev.high
        above_open = curr.above_open

        if method is FailedMethod.OPEN:
            failed = (not above_open) if is_two_up else above_open
        elif method is FailedMethod.RECLAIM:
            failed = inside_prior
        elif method is FailedMethod.RECLAIM_AND_OPEN:
            failed = ((not above_open) and inside_prior) if is_two_up \
                else (above_open and inside_prior)
        else:  # RECLAIM_OR_OPEN
            failed = ((not above_open) or inside_prior) if is_two_up \
                else (above_open or inside_prior)

        # A "potential" failure: the break has been reclaimed on price, but the
        # close-vs-open half of the test has not confirmed yet. Only the two
        # open-based methods can produce this - under the pure reclaim methods
        # the reclaim alone would already have set `failed`.
        if not failed and method in (FailedMethod.OPEN, FailedMethod.RECLAIM_AND_OPEN):
            if is_two_up and inside_prior and above_open:
                potential = True
            elif is_two_down and inside_prior and not above_open:
                potential = True

    return BarState(
        structure=structure,
        above_open=curr.above_open,
        failed=failed,
        live=live,
        potential_failed=potential,
    )


def classify_series(
    candles: Sequence[Candle],
    *,
    method: FailedMethod = FailedMethod.RECLAIM,
    detect_failed: bool = True,
    last_is_live: bool = False,
) -> List[Optional[BarState]]:
    """Classify a whole series, oldest first.

    Returns a list the same length as `candles`. The first entry is None - the
    first candle has no predecessor to be classified against.

    Set `last_is_live=True` when the final candle is still forming; it will be
    marked `live` so combo strings render it as the current slot.
    """
    out: List[Optional[BarState]] = [None]
    n = len(candles)
    for i in range(1, n):
        out.append(
            classify(
                candles[i - 1],
                candles[i],
                method=method,
                detect_failed=detect_failed,
                live=last_is_live and i == n - 1,
            )
        )
    return out


def attach_patterns(
    states: Iterable[Optional[BarState]],
    candles: Sequence[Candle],
    *,
    method=None,
    match_color: bool = False,
) -> List[Optional[BarState]]:
    """Return states with hammer/shooter flags filled in from the candles.

    Kept separate from `classify` because hammers and shooters are not bar
    types - they are proportion patterns layered on top of any structure.
    """
    from .patterns import hammer_shooter, HammerMethod

    if method is None:
        method = HammerMethod.BROAD

    out: List[Optional[BarState]] = []
    for i, st in enumerate(states):
        if st is None:
            out.append(None)
            continue
        ham, sho = hammer_shooter(candles[i], method=method, match_color=match_color)
        out.append(
            BarState(
                structure=st.structure,
                above_open=st.above_open,
                failed=st.failed,
                live=st.live,
                potential_failed=st.potential_failed,
                is_hammer=ham,
                is_shooter=sho,
            )
        )
    return out
