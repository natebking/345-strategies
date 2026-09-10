# Publishing packet: Automotive Display Studio

This is the publication packet for `display_studio.pine`. It deliberately uses an original,
generic product name and a self-contained description. The Rivian reference research belongs
in `DESIGN_NOTES.md`, not in the TradingView title, source commentary, or public description.

The consolidated source is **not cleared for public release yet**. It was assembled and
statically reviewed on 2026-09-10, but this pass did not have access to an authenticated
TradingView Pine runtime. Complete the release gate below in a private draft first.

## Publication settings

- Title: **Automotive Display Studio**
- Visibility: **Open-source**
- First publication: **Private draft**
- Intended public version: create a new public publication only after the private draft passes
- Suggested custom tags: `display`, `dashboard`, `range`, `candlestick`, `typography`

Privacy and visibility cannot be changed after publication. A public script has a short edit
window before it becomes final, so the private draft is a real release gate rather than an
optional rehearsal.

## Ready-to-paste description

The text inside the following block is self-contained and contains no outside links or brand
references.

```text
Automotive Display Studio is an original display-first indicator for traders who want a calm, instrument-cluster-style hierarchy instead of another signal overlay. It combines a large primary readout, compact monospaced context, restrained accents, and optional chart theming in one configurable Pine v6 script.

[b]What it displays[/b]

[list]
[*]Price: the latest chart close, with this bar's absolute and percentage open-to-close movement.
[*]Range Position: the close's position inside the current bar, calculated as 100 * (close - low) / (high - low) and bounded to 0-100%.
[*]Relative Range: the current high-low range divided by the average high-low range of prior completed bars. The current bar is excluded from the configurable 2-500 bar average.
[*]Instrument: the ticker as the primary readout, with the latest price, currency when available, and this-bar percentage as context.
[/list]

[b]How it is composed[/b]

[list]
[*]Classic Card: a compact top-left label stack with a large headline and short accent rule.
[*]Horizon Header: a distributed, full-width header with identity left, the headline centered, and context right.
[*]Inset Panel: a compact reversed panel with an accent edge.
[*]Bottom Rail: a wide three-part readout anchored to the bottom of the main chart.
[/list]

Readout and Layout are independent inputs, producing sixteen available combinations without maintaining separate scripts. The default is Price in Classic Card to preserve the preferred baseline from the preceding design study.

[b]Themes and chart treatment[/b]

Ink, Field, Charge, and Night themes coordinate the table, accents, optional canvas, and optional candle layer. Ink uses canvas-colored up bodies with dark borders and wicks for a hollow-bodied appearance. Field uses muted green and red. Charge uses bright green with dark edges and slate down candles. Night uses pale blue-green and gold on deep teal. The Accent input can override the theme accent with blue, gold, or bright green.

The themed candles are a second OHLC candle layer drawn above the native series. Turn them off when the native chart or another script should own candle rendering. The canvas control is independent and can remain behind native candles. Turn it off when native chart settings should own the background as well. Matching the native chart canvas and disabling grid lines produces the most continuous edge-to-edge treatment.

[b]Behavior and limitations[/b]

All values come from the selected chart's own OHLC. THIS BAR always means open-to-close movement on the current chart bar; it is not previous-close or daily performance unless those definitions happen to coincide. A forming bar can change with each available update, and market data may be delayed.

Relative Range compares a possibly forming current range with completed prior bars. It is high-low range, not true range, ATR, a volatility forecast, or a signal. Range Position is not a probability or a signal. Zero denominators and unavailable history display N/A.

The table reports the latest chart bar and does not follow the crosshair. Synthetic chart types supply synthetic OHLC. Pine tables cannot measure the viewport, automatically scale typography, reserve chart margin, or avoid other drawings. Use a smaller 36pt or 48pt headline and adjust native top or bottom margins when a long symbol, large price, or narrow chart needs more room. Bottom Rail is an overlay; it does not create a separate pane.

[b]Originality[/b]

This script's purpose is a unified information-and-composition system, not a bundle of unrelated indicators. Its independent Readout and Layout controls let the same current-bar context move through four deliberate visual hierarchies, while the theme controls coordinate typography, tables, canvas, and candles. It contains no trade signals, alerts, orders, external symbol requests, or performance claims.
```

## Publication chart

Use one clean chart with only the native price series and Display Studio:

1. Open the current `display_studio.pine` source, compile it, save it, and add a **fresh** instance.
2. Reset the instance to its defaults: Price, Classic Card, Ink, 56pt, theme accent, opaque
   card, canvas on, candles on.
3. Use ordinary Candles on a liquid symbol. Do not use a synthetic chart for the publication.
4. Keep the symbol and timeframe visible in the chart status line and keep **Display Studio**
   visible in the script status line.
5. Remove unrelated indicators, drawings, images, account information, and private material.
6. Keep the price series and Display Studio output visible. A light native canvas matching
   `#F6F6F6`, no grids, and adequate top margin best demonstrate the default.

The existing clean gallery images are design evidence, not publication charts: their hidden
native titles conflict with the public requirement to show symbol, timeframe, and script name.

## Release gate

Record the actual result in `DESIGN_NOTES.md`; do not convert planned checks into claims.

- [ ] Pine v6 compiler reports no errors or warnings for the exact packaged source.
- [ ] A fresh default instance renders after source save and layout reload.
- [ ] Price matches the latest close at the symbol's minimum tick.
- [ ] `NONE` and blank currency values are omitted.
- [ ] All four Readouts work in Classic Card on SPX 1D.
- [ ] All four Layouts show the same Price payload on SPX 1D.
- [ ] Range Position handles a zero-range bar as `N/A` and stays within 0-100% otherwise.
- [ ] Relative Range shows `N/A` for insufficient history or a zero prior average.
- [ ] Relative Range lookbacks 2, 20, and 500 load without a stale or shifted table.
- [ ] Instrument mode is checked on BTCUSDT 1D and on a long ticker/description case.
- [ ] Price precision is checked on an FX symbol, a crypto symbol, and a large-value index.
- [ ] Interval labels are checked on 1m, 60m, 1D, 1W, and 1M.
- [ ] Ink, Field, Charge, and Night each have legible table and candle contrast.
- [ ] Turning themed candles off reveals the unchanged native series.
- [ ] Turning canvas off removes only the scripted background.
- [ ] 56pt is inspected around a 1464 × 681 desktop viewport.
- [ ] 36pt is inspected around a 722 × 677 compact desktop viewport.
- [ ] Horizon Header and Inset Panel do not clip the tested values.
- [ ] Bottom Rail is checked with sufficient bottom margin and documented as an overlay.
- [ ] Forming-bar updates and a new-bar transition are checked during an open market.
- [ ] Save, layout save, and reload preserve the selected inputs.
- [ ] The publication chart shows symbol, timeframe, and script name in its status lines.
- [ ] The private draft title, description, default screenshot, source, and settings are reviewed
      before creating a separate public publication.

Do not attempt every possible Cartesian combination. The pairwise matrix above covers the
meaningful formula, geometry, precision, theme, and viewport risks.

## Platform references

- [Publishing scripts](https://www.tradingview.com/pine-script-docs/writing/publishing/)
- [Script Publishing Rules](https://www.tradingview.com/support/solutions/43000590599-script-publishing-rules/)
- [Visual placement and `overlay`](https://www.tradingview.com/pine-script-docs/visuals/overview/)
- [Tables](https://www.tradingview.com/pine-script-docs/visuals/tables/)
