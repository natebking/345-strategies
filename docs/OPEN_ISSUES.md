# Open issues

Confirmed problems not yet fixed. Each entry states the evidence, so nobody has to
re-derive it. Remove an entry when it ships, with the `FIX` tag that closed it.

## Fractional-tick instruments print decimal prices in alerts and labels

**Severity:** real bug, narrow blast radius. Wrong on the bond complex, correct everywhere else.

Six sites format prices with `str.tostring(price, format.mintick)`:

- `pine/TheStratSuite_v3.1.0.pine:2042` — the price appended to a chart label when
  *Show Price in Label* is on
- `pine/TheStratSuite_v3.1.0.pine:2828, 2832, 2836, 2840` — the trigger, magnitude,
  exhaustion and stop prices in enriched alert messages
- `cross-levels/CrossLevels_v0.1.0.pine:1012` — level labels

`format.mintick` rounds to the symbol's tick and renders the result as a decimal. On
instruments TradingView displays fractionally, the two disagree. On ZB (mintick 1/32
of a point) an alert reads `STOP 110.234375` while the chart shows `110'07'5`. A trader
cannot match the alert to the chart without doing arithmetic.

Affected: ZB, ZN, ZF, ZT and the rest of the Treasury complex. Unaffected: equities,
indices, crypto, FX, and every other decimal-quoted symbol, which is nearly all use.

**Fix:** write an `asFractional` formatter, roughly 100 lines of deterministic
arithmetic, and unit-test it against ZB1! quotes. Do not import
`n00btraders/PriceFormat` for this: its signature is
`formatPrice(price, precision, language, allowPips)`, and Pine cannot read the chart's
precision or language, so importing it forces two user-facing inputs into the settings
panel to configure something the platform already knows. Only the fractional branch is
needed. (Prior art reviewed 2026-08-18.)

**Where it belongs:** PineDraw, so Cross Levels and the Suite share one implementation.

## HTF requests are not guarded by the requested timeframe

`pine/TheStratSuite_v3.1.0.pine:963-968` issue six `request.security` calls with the
user's timeframe strings unconditionally. `validTimeframe`
(`timeframe.in_seconds() <= timeframe.in_seconds(tf)`, line ~1230) gates *consumption*,
so a slot set below the chart timeframe is never acted on. PineCoders recommends
blocking the request itself rather than the result.

**Deliberately not fixed yet.** Correctness is already handled at consumption, the
change touches the most repaint-sensitive code in the project, and it should not ride
along with a release that is already migrating classification to a library. Do it as
its own change, with its own verification pass, on a chart where a slot is genuinely
set below the chart timeframe.
