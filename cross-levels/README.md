# Cross Levels (ES ↔ SPY/SPX)

A Pine v6 overlay that translates price levels between ES futures and the cash market and
draws them on whichever chart is open.

- On an ES chart: the cash market's killzone session highs and lows, opening prices, and
  prior day/week/month levels, converted to ES prices, plus SPY overnight gap boxes.
- On a SPY or SPX chart: ES levels converted to cash prices. This direction is the reason
  the indicator exists — the overnight killzones (Asia, London) happen while the cash chart
  has no bars at all.

The chart symbol is detected automatically (ES/MES vs SPY/SPX), with a manual override.

## Conversion

Everything runs through a basis measured while both markets are open: `ES − SPX` for the
index, `ES − SPY×10` for the ETF. The ×10 scaling means one SPY point is always ten ES
points, which is how the spread gets quoted anyway. The basis updates on every chart bar
where both symbols print, and freezes at its last value overnight.

Two conversion modes, because there are two honest answers to "where is that level on this
chart." **Projection**, the default, converts with the current basis: the line marks where
this chart will trade when the other symbol returns to its level, which is the liquidity
read. It converts through a held copy of the basis that only re-anchors past a threshold
(default one ES point), since SPY and ES closes are not synchronized prints and unheld
lines re-price on every bar of feed noise. **Historical** pins each level to the basis
measured when its extreme printed, so lines sit on the other symbol's actual prints and
never move — at the cost of no longer marking where a retest will land. The difference
between the modes on any level is exactly how far the basis has drifted since it formed.

## What draws

- **Killzone highs and lows** of the other symbol, most recent completed session, shown
  until price trades through them — a spent level drops off the chart by default. The
  sessions, names, and colors default to the ones in ICT Killzones & Pivots [TFO] by
  tradeforopp, so the two scripts can sit on the same chart and agree. On an ES chart with
  a cash source, only the New York sessions produce levels — the cash market has no
  overnight bars, and an empty Asia box would be an invention.
- **Opening prices**: the futures daily open (18:00), midday, and the cash close by
  default, each with its own color and label. The daily open is the one open a cash chart
  cannot see; a 09:30 slot would duplicate the chart's own open, so it is not a default.
- **Prior day high, low, and midpoint** (week and month available, off by default). SPY's
  prior day is the regular session only, which is exactly why it lands somewhere different
  from the ES chart's own prior day.
- **SPY gap boxes** on the ES chart: prior 16:00 close to today's 09:30 open, converted,
  extended right until price fills the gap. Filled gaps drop off by default, and gaps
  under 0.10 SPY are ignored — SPY opens a few cents off the prior close almost every day.

A small corner table reports the direction, the current basis, and whether it is live or
frozen.

## Limitations

- The basis freezes when the cash market is closed. A contract roll on a continuous ES
  symbol shifts the basis, and the frozen value is stale until the first regular-session
  overlap bar after the roll.
- Nothing draws until the loaded chart history contains at least one bar where both markets
  were open.
- A partially observed session or period is never served. If the loaded history does not
  cover a full prior day, the prior-day lines simply stay off rather than showing a wrong
  value.

## Requirements

Imports the [PineDraw](../pine-draw/) library (`SpinTrades/PineDraw/1`).

## Status

v0.1.0. Not published on TradingView.

## License

Mozilla Public License 2.0.
