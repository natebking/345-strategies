# The Strat Grammar

A precise, implementation-independent definition of the price action states used in TheStrat. If you are building a bot, labeling a dataset, or writing your own indicator, this is the layer to agree on first.

Everything here is a definition, not a strategy. Nothing in this document tells you what to trade.

Version 0.1.0. Derived from the reference implementation shipped in TheStrat Suite.

---

## 1. The core model

Every candle reduces to one four-field tuple. Every notation you have seen on a chart is a projection of it.

| Field | Type | Meaning |
|---|---|---|
| `structure` | `INSIDE` \| `TWO_UP` \| `TWO_DOWN` \| `OUTSIDE` | what this candle did to the prior candle's range |
| `above_open` | bool | did it close above its own open |
| `failed` | bool | did a directional break get rejected |
| `live` | bool | is the candle still forming |

**The tuple is the truth. Notations are projections.** When two displays disagree, resolve them back to the tuple before assuming a bug.

`structure` and `above_open` are orthogonal. They answer different questions about the same candle and neither implies the other.

---

## 2. Structure

Compare the candle's high and low to the **prior** candle's high and low.

| Structure | Condition |
|---|---|
| `INSIDE` | `high <= prior_high` and `low >= prior_low` |
| `TWO_UP` | `high > prior_high` and `low >= prior_low` |
| `TWO_DOWN` | `low < prior_low` and `high <= prior_high` |
| `OUTSIDE` | `high > prior_high` and `low < prior_low` |

Three consequences worth stating explicitly, because they are the usual source of disagreement between implementations:

**Equal is not a break.** A high exactly equal to the prior high has not crossed it. A candle with an equal high and a held low is `INSIDE`.

**Gaps do not get their own structure.** A gap-up open above the prior high already implies `high > prior_high`, so the candle is at least `TWO_UP`. If it also trades below the prior low it is `OUTSIDE`. Classification always tests the range, never the open.

**A `TWO_UP` can close red.** The direction in `TWO_UP` names which side broke, not the candle's color.

---

## 3. Sign (`above_open`)

```
above_open = close > open
```

A close exactly at the open is **not above**. It buckets down.

This is a separate channel from structure. It is what Full Timeframe Continuity is built from, and it supplies the direction suffix on structures where "which side broke" cannot.

The suffix `u`/`d` in conventional notation means two different things depending on the digit:

| Token | The digit says | The suffix says |
|---|---|---|
| `2u` / `2d` | one side broke | **which side broke** |
| `1u` / `1d` | nothing broke | close above / below open |
| `3u` / `3d` | both sides broke | close above / below open |

This overload is the single most common misreading of Strat notation. Keep the two channels separate internally and render the convention only at display time.

### The two projections

Because of that overload, this grammar defines two renderings of the same state. Both are normative; an implementation may emit either, but must name which one it is emitting.

**Chart notation** is the community convention above: `1u`, `2d`, `F2u`, `3d`. The u/d overload lives at this display boundary and nowhere else.

**Glyph notation** removes the overload. The token never carries sign — `1`, `2u`, `2d`, `F2u`, `F2d`, `3` — where u/d on a 2 is the break side, part of structure. The sign channel is rendered exclusively as a suffix: `>` for close above open, `<` otherwise. So a red 2u is `2u<`: break side and sign visibly separate. Examples: `1>`, `F2u<`, `3<`.

Glyph notation is what programmatic surfaces should emit, and it is the `display` form priceactionapi serves. The two projections are always translatable through the tuple, never directly through each other's strings.

---

## 4. Failed (Failing 2 / Range Reclaim)

A **Failing 2** is a directional candle whose break was rejected: price took out one side of the prior range and came back.

Only `TWO_UP` and `TWO_DOWN` can fail. `INSIDE` broke nothing and `OUTSIDE` broke both sides, so neither has a single break to reject.

`failed` is method-dependent. Four methods are defined:

| Method | Condition |
|---|---|
| `RECLAIM` | the candle closes back inside the prior candle's range |
| `OPEN` | the candle closes against its break direction (a `TWO_UP` closing at or below its open) |
| `RECLAIM_AND_OPEN` | both |
| `RECLAIM_OR_OPEN` | either |

`RECLAIM` is the reference default.

**The direction letter names the break that failed, not the trade it implies.** `F2u` is a failed upside break, which is a bearish condition. `F2d` is a failed downside break, which is bullish.

Also known as a Range Reclaim, a Potential 3, or a 1-bar Rev Strat.

### Notation is tense-free

Always uppercase `F2u` / `F2d`, live or closed. Case is not a liveness marker. Case-significant notation cannot be spoken aloud, is illegible at small sizes, and is a footgun in any API or query context.

Liveness is carried by position (the last token of a combo is the forming candle), by a `*` prefix for a state that has not confirmed, or by words.

---

## 5. Combos

A combo is an ordered sequence of candle states, **oldest to newest**.

`2d-1-2u` means: two candles back was `TWO_DOWN`, the prior candle was `INSIDE`, the current candle is `TWO_UP`.

- `*` prefix marks a **potential** combo: the current candle has not yet broken the trigger level.
- `F` inside a combo marks a slot that was itself a Failing 2. `F2d-2u` is a failed downside break followed by upside follow-through.
- Separators are cosmetic. `2d12u` and `2d-1-2u` are the same combo.

Slot names used throughout: `CC` is the current (forming) candle, `C1` the prior candle, `C2` two back, `C3` three back.

---

## 6. Proportion patterns (hammer / shooter)

Not structures. These are layered on top of any structure and defined by where the body sits within the candle's range. A hammer rejected the low; a shooter rejected the high.

Let `range = high - low`, `body = abs(close - open)`. A zero range candle is neither.

| Method | Hammer | Shooter |
|---|---|---|
| `BROAD` | open and close both strictly above the range midpoint | open and close both strictly below the midpoint |
| `CLASSIC` | body <= 30% of range, lower wick >= 3x body, upper wick <= 35% of range, body center in the top third, close within 25% of the high | mirrored |
| `PIN_BAR` | open and close both within the top 25% of the range | open and close both within the bottom 25% |

`BROAD` is the reference default. A body centered exactly at the midpoint is neither pattern, under any method.

Under `CLASSIC`, a body below 0.1% of the range does not qualify: the wick-to-body ratio needs a real body, so a doji is never a classic hammer or shooter.

An optional color filter additionally requires a hammer to close above its open and a shooter to close below.

---

## 7. Full Timeframe Continuity

FTFC is built **entirely from the sign channel**, across a set of timeframes evaluated at the same moment.

| Reading | Condition |
|---|---|
| `UP` | every monitored timeframe has `above_open == True` |
| `DOWN` | every monitored timeframe has `above_open == False` |
| `CONFLICT` | anything else |

Conflict is the resting state. Full continuity is the exception, which is what makes it information.

**Do not reconstruct FTFC from structure.** A `2u` can close red. Only the sign channel is authoritative.

---

## 8. What this document deliberately does not define

Signal selection, entry triggers, targets, stop placement, filtering, and anything that constitutes a trading decision. Those are strategy, and they belong to the implementation that consumes this grammar, not to the grammar.
