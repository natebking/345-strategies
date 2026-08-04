# PineDraw

Drawing and labeling components for Pine v6. Extracted from [TheStrat Suite](../pine/), where they render six timeframes of levels on a single chart without running out of objects.

Nothing here knows anything about TheStrat, or about any strategy. It is the layer underneath: put an object at an exact price and time, keep it updated, and keep the chart readable when several of them land on the same price.

## What's in it

**Update in place, don't delete and recreate.** The obvious way to redraw a level is to delete it and make a new one every tick. That works until the chart is busy, and then you are churning hundreds of objects a second against TradingView's per-script cap. `updateLine`, `updateBox`, `clearLine` and `clearBox` mutate what already exists and only allocate when there is nothing to mutate.

**A label pool.** Labels are the easiest way to blow the object budget, because most scripts recreate all of them on every bar. `LabelPool` keeps them allocated and rewrites their contents. Call `reset()` at the top of a render pass and `acquire()` once per label; anything left over from the previous pass is blanked rather than deleted, so the next pass reuses it.

**Price consolidation.** Two levels at the same price produce two labels stacked on the same pixel row, and the text becomes unreadable. `LabelSet` groups labels by price with a tolerance you choose, merging them into one row. This is the difference between a script that scales to several timeframes and one that doesn't.

## Use

Add the library to your script:

```pine
//@version=6
indicator("My Levels", overlay = true)
import natebking/PineDraw/1 as draw

var draw.LabelPool pool = draw.newPool()
var line priorHigh = na

if barstate.islast
    pool.reset()
    endTime = time + (time - time[1]) * 10

    priorHigh := draw.updateLine(priorHigh, time[1], high[1], endTime, high[1], color.teal, 1, draw.lineStyle("Dashed"))

    set = draw.newSet()
    set.add(high[1], "prior high", " + ", syminfo.mintick)
    set.add(low[1],  "prior low",  " + ", syminfo.mintick)
    set.flush(pool, endTime, false, color.new(color.black, 20), color.white, draw.textSize("Small"))
```

`PineDraw.pine` includes that demo at the bottom, so you can paste the whole file into the Pine editor and see it run before importing anything.

## Choosing a merge tolerance

`add()` takes a tolerance in price units, which is the one number worth thinking about:

- `0` merges only exact prices.
- `syminfo.mintick` merges within one tick. A sane floor.
- A fraction of `ta.atr(14)` scales across instruments, so the same script behaves on SPX and on a crypto pair without retuning.

Labels overlap by pixels, not by price, and Pine cannot measure pixels. A tolerance derived from recent range is the closest practical proxy.

## Status

Version 0.1.0, published as a Pine library. The primitives are the ones running in TheStrat Suite; the `LabelSet` grouping is a generalization of the consolidation in that script, with the tolerance made an argument instead of being fixed at one tick.

## License

Mozilla Public License 2.0.
