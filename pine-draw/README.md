# PineDraw

Drawing and labeling components for Pine v6. Extracted from [TheStrat Suite](../pine/), where they render six timeframes of levels on a single chart without running out of objects.

Nothing here knows anything about TheStrat, or about any strategy. It is the layer underneath: put an object at an exact price and time, keep it updated, and keep the chart readable when several of them land on the same price.

## What's in it

**Update in place, don't delete and recreate.** The obvious way to redraw a level is to delete it and make a new one every tick. That works until the chart is busy, and then you are churning hundreds of objects a second against TradingView's per-script cap. `updateLine`, `updateBox`, `clearLine` and `clearBox` mutate what already exists and only allocate when there is nothing to mutate.

**A label pool.** Labels are the easiest way to blow the object budget, because most scripts recreate all of them on every bar. `LabelPool` keeps them allocated and rewrites their contents. Call `reset()` at the top of a render pass and `acquire()` once per label; anything left over from the previous pass is blanked rather than deleted, so the next pass reuses it.

**Price consolidation.** Two levels at the same price produce two labels stacked on the same pixel row, and the text becomes unreadable. `LabelSet` groups labels by price with a tolerance you choose, merging them into one row. This is the difference between a script that scales to several timeframes and one that doesn't. `ColoredLabelSet` is the version that matters once your levels come from different sources: each row keeps its first entry's text color and time anchor, later entries append their text, and an entry whose text is already present is skipped instead of repeated.

**A tight pass lifecycle.** `reset()` starts a render pass and `trim()` ends it, deleting every pooled label beyond the ones acquired — so switching a feature off removes its labels instead of leaving blanks against the object cap. `tablePos()` maps a position dropdown to the table constant, because every script with a settings table writes that switch eventually.

## Use

Add the library to your script:

```pine
//@version=6
indicator("My Levels", overlay = true)
import SpinTrades/PineDraw/2 as draw

var draw.LabelPool pool = draw.newPool()
var line priorHigh = na

if barstate.islast
    pool.reset()
    endTime = time + timeframe.in_seconds(timeframe.period) * 1000 * 10

    priorHigh := draw.updateLine(priorHigh, time[1], high[1], endTime, high[1], color.teal, 1, draw.lineStyle("Dashed"))

    set = draw.newColoredSet()
    set.add(high[1], "prior high", color.teal,   int(na), " + ", syminfo.mintick)
    set.add(low[1],  "prior low",  color.maroon, int(na), " + ", syminfo.mintick)
    set.flushChips(pool, endTime, false, color.white, draw.textSize("Small"))
    pool.trim()
```

`PineDraw.pine` includes that demo at the bottom, so you can paste the whole file into the Pine editor and see it run before importing anything.

## Choosing a merge tolerance

`add()` takes a tolerance in price units, which is the one number worth thinking about:

- `0` merges only exact prices.
- `syminfo.mintick` merges within one tick. A sane floor.
- A fraction of `ta.atr(14)` scales across instruments, so the same script behaves on SPX and on a crypto pair without retuning.

Labels overlap by pixels, not by price, and Pine cannot measure pixels. A tolerance derived from recent range is the closest practical proxy.

## Status

Published on TradingView, current import `SpinTrades/PineDraw/2` (v2, 2026-08-13;
v1 2026-08-12): https://www.tradingview.com/script/L1Yo5Rir-PineDraw/

The primitives are the ones running in TheStrat Suite; the `LabelSet` grouping is a
generalization of the consolidation in that script, with the tolerance made an argument
instead of being fixed at one tick. Version-to-commit mapping lives in the root
`PUBLISHED.md`.

## License

Mozilla Public License 2.0.
