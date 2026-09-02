# Price Display

A standalone Pine Script v6 overlay with a large latest-price readout, small monospaced labels, and a restrained color palette. It is independent of TheStrat Suite and requires no other scripts. This is an original visual homage, not an official Rivian product.

`price_display.pine` is the verified price-readout baseline. `instrument_display.pine` is a separate experimental script with Range Position, Relative Range, and Instrument headline modes. Neither has signals, alerts, orders, external data requests, or chart-recoloring calls. Neither is a TheStrat Suite feature.

The [design notes](DESIGN_NOTES.md) record the palette and typography trials, what was kept or rejected, the test record, limitations, and ideas that are not implemented. Ink & Paper was the preferred chart direction; the price baseline still defaults to Cloud & Field, while the experimental display defaults to Ink & Paper.

## Install

1. Open a chart in TradingView and create a new indicator in Pine Editor.
2. Replace the editor contents with `price_display.pine`, or use `instrument_display.pine` to try the experimental metrics.
3. Save the script, then select **Add to chart**.
4. Open the indicator's settings to choose its appearance. To reproduce the monochrome design, select **Ink & Paper** and apply the native chart settings below separately.

Use one display at a time. Both occupy the same top-left anchor and can cover each other if added together.

## Price Display inputs

| Input | Default | Options / behavior |
| --- | --- | --- |
| Palette | Cloud & Field | Cloud & Field, Ink & Paper, Charging Green, Night Expedition |
| Headline size (pt) | 56 | 36, 48, 56, or 64 typographic points; smaller sizes suit narrow charts or long prices |
| Transparent card | Off | Off matches the selected palette's canvas; on lets candles show behind the text |
| Show palette key | Off | Off shows a short decorative gold rule; on shows four suggested-color chips |
| Top inset (% of chart) | 3 | 0–15% of chart height |

The headline uses TradingView's native default font family in bold. Supporting labels use its native monospace family at 11pt. No custom font is loaded or distributed; these are not Rivian's proprietary fonts.

## Values and behavior

The fixed top-left table follows the latest available chart bar, not the crosshair:

- Headline: `close`, formatted to the symbol's minimum tick.
- Absolute change: `close - open`.
- Percentage change: `100 * (close - open) / abs(open)`. An unavailable or zero open produces `N/A` for the percentage.
- Supporting label: symbol, chart timeframe, and currency when available. Blank currency and `NONE` are omitted.

**THIS BAR** means the current bar's open-to-close change. It is not a previous-close return or a daily-change calculation unless that happens to coincide with the selected bar. On an unfinished bar, the displayed close can change with each available update. Market data may be delayed. Synthetic chart types supply synthetic values, so use ordinary Candles when actual bar OHLC values are intended.

## Ink & Paper chart setup

The indicator's Palette input styles only its table. It does not apply a native chart template, recolor candles, change scale fonts, or modify TradingView's surrounding interface.

For the monochrome design, use these native chart settings:

| Setting | Value |
| --- | --- |
| Chart type | Ordinary **Candles**, not **Hollow candles** |
| Color bars based on previous close | Off |
| Body, borders, and wick | All on |
| Up body | `#F6F6F6` |
| Down body | `#101512` |
| Up and down borders | `#101512` |
| Up and down wicks | `#101512` |
| Candle-color opacity | 100% for every body, border, and wick color |
| Canvas | Solid `#F6F6F6` |
| Horizontal and vertical grids | Off |
| Scale labels | Visible; native font, 14px, `#606060` |
| Axis lines | Hidden or fully transparent |
| Crosshair | `#1676CA` |
| Top / bottom margins | 20% / 15% |
| Right margin | 10 bars |

Set the indicator to **Ink & Paper**, 56pt, Transparent card off, Show palette key off, and Top inset 3%. Its headline is `#101512`, supporting text is `#606060`, and the short rule is `#FFAC03`. The gold rule is decoration, not an essential data encoding.

The background-colored up bodies create a hollow appearance while retaining ordinary open/close candle semantics. TradingView's separate Hollow candles type also considers the previous close for its color encoding and is not interchangeable.

For a quieter composition, collapse the indicator legend without hiding the indicator itself, reduce redundant status-line information, and close the watchlist and Pine Editor. Adjust chart zoom to keep candles readable; margins may need adjustment for a different symbol, timeframe, or viewport.

## Other palettes

These are suggested native chart colors to match each table theme. They must be applied manually.

| Palette | Solid canvas | Up body | Up border / wick | Down body / border / wick |
| --- | --- | --- | --- | --- |
| Cloud & Field | `#F6F6F6` | `#5F6559` | `#5F6559` | `#DE311E` |
| Charging Green | `#F2F2F2` | `#72DC57` | `#5F6559` | `#293846` |
| Night Expedition | `#02171C` | `#84ACB3` | `#84ACB3` | `#FFAC03` |

For Cloud & Field and Charging Green, use scale text `#606060` and crosshair `#1676CA`. For Night Expedition, use scale text `#B8C7CB` and crosshair `#84ACB3`. Keep Charging Green's dark borders and wicks: the bright fill alone has weak contrast on the light canvas.

`#5F6559` is sampled from the digital Rivian Green swatch in the [official Rivian Green story](https://rivian.com/stories/pantone-partner-rivian-green-color), not a canonical Pantone-to-sRGB specification. `#72DC57` is an image-derived approximation of the charging UI green on [Rivian's Technology page](https://rivian.com/technology), not a published color standard.

## Experimental Instrument Display

This is a separate standalone indicator titled **Instrument Display · Design Studies**.
All three modes have compiled, saved, rendered, and passed saved-layout reload checks on
BTCUSDT 1D. This remains a design study, not a signal. The exact coverage and untested cases
are in [DESIGN_NOTES.md](DESIGN_NOTES.md#test-record).

| Input | Default | Options / behavior |
| --- | --- | --- |
| Display mode | Range Position | Range Position, Relative Range, Instrument |
| Palette | Ink & Paper | Same four table palettes as Price Display |
| Headline size (pt) | 56 | 36, 48, 56, 64 |
| Top inset (% of chart) | 3 | 0–15% |
| Transparent card | Off | Use an opaque matching card for reliable contrast |
| Relative range lookback | 20 | 2–500 completed chart bars |
| Short instrument description | On | Instrument mode only; omit descriptions longer than 28 characters |

- **Range Position:** `100 * (close - low) / (high - low)`, bounded to 0–100%. Zero range
  or unavailable required data gives `N/A`. This is location inside the current chart bar,
  not a stochastic lookback, a session measure, or a probability.
- **Relative Range:** current `high - low` divided by `ta.sma(high - low, lookback)[1]`.
  The average excludes the current bar. A zero prior average or insufficient history gives
  `N/A`. A partially formed numerator is compared with completed bars; it is not
  time-of-day normalized, true range, ATR, or a forecast of expected volatility.
- **Instrument:** a large ticker with smaller latest price and current-bar percentage.
  The optional description is omitted when too long. As in Price Display, the percentage
  is relative to this bar's open, not a prior-close return.

These modes use chart OHLC only and show the selected chart timeframe. They make no
daily/session assumption. Forming values can change intrabar, data can be delayed, and
synthetic charts supply synthetic OHLC. Mode formulas, edge cases, and unimplemented
extensions are documented separately from verified behavior in the design notes.

## License

The Pine source carries the Mozilla Public License 2.0 notice used by this repository.
