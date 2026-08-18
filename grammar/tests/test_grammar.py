"""Tests for the Strat grammar.

The edge cases here are the ones SPEC.md flags as the usual sources of
disagreement between implementations. They are the point of the package.
"""

import pytest

from strat_grammar import (
    Candle, Structure, FailedMethod, PatternMethod, Continuity,
    classify, structure_of, is_failed, is_hammer, is_shooter, continuity, combo,
)

PRIOR = Candle(open=100, high=110, low=90, close=105)


# --- structure -------------------------------------------------------------

def test_inside_holds_both_sides():
    assert structure_of(Candle(101, 109, 91, 108), PRIOR) is Structure.INSIDE

def test_two_up_breaks_high_only():
    assert structure_of(Candle(105, 115, 95, 112), PRIOR) is Structure.TWO_UP

def test_two_down_breaks_low_only():
    assert structure_of(Candle(105, 108, 85, 95), PRIOR) is Structure.TWO_DOWN

def test_outside_breaks_both():
    assert structure_of(Candle(105, 115, 85, 95), PRIOR) is Structure.OUTSIDE

def test_equal_high_is_not_a_break():
    """Equal is not a break. This one trips most implementations."""
    assert structure_of(Candle(101, 110, 91, 108), PRIOR) is Structure.INSIDE

def test_equal_both_sides_is_inside():
    assert structure_of(Candle(101, 110, 90, 108), PRIOR) is Structure.INSIDE

def test_gap_up_is_two_up_not_its_own_type():
    """A gap-up open above the prior high is already a 2u by the range test."""
    assert structure_of(Candle(112, 118, 111, 117), PRIOR) is Structure.TWO_UP

def test_gap_that_fills_through_is_outside():
    assert structure_of(Candle(112, 118, 85, 88), PRIOR) is Structure.OUTSIDE


# --- sign ------------------------------------------------------------------

def test_two_up_can_close_red():
    """The u names which side broke, not the candle's color."""
    state = classify(Candle(112, 115, 95, 108), PRIOR)
    assert state.structure is Structure.TWO_UP
    assert state.above_open is False

def test_close_equal_to_open_buckets_down():
    assert Candle(100, 110, 90, 100).above_open is False


# --- failed ----------------------------------------------------------------

def test_reclaim_requires_close_back_inside():
    up = Candle(105, 115, 95, 101)          # broke high, closed inside prior range
    assert is_failed(up, PRIOR, Structure.TWO_UP) is True

def test_no_reclaim_when_close_holds_outside():
    up = Candle(105, 115, 95, 114)
    assert is_failed(up, PRIOR, Structure.TWO_UP) is False

def test_open_method_uses_close_versus_open():
    up = Candle(112, 115, 95, 111)          # closed below its own open
    assert is_failed(up, PRIOR, Structure.TWO_UP, FailedMethod.OPEN) is True

def test_and_method_needs_both():
    up = Candle(105, 115, 95, 114)          # closed against open? no. reclaimed? no.
    assert is_failed(up, PRIOR, Structure.TWO_UP, FailedMethod.RECLAIM_AND_OPEN) is False

def test_or_method_needs_either():
    up = Candle(112, 115, 95, 111)
    assert is_failed(up, PRIOR, Structure.TWO_UP, FailedMethod.RECLAIM_OR_OPEN) is True

@pytest.mark.parametrize("structure", [Structure.INSIDE, Structure.OUTSIDE])
def test_only_directional_candles_can_fail(structure):
    """Inside broke nothing; outside broke both sides. Neither has one break to reject."""
    assert is_failed(Candle(105, 115, 85, 95), PRIOR, structure) is False


# --- notation --------------------------------------------------------------

def test_failed_notation_is_uppercase_and_tense_free():
    state = classify(Candle(105, 115, 95, 101), PRIOR, live=True)
    assert state.notation() == "F2u"        # uppercase even while live

def test_inside_notation_carries_sign():
    assert classify(Candle(101, 109, 91, 108), PRIOR).notation() == "1u"
    assert classify(Candle(108, 109, 91, 101), PRIOR).notation() == "1d"

def test_outside_notation_carries_sign():
    assert classify(Candle(105, 115, 85, 112), PRIOR).notation() == "3u"

def test_combo_renders_oldest_to_newest():
    c2 = classify(Candle(105, 108, 85, 95), PRIOR)              # 2d
    c1 = classify(Candle(96, 100, 90, 99), Candle(105, 108, 85, 95))
    cc = classify(Candle(99, 112, 95, 111), Candle(96, 100, 90, 99))
    assert combo([c2, c1, cc]).endswith("2u")
    assert combo([c2, c1, cc], potential=True).startswith("*")


# --- patterns --------------------------------------------------------------

def test_broad_hammer_needs_body_in_upper_half():
    assert is_hammer(Candle(open=108, high=110, low=90, close=109)) is True

def test_body_exactly_at_midpoint_is_neither():
    """A body centered exactly at the midpoint is neither pattern."""
    doji = Candle(open=100, high=110, low=90, close=100)
    assert is_hammer(doji) is False
    assert is_shooter(doji) is False

def test_zero_range_candle_is_neither():
    flat = Candle(open=100, high=100, low=100, close=100)
    assert is_hammer(flat) is False
    assert is_shooter(flat) is False

def test_color_filter_rejects_red_hammer():
    red = Candle(open=109, high=110, low=90, close=108)
    assert is_hammer(red) is True
    assert is_hammer(red, require_color=True) is False

def test_pin_bar_is_stricter_than_broad():
    """Body just above the midpoint: broad accepts it, pin bar wants the top quarter."""
    c = Candle(open=101, high=110, low=90, close=102)
    assert is_hammer(c, PatternMethod.BROAD) is True
    assert is_hammer(c, PatternMethod.PIN_BAR) is False


# --- continuity ------------------------------------------------------------

def test_all_above_open_is_up():
    assert continuity([Candle(1, 2, 0, 1.5), Candle(1, 2, 0, 1.9)]) is Continuity.UP

def test_all_at_or_below_open_is_down():
    assert continuity([Candle(1, 2, 0, 0.5), Candle(1, 2, 0, 1.0)]) is Continuity.DOWN

def test_mixed_is_conflict():
    assert continuity([Candle(1, 2, 0, 1.5), Candle(1, 2, 0, 0.5)]) is Continuity.CONFLICT

def test_empty_is_conflict():
    assert continuity([]) is Continuity.CONFLICT


# --- glyph projection ------------------------------------------------------

def test_glyph_token_never_carries_sign_on_ones_and_threes():
    assert classify(Candle(101, 109, 91, 108), PRIOR).display() == "1>"
    assert classify(Candle(108, 109, 91, 101), PRIOR).display() == "1<"
    assert classify(Candle(105, 115, 85, 112), PRIOR).display() == "3>"

def test_glyph_makes_the_red_two_up_visible():
    """The whole point: break side and sign visibly separate."""
    state = classify(Candle(114, 115, 95, 112), PRIOR)   # broke high, closed red, held above the prior high
    assert state.display() == "2u<"

def test_glyph_failed_keeps_break_side():
    state = classify(Candle(105, 115, 95, 101), PRIOR)   # F2u closing red
    assert state.display() == "F2u<"

def test_projections_agree_through_the_tuple():
    """Chart and glyph forms of one state always describe the same tuple."""
    state = classify(Candle(114, 115, 95, 112), PRIOR)
    assert state.notation() == "2u" and state.display() == "2u<"


def test_classic_rejects_a_doji_regardless_of_wick():
    """A near-zero body fails Classic: the ratio test needs a real body."""
    doji_long_wick = Candle(open=109.99, high=110, low=90, close=110)
    assert is_hammer(doji_long_wick, PatternMethod.CLASSIC) is False
