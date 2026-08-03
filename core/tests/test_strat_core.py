"""Tests for strat_core.

Run from the `core/` directory:

    python3 -m unittest discover -s tests -v

These pin the decisions that are easy to get wrong on a re-implementation:
the strict-vs-inclusive comparisons, the close==open tie-break, the meaning of
the u/d suffix per digit, and the fact that outside bars are never graded as
failed.
"""

import unittest

from strat_core import (
    Candle,
    Continuity,
    FailedMethod,
    HammerMethod,
    Structure,
    TimeframeVote,
    classify,
    classify_series,
    combo,
    describe,
    hammer_shooter,
    is_inside,
    metrics,
    powerbar_core,
    rolling_mean_body,
    timeframe_continuity,
)


def C(o, h, l, c):
    return Candle(open=o, high=h, low=l, close=c)


class TestStructure(unittest.TestCase):
    def test_inside(self):
        prev = C(100, 110, 90, 105)
        curr = C(100, 108, 92, 101)
        self.assertIs(classify(prev, curr).structure, Structure.INSIDE)

    def test_two_up(self):
        prev = C(100, 110, 90, 105)
        curr = C(105, 112, 95, 111)
        self.assertIs(classify(prev, curr).structure, Structure.TWO_UP)

    def test_two_down(self):
        prev = C(100, 110, 90, 105)
        curr = C(105, 108, 88, 89)
        self.assertIs(classify(prev, curr).structure, Structure.TWO_DOWN)

    def test_outside(self):
        prev = C(100, 110, 90, 105)
        curr = C(105, 112, 88, 111)
        self.assertIs(classify(prev, curr).structure, Structure.OUTSIDE)

    def test_equal_high_is_not_a_break(self):
        """A high exactly matching the prior high has not crossed it."""
        prev = C(100, 110, 90, 105)
        curr = C(100, 110, 95, 108)
        self.assertIs(classify(prev, curr).structure, Structure.INSIDE)

    def test_equal_low_is_not_a_break(self):
        prev = C(100, 110, 90, 105)
        curr = C(100, 108, 90, 95)
        self.assertIs(classify(prev, curr).structure, Structure.INSIDE)

    def test_touch_of_opposite_extreme_keeps_it_a_two(self):
        """Held side is inclusive: an exact touch is not the second break."""
        prev = C(100, 110, 90, 105)
        curr = C(105, 112, 90, 111)   # broke the high, low exactly equal
        self.assertIs(classify(prev, curr).structure, Structure.TWO_UP)

    def test_gap_up_is_still_just_a_two_up(self):
        """Gaps get no special case - classification is always the range test."""
        prev = C(100, 110, 90, 105)
        curr = C(115, 120, 114, 118)
        self.assertIs(classify(prev, curr).structure, Structure.TWO_UP)

    def test_gap_up_that_fills_below_is_an_outside_bar(self):
        prev = C(100, 110, 90, 105)
        curr = C(115, 120, 88, 95)
        self.assertIs(classify(prev, curr).structure, Structure.OUTSIDE)

    def test_is_inside_helper_is_inclusive(self):
        self.assertTrue(is_inside(C(100, 110, 90, 105), C(100, 110, 90, 101)))


class TestAboveOpen(unittest.TestCase):
    def test_close_equal_to_open_is_not_above(self):
        prev = C(100, 110, 90, 105)
        curr = C(100, 108, 92, 100)      # inside, close == open
        st = classify(prev, curr)
        self.assertFalse(st.above_open)
        self.assertEqual(st.token, "1d")

    def test_inside_suffix_comes_from_close_vs_open(self):
        prev = C(100, 110, 90, 105)
        self.assertEqual(classify(prev, C(100, 108, 92, 104)).token, "1u")
        self.assertEqual(classify(prev, C(100, 108, 92, 96)).token, "1d")

    def test_outside_suffix_comes_from_close_vs_open(self):
        prev = C(100, 110, 90, 105)
        self.assertEqual(classify(prev, C(100, 112, 88, 104)).token, "3u")
        self.assertEqual(classify(prev, C(100, 112, 88, 96)).token, "3d")

    def test_a_two_up_can_be_red(self):
        """The u names which side broke, not the candle's color."""
        prev = C(100, 110, 90, 105)
        curr = C(108, 112, 100, 102)     # broke the high, closed red
        st = classify(prev, curr, detect_failed=False)
        self.assertIs(st.structure, Structure.TWO_UP)
        self.assertFalse(st.above_open)
        self.assertEqual(st.token, "2u")


class TestFailedTwos(unittest.TestCase):
    def setUp(self):
        self.prev = C(100, 110, 90, 105)

    def test_reclaim_default(self):
        curr = C(108, 112, 100, 105)     # broke high, closed back inside
        st = classify(self.prev, curr)
        self.assertTrue(st.failed)
        self.assertEqual(st.token, "F2u")

    def test_reclaim_does_not_fire_when_it_holds(self):
        curr = C(108, 112, 100, 111)     # closed beyond the prior high
        self.assertFalse(classify(self.prev, curr).failed)

    def test_close_exactly_at_the_level_counts_as_reclaimed(self):
        curr = C(108, 112, 100, 110)     # close == prior high, inclusive
        self.assertTrue(classify(self.prev, curr).failed)

    def test_open_method(self):
        curr = C(111, 113, 108, 109)     # broke high, closed below its open
        self.assertTrue(classify(self.prev, curr, method=FailedMethod.OPEN).failed)

    def test_reclaim_and_open_needs_both(self):
        curr = C(108, 112, 100, 111)     # reclaim fails: closed above prior high
        self.assertFalse(
            classify(self.prev, curr, method=FailedMethod.RECLAIM_AND_OPEN).failed
        )

    def test_reclaim_or_open_needs_either(self):
        curr = C(112, 114, 108, 111)     # closed below own open, above prior high
        self.assertTrue(
            classify(self.prev, curr, method=FailedMethod.RECLAIM_OR_OPEN).failed
        )

    def test_f2u_reads_bearish(self):
        """The letter names the break that failed, not the trade it sets up."""
        curr = C(108, 112, 100, 105)
        self.assertEqual(classify(self.prev, curr).direction, -1)

    def test_f2d_reads_bullish(self):
        curr = C(95, 100, 88, 96)
        st = classify(self.prev, curr)
        self.assertEqual(st.token, "F2d")
        self.assertEqual(st.direction, 1)

    def test_outside_bars_are_never_graded_failed(self):
        """There is no F3 - an outside bar closing back inside is still a 3."""
        curr = C(105, 112, 88, 100)
        st = classify(self.prev, curr)
        self.assertIs(st.structure, Structure.OUTSIDE)
        self.assertFalse(st.failed)
        self.assertIn(st.token, ("3u", "3d"))

    def test_detection_can_be_disabled(self):
        curr = C(108, 112, 100, 105)
        self.assertFalse(classify(self.prev, curr, detect_failed=False).failed)

    def test_potential_only_for_open_based_methods(self):
        curr = C(103, 112, 100, 105)     # reclaimed, but closed above its open
        st = classify(self.prev, curr, method=FailedMethod.OPEN)
        self.assertFalse(st.failed)
        self.assertTrue(st.potential_failed)
        self.assertFalse(classify(self.prev, curr).potential_failed)


class TestPatterns(unittest.TestCase):
    def test_broad_hammer(self):
        c = C(108, 110, 100, 109)        # body up top, long lower wick
        ham, sho = hammer_shooter(c)
        self.assertTrue(ham)
        self.assertFalse(sho)

    def test_broad_shooter(self):
        c = C(102, 110, 100, 101)
        ham, sho = hammer_shooter(c)
        self.assertFalse(ham)
        self.assertTrue(sho)

    def test_centered_doji_is_neither(self):
        """Strictly centered: satisfies neither test, by design."""
        c = C(105, 110, 100, 105)
        self.assertEqual(hammer_shooter(c), (False, False))

    def test_color_filter_only_subtracts(self):
        c = C(109, 110, 100, 108)        # hammer shape, red body
        self.assertTrue(hammer_shooter(c)[0])
        self.assertFalse(hammer_shooter(c, match_color=True)[0])

    def test_pin_bar_is_inclusive_at_the_boundary(self):
        c = C(107.5, 110, 100, 109)      # open exactly at the 25% boundary
        self.assertTrue(hammer_shooter(c, method=HammerMethod.PIN_BAR)[0])

    def test_flat_candle_is_never_a_pattern(self):
        c = C(100, 100, 100, 100)
        self.assertEqual(hammer_shooter(c), (False, False))
        self.assertTrue(metrics(c).is_flat)

    def test_classic_extreme_doji_is_excluded_by_the_guard(self):
        """Body <= 0.1% of range forces the wick ratio to zero."""
        c = C(109.999, 110, 100, 110)
        self.assertFalse(hammer_shooter(c, method=HammerMethod.CLASSIC)[0])


class TestPowerBar(unittest.TestCase):
    def test_clean_powerbar(self):
        c = C(100, 110.5, 99.5, 110)     # nearly all body
        pb = powerbar_core(c, expected_body=5.0)
        self.assertTrue(pb.is_powerbar)
        self.assertEqual(pb.direction, 1)
        self.assertGreater(pb.score, 0)

    def test_without_a_baseline_it_cannot_pass(self):
        c = C(100, 110.5, 99.5, 110)
        self.assertFalse(powerbar_core(c).is_powerbar)

    def test_long_wick_fails_the_shape(self):
        c = C(100, 120, 99.5, 110)
        self.assertFalse(powerbar_core(c, expected_body=5.0).is_powerbar)

    def test_small_body_versus_normal_fails(self):
        c = C(100, 110.5, 99.5, 110)
        self.assertFalse(powerbar_core(c, expected_body=50.0).is_powerbar)

    def test_rolling_mean_body(self):
        cs = [C(100, 101, 99, 102), C(100, 101, 99, 104)]
        self.assertEqual(rolling_mean_body(cs, 2), 3.0)
        self.assertIsNone(rolling_mean_body(cs, 5))


class TestCombos(unittest.TestCase):
    def test_reads_oldest_to_newest(self):
        c3 = C(100, 110, 90, 95)
        c2 = C(95, 105, 85, 88)          # 2d
        c1 = C(88, 100, 87, 95)          # inside
        cc = C(95, 106, 90, 104)         # 2u
        states = [classify(c3, c2), classify(c2, c1), classify(c1, cc)]
        self.assertEqual(combo(states), "2d-1-2u")

    def test_dashes_are_cosmetic(self):
        c3 = C(100, 110, 90, 95)
        c2 = C(95, 105, 85, 88)
        c1 = C(88, 100, 87, 95)
        cc = C(95, 106, 90, 104)
        states = [classify(c3, c2), classify(c2, c1), classify(c1, cc)]
        self.assertEqual(combo(states, dashes=False), "2d12u")

    def test_potential_prefix(self):
        c1 = C(88, 100, 87, 95)
        cc = C(95, 99, 90, 96)
        states = [classify(c1, cc)]
        self.assertTrue(combo(states, potential=True).startswith("*"))

    def test_failed_slot_carries_the_f(self):
        prev = C(100, 110, 90, 105)
        curr = C(108, 112, 100, 105)
        self.assertEqual(combo([classify(prev, curr)]), "F2u")

    def test_describe_names_an_inside_reversal(self):
        c3 = C(100, 110, 90, 95)
        c2 = C(95, 105, 85, 88)          # 2d
        c1 = C(88, 100, 87, 95)          # inside
        cc = C(95, 106, 90, 104)         # 2u -> reversal
        states = [classify(c3, c2), classify(c2, c1), classify(c1, cc)]
        s = describe(states)
        self.assertEqual(s.name, "inside reversal")
        self.assertEqual(s.direction, 1)
        self.assertTrue(s.actionable)

    def test_describe_marks_a_setup_as_not_actionable(self):
        c2 = C(95, 105, 85, 88)
        c1 = C(88, 100, 87, 95)
        cc = C(95, 99, 90, 96)           # still inside
        states = [classify(c2, c1), classify(c1, cc)]
        s = describe(states)
        self.assertFalse(s.actionable)


class TestContinuity(unittest.TestCase):
    def test_all_up(self):
        votes = [TimeframeVote(str(i), 100, 101) for i in range(3)]
        r = timeframe_continuity(votes)
        self.assertIs(r.state, Continuity.UP)
        self.assertEqual(r.direction, 1)

    def test_all_down(self):
        votes = [TimeframeVote(str(i), 100, 99) for i in range(3)]
        self.assertIs(timeframe_continuity(votes).state, Continuity.DOWN)

    def test_conflict(self):
        votes = [TimeframeVote("a", 100, 101), TimeframeVote("b", 100, 99)]
        r = timeframe_continuity(votes)
        self.assertIs(r.state, Continuity.CONFLICT)
        self.assertEqual(r.direction, 0)

    def test_doji_breaks_continuity_up(self):
        """A timeframe exactly at its open is not up, so it breaks continuity."""
        votes = [TimeframeVote("a", 100, 101), TimeframeVote("b", 100, 100)]
        self.assertIs(timeframe_continuity(votes).state, Continuity.CONFLICT)

    def test_doji_alone_counts_as_down(self):
        """close == open lands on the not-above branch, clearing up only."""
        votes = [TimeframeVote("a", 100, 100)]
        self.assertIs(timeframe_continuity(votes).state, Continuity.DOWN)

    def test_slots_without_data_cast_no_vote(self):
        votes = [TimeframeVote("a", 100, 101), TimeframeVote("b", None, None)]
        r = timeframe_continuity(votes)
        self.assertIs(r.state, Continuity.UP)
        self.assertEqual(r.voting, ["a"])

    def test_disabled_slots_cast_no_vote(self):
        votes = [
            TimeframeVote("a", 100, 101),
            TimeframeVote("b", 100, 99, enabled=False),
        ]
        self.assertIs(timeframe_continuity(votes).state, Continuity.UP)

    def test_no_voting_slots_reports_none_not_up(self):
        votes = [TimeframeVote("a", None, None)]
        r = timeframe_continuity(votes)
        self.assertIs(r.state, Continuity.NONE)
        self.assertEqual(r.direction, 0)

    def test_conflict_never_blocks(self):
        votes = [TimeframeVote("a", 100, 101), TimeframeVote("b", 100, 99)]
        r = timeframe_continuity(votes)
        self.assertFalse(r.blocks(bullish=True))
        self.assertFalse(r.blocks(bullish=False))

    def test_opposing_continuity_blocks(self):
        votes = [TimeframeVote("a", 100, 99)]
        r = timeframe_continuity(votes)
        self.assertTrue(r.blocks(bullish=True))
        self.assertFalse(r.blocks(bullish=False))


class TestSeries(unittest.TestCase):
    def test_first_entry_has_no_predecessor(self):
        cs = [C(100, 110, 90, 105), C(105, 112, 95, 111)]
        states = classify_series(cs)
        self.assertIsNone(states[0])
        self.assertIs(states[1].structure, Structure.TWO_UP)

    def test_last_is_live(self):
        cs = [C(100, 110, 90, 105), C(105, 112, 95, 111)]
        self.assertTrue(classify_series(cs, last_is_live=True)[-1].live)

    def test_from_mapping_accepts_short_and_long_keys(self):
        a = Candle.from_mapping({"o": 1, "h": 2, "l": 0, "c": 1.5})
        b = Candle.from_mapping({"open": 1, "high": 2, "low": 0, "close": 1.5})
        self.assertEqual(a, b)

    def test_malformed_candle_is_rejected(self):
        with self.assertRaises(ValueError):
            C(100, 90, 110, 95)


if __name__ == "__main__":
    unittest.main()
