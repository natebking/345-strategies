# Display studies: decisions and test record

Updated 2026-09-02. This log covers `price_display.pine`, `instrument_display.pine`,
`composition_overlays.pine`, and `console_strip.pine`. They are standalone siblings,
not part of TheStrat Suite.

I started with Rivian's use of large numbers, quiet supporting text, open space, and a
small number of colors. The aim was to carry those ideas into a usable TradingView chart,
not reproduce its logo, fonts, or vehicle interface. The reference is a public website,
not a published Rivian UI kit. This is an independent visual study.

## What is verified, and what is still a study

| Item | State |
| --- | --- |
| Price Display source | Compiled, saved, displayed, and checked after reload on SPX 1D |
| Four native chart palettes | Applied and compared on the same SPX daily candle composition; saved and reloaded |
| Large default-font headline and monospace labels | Verified in the price display at 56pt and 11pt |
| Instrument Display | All three modes compiled, saved, rendered, and checked after saved-layout reload on BTCUSDT 1D |
| Horizon Header and Inset Panel | Current source compiled; correct chart instances saved, reloaded, and captured on SPX 1D at 1464 × 681; no text clipping or candle overlap |
| Console Strip | Current source compiled; correct 48pt instance saved, reloaded, and captured on SPX 1D at 1464 × 681 in a separate approximately 141px pane; complete text and no candle overlap |
| Further ideas below | Candidates only; not implemented or represented as tested features |

The source, this log, and the chart-only [composition gallery](README.md#composition-gallery)
are the portable record. No account-specific layout links, account data, or screenshots
containing browser/interface chrome are included.

## Reference research and its boundaries

The initial reference audit was of the public [Technology page](https://rivian.com/technology),
not a running copy of the vehicle operating system. Observations were recorded on
2026-08-21 at a 1470 × 751 desktop viewport. They describe that rendition, not a permanent
brand specification or a rule for every screen.

### Observed in the public references

- Site inspection identified Adventure and Adventure Mono font assets. The main editorial
  text used Adventure, primarily regular 400 and semibold 600. Those proprietary files
  are not part of this repository; native default and monospace are the Pine substitutes.
- The page contrasted very large headings with modest body copy. Measured examples were
  approximately 96/92px hero text, 120/115px feature text, 56px section headings, and 16/24px
  body text. Desktop gutters were about 80px and large vertical section gaps about 128px.
  These informed hierarchy and whitespace, not literal chart dimensions.
- Light editorial fields alternated with dark technical scenes. App references grouped
  functions by color, including blue climate controls and green energy/charging controls.
- The web page used restrained parallax, staged entrances, masked character reels,
  auto-advancing media, and sticky device chapters with screen crossfades. The audit found
  reduced-motion handling and pause controls in relevant web components.

The [App 2.0](https://rivian.com/stories/app-2-0) and
[App 3.0](https://rivian.com/stories/app-software-3-0) stories were additional UI references.
The [Epic Games HMI case study](https://www.unrealengine.com/spotlights/rivian-brings-adventurous-spirit-to-new-display-ui-powered-by-unreal-engine)
describes the separate in-vehicle experience. Web page choreography should not be presented
as a measured specification for that vehicle UI.

### Inferences carried into the charts

One dominant readout, short labels, quiet secondary text, limited color, and open space
were the transferable ideas. The chart did not need a literal phone frame, a vehicle
illustration, or scrolling chapters. Large numbers needed an explicit metric and timeframe
to be useful rather than decorative.

### Access and motion work not completed

The public-source search did not locate an official downloadable UI kit, complete style
guide, vehicle-OS copy, or simulator. That is a search result, not proof that no such
resource exists. The [official iPhone app](https://apps.apple.com/us/app/rivian/id1570215232)
was identified as a possible next reference, but was not downloaded for this work. A
deeper live-feature audit may require appropriate account and vehicle access.

Motion can be studied through official media and the public website. A licensed-font web
specimen with original artwork remains a candidate, not an implemented deliverable here.
Pine table updates are driven by script executions; they are not a CSS animation engine
with a general scroll timeline, frame scheduler, or transition layout system. No
indicator attempts to copy the page's motion or includes Rivian source, fonts, or media.

## Four native chart palettes

These settings are manual TradingView chart settings. The scripts' Palette inputs only
style their tables. Changing an input does not change the chart canvas, candles, scale
labels, or surrounding TradingView interface.

| Setting | Cloud & Field | Ink & Paper | Charging Green | Night Expedition |
| --- | --- | --- | --- | --- |
| Solid canvas | `#F6F6F6` | `#F6F6F6` | `#F2F2F2` | `#02171C` |
| Up body | `#5F6559` | `#F6F6F6` | `#72DC57` | `#84ACB3` |
| Up border and wick | `#5F6559` | `#101512` | `#5F6559` | `#84ACB3` |
| Down body, border, and wick | `#DE311E` | `#101512` | `#293846` | `#FFAC03` |
| Scale text | `#606060` | `#606060` | `#606060` | `#B8C7CB` |
| Crosshair | `#1676CA` | `#1676CA` | `#1676CA` | `#84ACB3` |
| Display headline | `#101512` | `#101512` | `#101512` | `#F6F6F6` |
| Display supporting text | `#606060` | `#606060` | `#606060` | `#A5B5B7` |
| Short decorative rule | `#FFAC03` | `#FFAC03` | `#FFAC03` | `#FFAC03` |

All four use ordinary Candles, with previous-close coloring off and body, border, and
wick colors at full opacity. Grids are off. Scale labels stay visible. The comparison
used 14px native scale labels, 20% top margin, 15% bottom margin, and a 10-bar right margin.
Those are starting values, not a promise of identical layout on every display.

### Two greens, not one

The first Cloud trial used `#677366`, an approximate sage from the earlier page study.
It was a usable muted chart color, but it should not have stood in for a verified
signature Rivian green. I replaced it after inspecting the official color story.

Rivian describes its Pantone-developed **Rivian Green** as a foundational neutral with
forest, technical-gray, and blue-undertone qualities. The article does not give a
canonical hex or RGB specification. I sampled the flat labeled swatch in its official
digital image: RGB `(95, 101, 89)`, or `#5F6559`. The sampled interior was uniform in the
512px PNG rendition. This is a measured digital reproduction, not a Pantone-to-sRGB
specification. [Color story](https://rivian.com/stories/pantone-partner-rivian-green-color),
[swatch image](https://media.rivian.com/image/upload/w_512,f_png,q_auto,c_lfill/v1/papyrus/stories/pantone-partner-rivian-green-color-original-564e82d1)

The bright green in the charging UI is different. In the official Technology page's
charging-schedule image, the most frequent green in the sampled ring was RGB
`(114, 220, 87)`, or `#72DC57`. The image includes nearby shades from gradients and
quantization, so this is an approximation. It became the Charging Green candle fill.
[Technology page](https://rivian.com/technology),
[charging UI image](https://media.rivian.com/image/upload/f_png/q_auto:good/c_limit,w_512/v3/rivian-com/technology/mobile-app/App%20-%20Charging)

## Trials and decisions

| Trial | What happened | Decision |
| --- | --- | --- |
| Approximate sage up candles | Readable, but did not settle which Rivian green was intended | Superseded by the sampled forest-gray green in Cloud & Field |
| Forest-green and vermilion candles | Conventional up/down reading with a restrained palette | Kept as the Cloud baseline |
| Hollow-looking charcoal candles | Reduced the chart to fill, outline, and price structure | Kept; Ink & Paper was the preferred direction |
| Bright charging-green candles | Brought in the software UI color, but the fill alone was faint on a light canvas | Kept with dark forest borders and wicks, slate down candles |
| Deep teal canvas with powder teal and gold candles | Clear contrast and a distinct dark alternative | Kept as an optional comparison, not a requirement for the light design |
| Four colored palette chips under the number | Looked like a theme demo; table sizing stretched the strip | Key off by default; a short gold rule replaced it |
| Rivian-style typography | Arbitrary custom fonts were not available through the Pine display API | Kept the scale contrast using native default bold and monospace |
| Currency in the header | An index displayed the sentinel `NONE` | Omit blank currency and `NONE` |
| Suspected missing readout during QA | Direct inspection of the saved layout and final screenshot confirmed the readout was present | Palette re-selection was a verification action, not a proven fix; no defect or cause was established |
| Large latest price as the only headline | Established the layout, but repeats a value the chart already shows | Retained as the baseline; three alternative readouts are separate experiments |

### Hollow appearance without a semantic change

Ink & Paper does not use TradingView's separate Hollow candles chart type. It uses an
ordinary candle with a canvas-colored up body and charcoal borders and wicks; down bodies
are filled charcoal. That preserves ordinary close-versus-open coloring.

TradingView's Hollow candles type combines two tests: fill relates close to the current
open, while color relates close to the previous close. Switching to that type only for its
appearance would also change what the visual encoding means.
[TradingView's hollow-candle explanation](https://www.tradingview.com/support/solutions/43000745270-hollow-candle-charts-explained/)

### Typography and space

The original retained pairing is a 56pt bold default-font headline with 11pt native
monospace supporting text. Headline options are 36, 48, 56, and 64 typographic points,
not CSS pixels. The later composition pass increases supporting text where the layout
needs it; those sizes are recorded separately below.
No Rivian font files are imported or distributed. The short gold rule is decoration, not
an essential state marker. A label carries the instrument and chart timeframe, so the
large number does not stand alone without context.

I kept the card in the upper left, away from the newest candles, and left space above the
price action. This is not an automatic collision system. Long prices, long tickers, narrow
charts, and existing top-left tables can still conflict with the card. Smaller headline
sizes and chart margins are the current controls.

## Alternative headline studies

`instrument_display.pine` keeps the same type pairing, top-left anchor, palette canvases,
and short gold rule. Its default palette is Ink & Paper. These are descriptive readouts,
not entries, exits, signals, or probabilities.

| Mode | Formula or content | Boundary behavior |
| --- | --- | --- |
| Range Position | `100 * (close - low) / (high - low)`, bounded to 0–100% | Zero range or missing required data gives `N/A` |
| Relative Range | `(high - low) / ta.sma(high - low, lookback)[1]` | Zero prior average or insufficient history gives `N/A`; a zero current range with a positive prior average gives `0.00×` |
| Instrument | Large `syminfo.ticker`; supporting price and `100 * (close - open) / abs(open)` | Zero or missing open gives `N/A` percentage; long descriptions are omitted |

Range Position is the close's location inside **this chart bar**. It is not a stochastic
lookback calculation, a probability, or a measurement against a daily/session range.

Relative Range uses a 20-bar lookback by default, configurable from 2 to 500. The SMA runs
on every bar and is shifted by `[1]`, so the average excludes the current bar. The current
numerator can still be a partially formed bar compared with completed bars. The ratio is
not time-of-day normalized and is not a forecast or an estimate of expected volatility.
It uses high-low range, not true range or ATR. The selected chart timeframe defines a bar;
no daily or session interpretation is implied.

Instrument mode can include a short instrument description. It is omitted when too long
for the study's fixed text-length limit. That check is a practical width guard, not a
measurement of rendered pixels.

## Composition studies with content held constant

The next clarification changed the direction: the request was for more design options,
not more metric choices. Range Position, Relative Range, and Instrument were content
experiments. I kept them, and the original price readout, as separate references. This
pass changes grouping, alignment, spacing, contrast, and pane placement while keeping
the same price payload.

The comparison uses `SP_DLY:SPX`, 1D, ordinary Candles, and the Ink & Paper native colors.
All three show instrument metadata, latest price, and this bar's absolute/percentage
open-to-close change. The observed values were `7666.60` and `+32.02 (+0.42%)`.
These are capture observations, not fixed values a later run should reproduce. No new
metric or signal was introduced. Empty or `NONE` currency stays omitted, missing required
values produce unavailable output, and a zero open gives an unavailable percentage.

### Horizon Header

`composition_overlays.pine`, with Composition set to Horizon Header, spreads the display
across the top of the main pane: metadata on the left, a centered price, and change on the
right. A thin divider separates the header from price action. The columns are 25% / 42% /
25%, with 4% outer gutters. The price remains 56pt bold default font.

The first 11pt side labels looked too small across the wide header. Increasing them to
14pt made the supporting groups more legible while retaining the two-font hierarchy.
The horizontal grouping provides a clear scan, but fixed percentage columns do not
automatically fit long symbols or prices. Its full-width opaque cells also occupy space
inside the main chart; they do not reserve a separate UI region.

### Inset Panel

The same source, with Composition set to Inset Panel, makes a compact reversed card.
It uses a deep-teal `#02171C` field, a pale `#F6F6F6` 56pt price, `#A5B5B7` supporting
monospace at 12pt, and a narrow `#FFAC03` gold edge. The card is rectangular, with internal
padding and no simulated rounding or shadow. The initial fixed-width version used a
29.75% card plus a 2% outside gutter, with a 27% text column. That version clipped the
headline at 722px width. The revised content column uses Pine's automatic width, while
the outside gutter, narrow edge, and internal padding retain their percentage widths.
There is no longer a fixed total card width. This showed the complete price at 56pt in
the tested wide and narrow frames, but did not solve every spatial conflict.

The card creates a strong contained focal point without changing the candles. The cost
is greater visual weight and an opaque chart footprint. It can cover price structure
or grow too wide for a long value. At 722 × 677, the 56pt card could overlap candles
vertically even with its price fully visible. Manually using 36pt and a 0% top inset
removed overlap in that inspected frame. The desktop recipe remains 56pt with a 3%
inset. The gold edge is decorative, not a signal or status. Automatic content width is
not automatic text scaling, responsive layout, or collision avoidance.

### Console Strip

`console_strip.pine` puts the same payload in a real lower pane. Price sits left,
instrument metadata in the middle, and current-bar change right. The content widths are
36% / 28% / 30%, with 3% gutters. The headline is 48pt bold default; the source
uses 12pt monospace captions and 14pt secondary values.

The separate pane prevents the strip from covering candles while it remains there. It
also takes real vertical space from the chart. At the 1464 × 681 comparison viewport, the
native pane was resized from about 190px to about 141px. Its native indicator title was
hidden to reduce redundant footer text without hiding the indicator itself. The native
main-chart margins are 10% top, 10% bottom, and 10 bars right.

The script uses `overlay=false` and `bgcolor(..., force_overlay=false)`. Its background
belongs to its own pane, not the main price chart. `scale.none` is omitted because it is
valid only with `overlay=true`. Moving the script manually onto the price pane would
change where the background appears, so keep it below the chart. There are no price plots.
[Declaration settings](https://www.tradingview.com/pine-script-docs/language/declaration-statements/),
[background behavior](https://www.tradingview.com/pine-script-docs/visuals/backgrounds/)

### Setup results and learning log

| Trial or constraint | Observation and decision |
| --- | --- |
| New metrics presented as design options | They changed content, not composition. Preserve those studies and hold price content constant for this pass. |
| Horizon's original 11pt side labels | Too small in the wide layout. Increased to 14pt; the large price stays 56pt. |
| Inset supporting text | Uses 12pt monospace with a 56pt price inside the narrower card. |
| Console's first small supporting text | Refined source uses 12pt captions and 14pt values with a 48pt price. Source saving was confirmed, but the on-chart instance still needed updating and an explicit layout save before final persistence could be claimed. |
| Requested 30% and 40% native top margins | Both saved as 25% in this session's UI. Horizon and Inset recipes record 25% top, 15% bottom, and 10 bars right. This does not establish a platform-wide hard limit. |
| Console's initial lower pane | Reduced from about 190px to 141px. This keeps the strip compact but still spends chart height. |
| Native indicator titles | Hidden for cleaner compositions; the tables remain visible. |
| Source save versus layout save | Console's refined source was saved, but reloading before an explicit layout save retained an older on-chart instance. A historical read-only source view is expected for an instance on an older version. No application defect was established. |
| Reliable update workflow | Open the current source from the script library, update or add the correct chart instance, save source and layout, then reload and inspect. Replacing Inset's older instance with the current saved version did not delete its source file. |
| Console's final chart instance | Added the current saved source, removed the older 36pt instance from the chart without deleting its source, and kept the new 48pt instance. Explicit layout save and reload preserved the refined labels, lower-pane placement, and hidden native title. |
| Reload at a different viewport | The viewport changed from 1464 × 681 to 722 × 677. Inset's fixed text column significantly clipped the headline; Console's 48pt price clipped its final digit. The initial narrow fit failed. |
| Inset automatic width | `FIX DISPLAY-WIDTH-1` replaced the fixed 27% content column that clipped the narrow price. The full 56pt price became visible at the narrow frame, but vertical candle overlap remained possible. Manual 36pt with 0% inset fit the inspected compact frame without overlap. |
| Console compact headline | Manual 36pt resolved price clipping at 722 × 677 on an earlier instance, before the final 12pt captions and 14pt supporting values were attached. This was a price-size-only check, not a compact pass for the final version or all its fields. |
| Final wide comparison | Navigated the same 1464 × 681 browser tab through saved layouts to keep the viewport consistent. All three passed explicit layout-save/reload checks and were captured without clipped text or candle overlap. Console intentionally gives the candles less vertical space. |
| Native fonts | Retained default bold and monospace. No proprietary font import or export. |

The baseline's native margins remain 20% top, 15% bottom, and 10 bars right. These new
recipes are composition-specific, not a replacement for the earlier palette record.
Pine's explicit table dimensions are percentages of available pane space. Inset's content
uses native automatic width, not font scaling or responsive layout. Pane height, chart
margins, and headline size still need manual judgment. One narrower viewport exposed
concrete fit problems; it does not
establish general narrow-screen or mobile support. The compact settings are manual
variants of the same inputs, not a new automatic-fit feature. Long values and other
symbols are not covered by this comparison.

The final gallery compares reading order, chart area used or covered, hierarchy,
contrast and visual weight, and manual setup. Horizon scans horizontally across the
chart's top. Inset creates a stronger, contained focal point. Console reserves a separate
information area at the cost of candle height. All three final wide captures are complete;
this does not establish long-text fit or every viewport. Subjective preference remains
separate from compile and reload results.

## Limits that remain

- **These are table displays, not an application layout system.** Pine tables have fixed
  anchor positions and cell sizing. Native automatic cell width does not provide
  HTML/CSS-style panel composition, font scaling, or general-purpose responsive layout.
- **No arbitrary font import.** The display uses the native default and monospace families.
  Headline size is configurable; headline emphasis is fixed bold. Loading Rivian's proprietary font is not part
  of this implementation. [Pine text controls](https://www.tradingview.com/pine-script-docs/visuals/text-and-shapes/)
- **No native UI recoloring from a palette input.** Candle colors, chart background,
  crosshair, scale text, and interface theme remain separate native settings. Console
  Strip has a constant background in its own separate pane; it does not install a theme.
- **No live-data entitlement.** The latest available price can be delayed. These scripts
  show what the chart supplies; they do not obtain a different feed.
- **Synthetic charts stay synthetic.** Heikin Ashi and other nonstandard chart types
  supply their own OHLC. Use ordinary Candles for the tested designs and ordinary bar data.
- **A current-bar value can move.** Current close, high, and low can change intrabar. This
  is deliberate display-only movement, not a latched signal or a record of prior ticks.
- **The crosshair does not select the readout.** The table shows the latest chart bar even
  while inspecting an older one. [Pine tables](https://www.tradingview.com/pine-script-docs/visuals/tables/)
- **Transparent cards need judgment.** Text may overlap candles. The opaque, canvas-matched
  setting is the tested default.
- **Several overlays share chart space.** Compare one display at a time. A separate
  Console pane avoids overlay collisions, but reduces the price chart's available height.
- **Native visibility can reset on reload.** The Hide all drawings view state reset during
  the capture workflow. Recheck it after a reload if a clean comparison is needed. Hide
  drawings temporarily rather than deleting them; no script manages native drawing
  visibility. Do not confuse that control with hiding the display indicator itself.

## Readability checks

The color ratios below are calculations from the selected RGB values, not a complete
accessibility assessment. Thin strokes and small text still need inspection on screen.

| Pair | Contrast |
| --- | ---: |
| Charcoal headline on Cloud | 17.0748:1 |
| Forest-green candle on Cloud | 5.5641:1 |
| Supporting gray text on Cloud | 5.8189:1 |
| Bright charging fill on its light canvas | 1.5515:1 |
| Dark forest outline on Charging's canvas | 5.3714:1 |
| Dark forest outline against charging fill | 3.4620:1 |
| Slate down candle on Charging's canvas | 10.7290:1 |
| Cloud headline on Night | 17.0168:1 |
| Supporting text on Night | 8.6637:1 |
| Gold on Cloud | 1.7421:1 |

The charging fill needs its dark edge. Gold works as a small decorative rule or a filled
chip with dark text, not as thin essential text on the light canvas. The optional palette
key uses contrasting text on each fill; it remains off because it competes with the data.
[W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

## Test record

No local Pine compiler or test runner was used. TradingView is the runtime. Arithmetic
smoke checks outside Pine are useful for formulas but do not establish compilation,
rendering, or reload behavior.

| Date | Script / setup | Recorded result |
| --- | --- | --- |
| 2026-09-02 | Price Display, SPX 1D, ordinary Candles | Clean compile, save, current-price readout, currency omission, and short rule checked |
| 2026-09-02 | Cloud & Field, Ink & Paper, Charging Green, Night Expedition on SPX 1D | Native palettes applied; saved layouts reloaded; all four final captures checked with matched composition |
| 2026-09-02 | Ink & Paper copied layout | Suspected missing readout checked against the actual saved layout and final screenshot; readout and reload check passed, with no confirmed defect |
| 2026-09-02 | Instrument Display, BTCUSDT 1D, all three modes | Clean compile, standalone save, rendering, and saved-layout reload checks passed for each mode; final captures checked |
| 2026-09-02 | Arithmetic edge cases outside Pine | Range low/high/midpoint, zero range, relative-range multiplier, zero denominator, and missing-history examples behaved as specified |
| 2026-09-02 | Horizon Header, SPX 1D | Current source compiled and saved; correct chart instance explicitly saved and reloaded at 1464 × 681; 56pt headline, 14pt monospace, 3% inset, native 25% / 15% margins and 10-bar right margin; full readout without clipping or candle overlap |
| 2026-09-02 | Inset Panel, SPX 1D | Current automatic-width source replaced the older chart instance, then layout saved and reloaded at 1464 × 681; 56pt headline, 12pt monospace, 3% inset, native 25% / 15% margins and 10-bar right margin; full readout without clipping or candle overlap |
| 2026-09-02 | Console Strip, SPX 1D | Current source compiled and added as the only Console instance; explicit layout save and reload at 1464 × 681 retained its 48pt headline, 12pt captions, 14pt values, hidden native title, approximately 141px lower pane, and native 10% / 10% margins with 10 bars right; complete readout and no candle overlap |
| 2026-09-02 | Compact 722 × 677 frame | Initial fixed-column Inset and 48pt Console clipped. Inset automatic width (`DISPLAY-WIDTH-1`) showed the full 56pt price but could overlap candles; manual 36pt / 0% inset removed overlap in the inspected frame. Console 36pt resolved price clipping on an earlier instance before the final 12pt / 14pt supporting text was attached. That was price-size-only coverage, not a final-version compact pass, mobile pass, or general responsive-layout pass |
| 2026-09-02 | Wide chart-only images | All three captures are 1359 × 600 crops from the same 1464 × 681 browser viewport, with matching visible candles and values; inspected for complete text, candle overlap, and publication privacy. Console's candle placement differs vertically because of its separate pane. |

At capture time, Range Position showed `69%`, Relative Range showed `0.60×`, and Instrument
showed the ticker with price, current-bar percentage, and a short description. Those are
observations of a changing chart, not fixed expected values for a later run.

Still to check for the experimental source: every palette/control combination, mobile and
narrow views, long symbols and descriptions, zero-range bars and short history in
TradingView, and behavior around a new bar. Intraday and session-stamped futures coverage
has not been claimed. No Bar Replay pass has been claimed.

The composition pass uses the same SPX daily payload. All three final gallery captures
use a consistent 1464 × 681 viewport. The limited 722 × 677 check exposed fit failures
and verified the specific manual adjustments above. These remain research prototypes,
not automatic responsive layouts. Verification does not establish long-text fit, every
small-pane limit, all headline-size combinations, mobile behavior, new-bar behavior,
or runtime edge cases on other symbols and markets.

### Engineering review gates

- No `request.security` or lower-timeframe request. No HTF slots, preview path, calendar
  parsing, session inference, staleness calculation, or `timenow`.
- No alerts, trading state, or historical candle paint. The only `var` object is each
  display's table; its cells are recreated from current series data on the last bar.
- Console Strip's pane background is a constant color, not historical price-state paint.
  It uses no `force_overlay=true` output and does not recolor the main-chart candles.
- The relative-range SMA has one unconditional global call site, not a per-slot, loop,
  or conditional history buffer. Its prior-bar offset excludes forming-bar data from the
  denominator. [Pine history indexing](https://www.tradingview.com/pine-script-docs/language/operators/)
- Current OHLC values drive transient readouts only. No forming value is latched for a
  later signal, level, or alert. Reload checks compare the current chart state, not a
  claim that an unfinished bar should freeze while new data arrives.
- Existing Suite engines, grammar, libraries, and archived sources are untouched.

## Candidate ideas, not implemented

| Idea | Why test it | Required guardrail |
| --- | --- | --- |
| User-selected metric input | Make the headline useful beyond these three fixed studies | Define units, missing values, formatting, and whether the selected source is forming or confirmed; do not imply support before testing |
| TheStrat structure and context | Show one useful state such as an inside or directional bar | Reuse the repository's grammar. Structure and close-versus-open sign are different channels; do not turn a red `2u` into `2d` |
| A short status word | Read faster than a row of numbers | Use an explicit, documented rule and distinguish forming from confirmed state; do not invent confidence or prediction labels |
| Alignment matrix | Compare top-left, top-right, lower corners, and supporting-label alignment | Test table collisions, long values, and native scales; fixed anchors are not a free-position panel system |
| Small range-position gauge | Make 0–100% location visible without another large number | Preserve the same formula and `N/A` handling, label its endpoints, and retain readable text without relying only on color |
| One headline with optional context rows | Let instrument identity, a metric, and Strat context share hierarchy | Keep secondary rows genuinely optional and clear stale rows when modes change |

For any Strat extension, start with [bar types](../docs/concepts/bar-types.md) and
[signals](../docs/concepts/signals.md). For code changes, apply the repository's
[repaint](../docs/engineering/repaint-prevention.md) and
[HTF correctness](../docs/engineering/htf-correctness.md) review gates before treating a
candidate as a tested feature.
