"""Structure and failed-break classification. See SPEC.md sections 2 and 4."""

from __future__ import annotations

from .model import Candle, FailedMethod, State, Structure


def structure_of(current: Candle, prior: Candle) -> Structure:
    """Classify a candle against the prior candle's range.

    Equal is not a break: a high exactly matching the prior high has not
    crossed it. Gaps get no special case, because classification tests the
    range and never the open.
    """
    broke_high = current.high > prior.high
    broke_low = current.low < prior.low
    if broke_high and broke_low:
        return Structure.OUTSIDE
    if broke_high:
        return Structure.TWO_UP
    if broke_low:
        return Structure.TWO_DOWN
    return Structure.INSIDE


def is_failed(
    current: Candle,
    prior: Candle,
    structure: Structure,
    method: FailedMethod = FailedMethod.RECLAIM,
) -> bool:
    """Did a directional break get rejected?

    Only 2u and 2d can fail. An inside candle broke nothing and an outside
    candle broke both sides, so neither has a single break to reject.
    """
    if not structure.is_directional:
        return False

    reclaimed = prior.low <= current.close <= prior.high
    # "Closed against the break": a 2u that did not close above its open, or a
    # 2d that did. Note a doji closes at its open and counts as not above.
    against_open = (
        not current.above_open if structure is Structure.TWO_UP else current.above_open
    )

    if method is FailedMethod.RECLAIM:
        return reclaimed
    if method is FailedMethod.OPEN:
        return against_open
    if method is FailedMethod.RECLAIM_AND_OPEN:
        return reclaimed and against_open
    if method is FailedMethod.RECLAIM_OR_OPEN:
        return reclaimed or against_open
    raise ValueError(f"unknown method: {method}")


def classify(
    current: Candle,
    prior: Candle,
    *,
    method: FailedMethod = FailedMethod.RECLAIM,
    live: bool = False,
) -> State:
    """Reduce a candle to the four-field tuple that is the whole model."""
    structure = structure_of(current, prior)
    return State(
        structure=structure,
        above_open=current.above_open,
        failed=is_failed(current, prior, structure, method),
        live=live,
    )
