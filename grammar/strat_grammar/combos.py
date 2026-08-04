"""Combo strings. See SPEC.md section 5."""

from __future__ import annotations

from collections.abc import Sequence

from .model import State


def combo(states: Sequence[State], *, dashes: bool = True, potential: bool = False) -> str:
    """Render an ordered sequence of states, oldest to newest.

    The last token is the forming candle; that position is what carries
    liveness, which is why notation itself stays tense-free.
    """
    tokens = [s.notation() for s in states]
    # Inside bars in a combo's interior are written bare: 2d-1-2u, not 2d-1d-2u.
    # The sign of a middle inside bar is not what the combo is describing.
    for i in range(1, len(tokens) - 1):
        if tokens[i] in ("1u", "1d"):
            tokens[i] = "1"
    body = ("-" if dashes else "").join(tokens)
    return f"*{body}" if potential else body
