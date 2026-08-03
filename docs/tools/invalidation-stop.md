# Price Action Invalidation Stop Loss

`pine/tools/PA_Invalidation_Stop.pine`

A stop that sits where the trade would be **wrong**, not at a fixed distance
from where you got in.

A fixed-dollar or raw-ATR stop asks "how much am I willing to lose?" This one
asks a different question: "what would have to happen for the reason I took
this trade to stop being true?" That level is structural - the prior completed
30-minute or 60-minute high or low - so it moves when structure moves, and it
only ever moves in one direction.

Not part of TheStrat Suite indicator. It ships as its own script.

---

## How the stop is placed

For a long, two candidate levels matter:

- the **tighter** of the prior completed 30m and 60m lows - the immediate
  invalidation, and the default structural stop
- the **looser** of the two - the deep structural backstop the breathing
  engines are floored at

Mirror both for a short. Every higher-timeframe read is taken from a
**completed** bar, so the level does not move under you as the current bar
forms.

The stop ratchets. For a long it only ever moves up; a level that would loosen
it is ignored.

## What tightens it

- **A 2 in the trade's direction closes.** A 30m or 60m bar closes having taken
  out its prior high (for a long), and the stop pulls up to that bar's low.
  This is the "the structure just confirmed, so I can afford less room" case.
- **A Failing 2 against the trade.** The higher timeframe broke out and got
  reclaimed - the breakout failed - so the stop pulls to the last 15m low.
- **An outside bar, optionally.** With `3-override` on, a live outside bar
  holds the stop at its own high or low while it develops.

## The six versions

One dropdown picks the behavior; everything else is refinement.

| Version | What it does |
|---|---|
| **Classic** | The structural step-stop above. Prior 30m/60m level, plus the 2 and Failing-2 tightens. |
| **Mike's Version** | Adds a live classification of the forming higher-timeframe bar (C1 to C4) and gates exits on confirmation rungs, plus a Catastrophe Stop. |
| **Strat-PSAR** | A parabolic trail that breathes between the looser structural level and price, accelerating as the trade extends. |
| **Aggression** | A continuous price-action aggression index (close position in range, signed body, wick imbalance) breathes the trail between an ATR-scaled minimum and maximum distance. |
| **Compare: Classic + Mike's** | Draws both, so you can see where they diverge before committing to one. |
| **Classic + Cascade Break** | Classic, plus a timed exit when the 30m and 60m both sit on the wrong side of their opens for N consecutive minutes. Whichever fires first. |

**Mike's Version** draws two lines: the solid bright line is the enforced
invalidation, and the dim line is the soft tightened ratchet it is pulling
toward. The dim line is context, not an exit.

## The Catastrophe Stop

Used by Mike's Version and the two breathing engines. If a single 5-minute bar
travels more than `multiplier x average 5m range` against the position, the
trade exits immediately regardless of structure. A breathing trail can sit
wider than the immediate invalidation, and this is the net under it for
news-spike and flash-move cases.

## Candle-shape adjust (off by default)

An optional layer. At each 15m/30m/60m close it scores the just-closed candle:

- A shape **for** the trade (a hammer while long, a PowerBar in your direction)
  **widens** the stop toward that candle's own low - giving the trade room,
  bounded to a real bar level, floored at the structural invalidation.
- A shape **against** the trade **tightens** the stop toward price.

The largest timeframe that just closed with a shape wins. Hammer and shooter
detection uses the Suite's "Broad (Loose)" definition; the PowerBar test is the
core morphology described in [powerbar.md](powerbar.md).

## No-repaint

Every higher-timeframe level comes from a completed bar
(`request.security` with `[1]` and `lookahead_on`). Forming-bar highs, lows and
opens are accumulated from chart bars rather than requested, so nothing the
indicator remembers depends on data that was not available at the time.

Forming-bar movement is not repaint: a live stop level updating tick by tick is
the product. The rule is that a reload must reproduce it.

## Settings worth knowing

- **Tighten on 2-in-direction** (on) - the main ratchet.
- **Use neutral state** (on) - when a stop is hit and the opposite direction
  is not supported, stand aside rather than flipping straight into a reverse.
- **Mark stop-trigger points** (on) - plots an X exactly where the stop
  actually triggered out, which distinguishes a real trail-out from the step
  line merely re-levelling at a timeframe boundary.
- **Arm cascade only after N R** (0) - in Cascade Break mode, ignore cascade
  breaks until the trade has first reached a given R multiple.

## Caveats

Defaults are starting points, not recommendations. The Cascade Break version in
particular is experimental - validate it on your own instrument and timeframe
before relying on it.

Nothing here is financial advice.
