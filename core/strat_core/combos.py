"""Combo strings: reading a run of bar states as one scenario.

`2d-1-2u` reads oldest to newest: the candle two back was a 2d, the prior
candle was inside, the current candle broke up. The last token is always the
forming candle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .states import BarState, Structure


def combo(
    states: Sequence[BarState],
    *,
    dashes: bool = True,
    potential: bool = False,
    patterns: bool = False,
) -> str:
    """Render a run of states, oldest first, as a combo string.

    - `dashes` is cosmetic only: `2d12u` and `2d-1-2u` are the same string.
    - `potential=True` prefixes `*`, marking a setup whose trigger has not been
      broken yet. `*2d-1-2u` is a setup; `2d-1-2u` is a signal.
    - `patterns=True` appends ` HAM` / ` SHO` when the final candle carries one.

    Slots before the last render as their bare digit plus, for directional
    bars, the side that broke - and an `F` prefix if that break was reclaimed.
    """
    if not states:
        return ""

    tokens: List[str] = []
    for i, st in enumerate(states):
        last = i == len(states) - 1
        tokens.append(_slot_token(st, last=last))

    text = ("-".join(tokens)) if dashes else ("".join(tokens))
    if potential:
        text = "*" + text
    if patterns:
        tail = states[-1]
        if tail.is_hammer:
            text += " HAM"
        elif tail.is_shooter:
            text += " SHO"
    return text


def _slot_token(state: BarState, *, last: bool) -> str:
    """One slot of a combo.

    Inside bars render as a bare `1` inside a combo - the u/d of an inside bar
    is close-vs-open, which is not what a combo is describing. Directional bars
    keep their break side and any `F` prefix. Outside bars render as `3`, or
    `3u`/`3d` in the final slot where the direction of the expansion matters.
    """
    if state.structure is Structure.INSIDE:
        return "1"
    if state.structure is Structure.OUTSIDE:
        return ("3u" if state.above_open else "3d") if last else "3"
    return ("F" + state.structure.value) if state.failed else state.structure.value


@dataclass(frozen=True)
class Scenario:
    """A named reading of the last two or three slots."""

    name: str
    combo: str
    direction: int      # +1 bullish, -1 bearish, 0 neutral
    actionable: bool    # the trigger has been broken, not merely set up


def describe(states: Sequence[BarState]) -> Optional[Scenario]:
    """Name the scenario formed by the last three states, if it is a known one.

    Recognizes the common continuation and reversal shapes. Returns None when
    the run does not match a named scenario - which is not an error, most runs
    do not.

    `actionable` reports whether the final candle has actually broken its
    trigger (it is a 2 or a 3), as opposed to sitting inside as a setup.
    """
    if len(states) < 2:
        return None

    tail = states[-1]
    prior = states[-2]
    text = combo(states[-3:] if len(states) >= 3 else states[-2:])
    direction = tail.direction
    actionable = tail.structure is not Structure.INSIDE

    # Inside-bar breakouts: the coil resolves.
    if prior.structure is Structure.INSIDE and tail.structure.is_directional:
        if len(states) >= 3:
            two_back = states[-3]
            if two_back.structure.is_directional:
                same = (two_back.direction == tail.direction)
                name = "inside continuation" if same else "inside reversal"
                return Scenario(name, text, direction, actionable)
        return Scenario("inside breakout", text, direction, actionable)

    # 2-2: a directional bar followed by another directional bar.
    if prior.structure.is_directional and tail.structure.is_directional:
        if prior.direction == tail.direction:
            return Scenario("2-2 continuation", text, direction, actionable)
        return Scenario("2-2 reversal", text, direction, actionable)

    # 3-2: an outside bar shook out both sides, then price picked a side.
    if prior.structure is Structure.OUTSIDE and tail.structure.is_directional:
        return Scenario("3-2 reversal", text, direction, actionable)

    # Range expansion: the current bar takes out both sides.
    if tail.structure is Structure.OUTSIDE:
        return Scenario("range expansion", text, direction, actionable)

    if tail.structure is Structure.INSIDE:
        return Scenario("consolidation", text, 0, False)

    return None


def trigger_levels(prev, curr=None):
    """The two price levels that arm a signal on the next candle.

    A long triggers when price takes out the prior candle's high; a short when
    it takes out the prior candle's low. Equal is not a break, so a trigger
    needs price strictly beyond the level.

    Returns `(long_trigger, short_trigger)`.
    """
    return prev.high, prev.low
