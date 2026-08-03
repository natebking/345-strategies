# PowerBar

`pine/tools/PowerBar.pine` - and the core shape test in
`core/strat_core/patterns.py`.

A PowerBar is a candle that is **nearly all body**, and whose body is large
compared to what is normal for that instrument at that time of day.

It is a context marker, not an entry signal. It says something about how a
candle was built - decisive, one-directional, little rejection at either end -
and nothing about what price does next.

Not part of TheStrat Suite indicator. It ships as its own script.

---

## Why normalization matters

"Big body" is meaningless without a baseline. A 4-point body is enormous on a
quiet overnight 15-minute bar and unremarkable on the 09:30 open. Two
adjustments make the comparison fair:

- **Session.** On futures, regular-hours and overnight bars are kept in
  separate rolling averages. An overnight bar is compared to overnight bars.
- **Time of day.** Range varies structurally across the session - opening bars
  are larger, midday bars are smaller. Each 5-minute slot of the day carries
  its own smoothed average, and a bar is compared to its own slot.

Together:

```
expected_range = session_rolling_average * time_of_day_factor
range_ratio    = bar_range / expected_range
```

The time-of-day factor is clamped to [0.3, 3.0] so a thin slot with little
history cannot distort the comparison.

## The core morphology definition

This is the shared definition - the one the Invalidation Stop's shape adjust
and `strat_core.powerbar_core()` both use:

```
body_pct         = |close - open| / (high - low)
total_wick_pct   = (upper_wick + lower_wick) / (high - low)
max_wick_pct     = max(upper_wick, lower_wick) / (high - low)
body_vs_expected = |close - open| / expected_body

powerbar_core = body_pct         >= 0.70
            AND total_wick_pct   <= 0.30
            AND max_wick_pct     <= 0.20
            AND body_vs_expected >= 1.00
```

with a continuous score for ranking:

```
score = body_pct
      * clip(body_vs_expected, 0, 3)
      * (1 - total_wick_pct)
      * (1 - max_wick_pct)
```

`expected_body` is the normal absolute body for that instrument and timeframe.
`strat_core` uses a plain rolling mean (`rolling_mean_body`); the Pine
indicator additionally applies the session and time-of-day normalization above.
The Invalidation Stop uses the plain rolling mean too, and its tooltip says so.

Direction comes from the body: close above open is a bullish PowerBar, below is
bearish.

## The two indicator types

The `PowerBar.pine` script marks two setups. Both require the current bar to be
directional (a `2` or a `3`); both are judged on **C1**, the candle before it.

**PB-2 - non-inside.** C1 was not an inside bar, it has a strong body, and the
current bar reverses it.

```
C1 body_pct >= 0.70                                    -> pass
C1 body_pct >= 0.50 AND C1 range_ratio <= 1.50         -> pass
```

The size clause is the point: a medium body on a normal-sized bar is
meaningful, the same body on an oversized bar is not.

**PB-1 - inside breakout.** C1 was an inside bar with real compression, and the
bar that set the range was not oversized.

```
compression_ratio = C1 range / C2 range

compression >= 0.75                                    -> pass
compression >= 0.55 AND C2 range_ratio <= 1.50         -> pass
```

A coil is only informative if the thing it coiled inside was itself normal.

Every threshold above is an input. They are defaults, not recommendations.

## Using it from Python

```python
from strat_core import Candle, powerbar_core, rolling_mean_body

expected = rolling_mean_body(history, 20)
pb = powerbar_core(candle, expected_body=expected)

pb.is_powerbar      # bool
pb.score            # continuous, for ranking
pb.direction        # +1 bullish body, -1 bearish, 0 flat
pb.body_vs_expected # None when no baseline was supplied
```

With no `expected_body`, the shape terms still compute and `is_powerbar` stays
False - the size clause cannot be satisfied without a baseline, and the engine
will not quietly pretend otherwise.

## Caveats

A PowerBar describes a candle's construction. Treating it as a standalone entry
is a misuse of it - the Invalidation Stop, for example, uses it only to decide
whether to give a trade more room or less.

Nothing here is financial advice.
