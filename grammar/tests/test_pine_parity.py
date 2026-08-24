"""Parity with the Pine implementation shipped in TheStrat Suite.

This is the test that matters. A grammar that disagrees with the indicator it
was extracted from is documentation, not a specification. `pine_detect` below
is a direct transcription of `detectBarTypeAndFailed` from
TheStratSuite_v3.0.1.pine; if the Pine changes, change it here and watch this
test fail until both agree again.
"""

import random

import pytest

from thestrat_grammar import Candle, FailedMethod, classify


def pine_detect(prevH, prevL, currH, currL, currO, currC, method="Reclaim"):
    """Transcribed from TheStratSuite_v3.0.1.pine, detectBarTypeAndFailed."""
    aboveOpen = currC > currO
    gapUp, gapDown = currO > prevH, currO < prevL
    is2up = is2down = isInside = isOutside = False
    if gapUp:
        if currL < prevL:
            isOutside = True
        else:
            is2up = True
    elif gapDown:
        if currH > prevH:
            isOutside = True
        else:
            is2down = True
    else:
        high_crossed, low_crossed = currH > prevH, currL < prevL
        if high_crossed and low_crossed:
            isOutside = True
        elif high_crossed:
            is2up = True
        elif low_crossed:
            is2down = True
        else:
            isInside = True

    isFailed = False
    inside_prev_range = prevL <= currC <= prevH
    if is2up or is2down:
        if method == "Reclaim":
            isFailed = inside_prev_range
        elif method == "Open":
            isFailed = (not aboveOpen) if is2up else aboveOpen

    if isInside:
        return "1u" if aboveOpen else "1d"
    if is2up:
        return "F2u" if isFailed else "2u"
    if is2down:
        return "F2d" if isFailed else "2d"
    if isOutside:
        return "3u" if aboveOpen else "3d"
    return ""


METHODS = [(FailedMethod.RECLAIM, "Reclaim"), (FailedMethod.OPEN, "Open")]


@pytest.mark.parametrize("py_method,pine_method", METHODS)
def test_matches_pine_on_random_bars(py_method, pine_method):
    """20,000 random bars per method. Any mismatch is a real divergence."""
    random.seed(7)
    for _ in range(20_000):
        pl = round(random.uniform(90, 100), 2)
        ph = round(pl + random.uniform(0.01, 15), 2)
        cl = round(random.uniform(85, 105), 2)
        ch = round(cl + random.uniform(0.01, 18), 2)
        co = round(random.uniform(cl, ch), 2)
        cc = round(random.uniform(cl, ch), 2)

        mine = classify(Candle(co, ch, cl, cc), Candle(0, ph, pl, 0), method=py_method)
        theirs = pine_detect(ph, pl, ch, cl, co, cc, pine_method)
        assert mine.notation() == theirs, (
            f"prior(h={ph}, l={pl}) current(o={co}, h={ch}, l={cl}, c={cc}) "
            f"[{pine_method}]: python={mine.notation()} pine={theirs}"
        )


def test_gap_up_agrees():
    """Pine branches on the open for gaps; the spec tests only the range.
    They must still land on the same answer."""
    prior, cur = Candle(0, 110, 90, 0), Candle(112, 118, 111, 117)
    assert classify(cur, prior).notation() == pine_detect(110, 90, 118, 111, 112, 117)
