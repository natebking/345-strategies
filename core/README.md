# strat_core

The canonical TheStrat definitions, as plain Python.

This is the definitions layer the rest of the repository is built on. The Pine
indicators implement these rules for TradingView charts; `strat_core`
implements the same rules for anything that isn't a chart - a scanner, a
notebook, a data pipeline, a test harness, a port to another language.

**No dependencies.** Standard library only, Python 3.8+. No I/O, no network,
no plotting, no dataframes. Give it OHLC, get back classifications.

## Install

There is nothing to install. Copy the `strat_core/` directory into your
project, or add `core/` to your path:

```python
import sys; sys.path.insert(0, "path/to/345-strategies/core")
```

Or install it in place, from this directory:

```bash
pip install -e .
```

## The model

Every classification reduces to one four-field tuple:

| Field | Values | What it means |
|---|---|---|
| `structure` | `1`, `2u`, `2d`, `3` | what the candle did to the prior candle's range |
| `above_open` | true / false | close vs its own open |
| `failed` | true / false | a directional break that got reclaimed |
| `live` | forming / closed | whether the candle is still moving |

**The tuple is the truth; notations are projections.** When two displays seem
to disagree, resolve them back to the tuple before assuming a bug.

Note that the `u`/`d` suffix means two different things depending on the digit:
on a `2` it names *which side broke*; on a `1` or `3` it names *close vs open*.
That is the single most common misreading of Strat notation, so the engine
keeps the two channels separate and never makes you infer one from the other.

## Quick start

```python
from strat_core import Candle, classify, combo, describe

c2 = Candle(open=100, high=110, low=90,  close=95)    # sets the range
c1 = Candle(open=95,  high=105, low=85,  close=88)    # 2d - took the low
cc = Candle(open=88,  high=100, low=87,  close=95)    # inside

s1 = classify(c2, c1)
s2 = classify(c1, cc)

s1.token         # '2d'
s1.direction     # -1
s2.token         # '1u'

combo([s1, s2])  # '2d-1'
```

Classify a whole series at once:

```python
from strat_core import classify_series

states = classify_series(candles, last_is_live=True)
# states[0] is None - the first candle has nothing to be classified against
```

## Timeframe continuity

Continuity asks one question of each timeframe: is its **currently forming**
candle above or below its own open?

```python
from strat_core import TimeframeVote, timeframe_continuity

votes = [
    TimeframeVote("15m", open_=100, close=101),
    TimeframeVote("1h",  open_=99,  close=102),
    TimeframeVote("4h",  open_=98,  close=104),
]

r = timeframe_continuity(votes)
r.state              # Continuity.UP
r.blocks(bullish=True)   # False
```

Two things worth being explicit about, because they cause most "why is
continuity wrong" questions:

- It votes on the **forming** candle, not the last completed one.
- It is a pure sign channel. It has nothing to do with whether a timeframe is
  *in force*, which is a structural question about broken ranges.

A timeframe sitting exactly at its open counts as **not up**, so a doji breaks
continuity up rather than being ignored. A slot with no data casts no vote at
all; if nothing votes, the result is `Continuity.NONE` rather than a misleading
"up".

## Patterns

Hammers and shooters are not bar types - they are proportion patterns that
layer on top of any structure.

```python
from strat_core import hammer_shooter, HammerMethod, powerbar_core

hammer_shooter(candle)                                  # (is_hammer, is_shooter)
hammer_shooter(candle, method=HammerMethod.PIN_BAR)
hammer_shooter(candle, match_color=True)                # hammers must be green

powerbar_core(candle, expected_body=rolling_mean)       # the PowerBar shape test
```

## Comparison rules

These are load-bearing. A re-implementation that gets them wrong will agree
with this one most of the time and disagree exactly where it matters.

- **Equal is not a break.** The broken side is strict (`>` / `<`). A high
  exactly matching the prior high has not crossed it.
- **The held side is inclusive** (`>=` / `<=`). An exact touch of the opposite
  extreme keeps a bar a `2`, not a `3`.
- **A close exactly at the open is not above it.** It buckets down (`1d`, `3d`)
  and it breaks continuity up.
- **Gaps get no special case.** A gap-up open above the prior high already
  makes the bar at least a `2u` by the range test.
- **Outside bars are never graded as failed.** An outside bar that closes back
  inside the prior range is still a `3`. There is no `F3` token here, and none
  in the indicator.

## What this package is not

It classifies price structure. It does not decide what to trade, size a
position, manage risk, or backtest anything - and it makes no claim about what
price does next. Those are your decisions to make on top of it.

Nothing here is financial advice.

## Tests

```bash
cd core
python3 -m unittest discover -s tests -v
```

The tests pin the comparison rules above, since those are the parts most
likely to drift in a port.

## License

Mozilla Public License 2.0, same as the rest of the repository. See `LICENSE`
at the repo root.
