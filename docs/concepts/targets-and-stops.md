# Targets & Stops

A signal names the trade; targets and stops price it. For every actionable signal the Suite can project three derived levels - **magnitude** (the measured target), **exhaustion** (the extended target), and a **stop** - plus a shaded **Take Action Window** between trigger and target. This doc covers what each level means in TheStrat method, how the Suite computes it, how it renders, and every setting that touches it.

Bar-type notation is defined in `bar-types.md`; signal types and in-force rules in `signals.md` - this doc assumes both.

---

## The levels at a glance

| Level | Price | Label | Default | One line |
|---|---|---|---|---|
| Trigger | C1 high / low | combo (`2d-1-2u`) | per family | Entry - covered in `signals.md` |
| Magnitude | **C2 high / low** | `MAG` (`TARGET`) | **On** | The measured move: traverse the range the setup formed against |
| Exhaustion | Nearest untested swing beyond | `EXH` (`FINAL`) | **On** | Where the move may structurally finish |
| Stop | Opposite extreme of CC or C1 | `STOP` | Off | Where the signal's premise is dead |
| Take Action Window | trigger -> target, shaded | - | **On** | The zone where entering still leaves room |

Labels in parentheses are the Universal-mode names. All levels are computed **per timeframe slot** from that timeframe's own candles - a 1H magnitude and a Daily magnitude are independent levels that happen to share a chart.

---

## Magnitude - the measured move

TheStrat's target logic is mechanical: a triggered signal is expected to traverse the range it broke out against. Enter a `2d-1-2u` over the inside bar's high, and the target is the high of the `2d` bar - **C2's extreme on the break side**. No projection math, no multipliers; the level already printed.

The Suite snapshots C2's high and low at period open (served from completed bars - see `../engineering/repaint-prevention.md` for why that matters). The line draws from C2's candle forward to the projected end of the current period, in the signal color, **solid**.

When magnitude *doesn't* draw, it's one of these - each is deliberate:

- **C1 already traded through C2's extreme** (`shouldDrawMagnitude`). The "target" would sit behind the entry.
- **The signal is a continuation.** A `2u-2u` or `3-2u` broke C2's extreme by definition, so magnitude is already spent - **exhaustion takes over as the target**.
- **A Failing 2 points the other way.** An `F2u` is a failed upside break; projecting an upside target off it is a contradiction.
- **Dedup.** Magnitude equal to the trigger price: the trigger wins. Equal to the exhaustion level: exhaustion wins. One line per price.
- **Only When In-Force** is on and the signal hasn't triggered yet.

The full gate battery, with the engineering rationale for each, is in `../engineering/drawing-decisions.md` (Stage 4).

---

## Exhaustion - where the move may be done

Exhaustion is the **closest prior swing high (or low) that price hasn't been back through since it printed** - the nearest level that still holds untested structure beyond the magnitude. A move that reaches it has taken out every nearer extreme; expecting more from the same signal is asking a lot.

`findExhaustionLevels` runs inside each timeframe's own bar context: it scans up to ~48 completed bars back for the first pivot (an extreme higher than both neighbors) that also stands beyond every bar between it and now. Each side is independent, and **either can legitimately not exist** - price near its recent extreme has no untested swing above it, and the Suite draws nothing rather than inventing a level. Wherever the Suite needs "the far target" and no exhaustion exists, magnitude serves the same role (break-even triggers, the Advanced exhaustion behaviors below).

Details that follow from the definition:

- The level is a **snapshot taken at period open** and holds for the whole period (`FIX P0-2` in `../engineering/repaint-prevention.md` covers why it's seeded from completed bars only).
- The line starts at the pivot candle that defines it, so you can see *which* swing you're targeting.
- An exhaustion equal to the trigger, or colliding with the opposite side's trigger or magnitude, is discarded as invalid.
- **Only After Magnitude Hit** (off by default) hides exhaustion until price has actually reached magnitude - first target first.

---

## Hit levels turn grey, not off

When price touches a magnitude or exhaustion level, a per-period latch sets and the line changes to the **Crossed** color (Style -> Bullish/Bearish Levels; grey by default). The level stays on the chart for the rest of the period - including exhaustion levels whose trigger line is already gone. A target you reached is a record, not clutter; removing it would hide the most important fact of the session.

The latches are monotone - once crossed, crossed for the period - and they feed everything downstream: line color, Take Action Window removal, break-even stops, and the Advanced exhaustion behaviors.

---

## Take Action Windows

The shaded box between the trigger and the target is the **take-action zone**: while price is inside it, entering still leaves room to the objective. The box is drawn from the setup candle forward, filled and bordered in the signal color at low opacity (Fill 8 / Border 30 by default).

Behavior worth internalizing:

- The window extends to **exhaustion** when it exists and qualifies (**Extend to Exhaustion**, on by default), otherwise to magnitude.
- It renders only while price is actually beyond the trigger in the signal's direction, and **disappears once the destination level is crossed** - the window's job is done, the grey line takes over as the record.
- **Only When In-Force** defaults **on** for windows (unlike the target lines), so a potential setup shows lines but no shading until it triggers.
- **Failing 2 windows are different**: the zone is the reclaimed **C1 range itself** (Advanced -> Take Action Windows -> Include Failing 2s), drawn until price escapes out the far side of the range - matching the F2's in-force-from-detection semantics in `signals.md`.
- **Outside bars** get a trigger->magnitude window on the side they're closing toward (Include Outside Bars), separate from the main path.

Each direction's box checks only its *own* trigger line - the opposite trigger is often legitimately suppressed exactly when a signal is in force (`FIX TAW-1`).

---

## Stops

Off by default - the Suite doesn't presume to manage your risk until asked (Stops -> Stop Levels -> Enable). When on, a stop draws on the opposite side of every signal that goes in force, as a solid line from the current period's open.

**Reference - the one setting to actually think about**:

| Mode | Stop price | Character |
|---|---|---|
| **CC** (default) | The breakout bar's own opposite extreme - tracks live while the candle forms, final when it closes | Tighter. Invalidated when the breakout candle itself is fully reversed |
| **C1** | The prior bar's opposite side, locked the moment the signal goes in force | Wider. Invalidated when the whole setup range is taken out |

**Failing 2s always use CC** regardless of the setting - the failed candle *is* the trade, so its extreme is the only honest invalidation.

The rules that make stops trustworthy:

1. **Sticky for the period.** The stop latches the first time the signal goes in force and persists to period end *even if the signal falls back out of force* - price dipping under the trigger doesn't mean your fill went away. Surviving a chart reload with this lock intact is `FIX P1-a` in `../engineering/repaint-prevention.md`.
2. **Immune to exhaustion gating.** The latch keys off raw in-force *before* the "Exhaustion Disables In Force" behavior is applied - an Advanced display preference can never unhook a protective stop.
3. **Never cosmetically hidden.** Stop lines are excluded from cross-timeframe price-collision suppression (see the comment in `collectLinesFromTF`, and `../DESIGN_CONSTRAINTS.md`). The only thing that removes a stop mid-period is the Lead Signal filter suppressing the counter-trend side it belongs to - a stop never vanishes on its own.

**Break even** (both off by default): move the stop to the entry trigger when price crosses magnitude or exhaustion respectively. Each falls back to the other level when its own doesn't exist, so "break even at magnitude" still works on a signal that only has an exhaustion target. At break even the stop coincides with the trigger line, so the separate stop line and label fold away and the trigger label gains a **`+ STOP`** suffix.

**Color**: *Opposite Signal* (default - a long's stop wears the bearish color, which reads correctly: crossing it is the bearish event), *Match Signal*, or *Custom* with a single color.

---

## Targets and "in force"

Three interactions, all opt-in:

- **Only When In-Force** exists independently for magnitude, exhaustion, the base window, and the window's exhaustion extension (the Failing 2 and outside-bar windows reuse the base window's toggle). Defaults: target lines show on potential setups (`*`-prefixed), windows don't.
- **Exhaustion Disables 'In Force'** (Advanced -> Exhaustion Behavior, off): once a signal hits exhaustion - or magnitude, when no exhaustion level exists - it stops counting as in force. The default (off) says a move past its targets is still a move; turning it on says the move is structurally *complete*, which releases the Lead Signal filter to allow lower-timeframe reversals against it.
- **Exhaustion Excludes from FTFC** (same group, off): a timeframe whose move is complete stops blocking Full Timeframe Continuity from flipping. Same fallback: magnitude stands in when exhaustion doesn't exist.

---

## Detection vs signal nuances

`signals.md` defers these; here they are:

- **Outside bars (3 Exp)** get their own target toggles (Advanced -> Outside Bars -> Show Magnitude / Show Exhaustion for Outside Bars, both on) *underneath* the global toggles (`FIX CSS-2` made that gating symmetric). Targets project only on the side the bar is closing toward - an outside bar is a two-sided event, but its targets are not.
- **An inside bar that becomes a 3** (CC engulfs C1) projects magnitude only when 3-Exp display is on - no orphan targets from a signal family you've hidden.
- **Failing 2s** never draw targets on the failed side; their actionable geometry is the reclaimed C1 range (the F2 window above), and their stop is always CC.
- **A flat (doji) C2** counts as the reversal side for in-force purposes (`FIX CSS-1`), which matters here because the sticky stop latch and every Only-When-In-Force gate read that same in-force verdict - table, lines, windows, and stops agree by construction.

---

## Every setting that touches these levels

| Group | Setting | Default |
|---|---|---|
| Targets - Magnitude & Exhaustion | Show Magnitude Levels / Only When In-Force | On / Off |
| Targets - Magnitude & Exhaustion | Show Exhaustion Levels / Only When In-Force / Only After Magnitude Hit | On / Off / Off |
| Targets - Take Action Windows | Show Take Action Windows / Only When In-Force | On / On |
| Targets - Take Action Windows | Extend to Exhaustion / Only When In-Force / Fill & Border Opacity | On / On / 8 & 30 |
| Stops - Stop Levels | Enable / Reference / Break Even at Mag / at Exh / Color Mode / Custom Color | Off / CC / Off / Off / Opposite Signal / white |
| Style - Bullish & Bearish Levels | Crossed colors (hit-level grey) | greys |
| Advanced - Exhaustion Behavior | Exhaustion Disables 'In Force' / Excludes from FTFC | Off / Off |
| Advanced - Outside Bars | Show Magnitude / Show Exhaustion for Outside Bars | On / On |
| Advanced - Take Action Windows | Include Failing 2s / Include Outside Bars | On / On |
| Alerts - Detailed | MAG / EXH / STOP fields appended to the consolidated alert | Off |

One performance note: with both target toggles off, the exhaustion pivot scan doesn't run at all (see `../engineering/performance.md`).

---

*Why a specific level isn't drawing: the gate-by-gate walkthrough and diagnostic table in `../engineering/drawing-decisions.md`. Why none of these levels move on reload: `../engineering/repaint-prevention.md`.*
