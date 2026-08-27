# Invalidation Stop Classic

An always-in stop line. One line is on the chart at all times — blue below price while the
working read is long, orange above price while it is short — stepping along completed
structure, and a touch flips it to the other side. It answers one question: where is the
current move invalidated by price, right now.

Forked from my PA Invalidation Stop's Classic path. That script decides *when* a side may
display (neutral state, direction-support gates, re-entry cooldowns); this one deliberately
doesn't. The line is the trigger, and every state change goes through price trading at a
level. There is no confirmation logic — a wick through the line flips it, which means sweeps
get paid for in whipsaws and real breaks are never held through. That trade-off is the
design, not an accident.

## The rules

- **Base**: the prior completed 30m and 60m extremes. Long stop = the tighter prior low,
  short stop = the tighter prior high, one-way ratchet within a leg.
- **Tighten on 2-in-direction**: at each 30m/60m close, a bar that closed beyond its own
  two-back extreme in the trade direction pulls the stop to that bar's low/high. Close-based,
  so a completed outside bar that closed in-direction counts too.
- **F2 tighten**: a forming 30m/60m that took the prior extreme while the last 15m closed
  back inside pulls the stop to the prior 15m extreme.
- **Flips** seed at the tightest completed level strictly beyond the broken one (pool:
  prior 30m/60m highs and lows plus the prior day's extremes). Anchoring at the broken level
  rather than the chart bar's close is what makes the 1m and 5m charts draw the same line.
- **Session reset**: at the regular-session open the overnight leg is forgotten and the line
  re-seeds from the open — after a gap, at the gap-fill level (yesterday's extreme) instead
  of across the gap.
- **3-override** (outside-bar latch): ships OFF. When enabled, a live 15m outside bar
  re-anchors the stop once to its far extreme; 30m/60m outside bars never do — honoring an
  hour-scale outside bar's extreme parks the stop the width of the hour away, which is not
  a stop.

## Status

A working chart tool that is still being shaped against live tape. Every design decision is
dated in the file header and in comments next to the code it governs, including the ones
that were tried and reverted. Runs on chart timeframes at or below 15m. Diagnostics: the
"Emit diagnostic Pine Logs" input logs every flip, seed, re-level, and session reset with
the levels involved. Not published on TradingView.

License: MPL-2.0, same as everything here.
