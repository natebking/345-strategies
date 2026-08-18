# Strat Grammar

Technical definitions of the price action states used in TheStrat, plus a Python reference implementation that agrees with the indicator they came from.

If you are building a bot, labeling a dataset, or writing your own indicator, this is the layer to agree on before you write any strategy code.

## Why this exists

The Strat is widely used and loosely specified. Most disagreements between two implementations turn out to be the same three or four edge cases: whether an equal high counts as a break, what the `u` in `2u` actually refers to, whether a gap gets its own type, and when a directional bar counts as failed.

This package answers those in one place, then proves the answers against a working implementation.

- **[SPEC.md](SPEC.md)** is the definition, written to be implementable in any language.
- **`strat_grammar/`** is the Python reference implementation.
- **`tests/test_pine_parity.py`** checks it against the Pine Script running in [TheStrat Suite](../pine/) in this repo across 40,000 randomly generated bars, in both detection methods. Currently zero mismatches.

That last part is the point. A specification that disagrees with a shipped implementation is documentation, not a specification.

## The Pine implementation

`StratGrammar.pine` is the same grammar as a TradingView library (`import SpinTrades/StratGrammar/1`). It exports the `BarState` type, `classify`, both notation projections (`notation()` chart-convention, `display()` glyph-convention with `>`/`<`), the hammer/shooter methods, and `continuity` — with the Suite's exact settings strings accepted as method arguments so an indicator can pass its inputs straight through. TheStrat Suite itself imports it as of v3.1.0. Published versions are recorded in the repo root `PUBLISHED.md`.

## Install

```bash
pip install -e grammar/
```

No dependencies. Python 3.10+.

## Use

```python
from strat_grammar import Candle, classify, continuity

prior   = Candle(open=100, high=110, low=90, close=105)
current = Candle(open=106, high=115, low=95, close=101)

state = classify(current, prior)
state.structure      # Structure.TWO_UP  - it broke the prior high only
state.above_open     # False             - but it closed red
state.failed         # True              - and closed back inside the range
state.notation()     # 'F2u'             - a failed upside break
```

Continuity reads across timeframes, from the sign channel only:

```python
continuity([spy_5m, spy_1h, spy_1d])   # Continuity.UP | DOWN | CONFLICT
```

## The model

Every candle reduces to one tuple:

| Field | Values |
|---|---|
| `structure` | `INSIDE` / `TWO_UP` / `TWO_DOWN` / `OUTSIDE` |
| `above_open` | bool |
| `failed` | bool |
| `live` | bool |

Everything you have seen on a chart is a projection of that tuple. `structure` and `above_open` are orthogonal: a `2u` can close red, which is why `failed` exists as its own field rather than being inferred from color.

## What this does not do

No signals, entries, targets, stops, or filtering. Those are strategy decisions and they belong to whatever consumes this, not to the grammar.

## License

Mozilla Public License 2.0, same as the rest of this repository.
