# TradingView Listing Kit — TheStrat Suite (open-source publication)

Everything to paste into the Publish window. **The description is ONE-SHOT: TradingView does not allow editing it after publication** (typo fixes require moderators). Review before publishing, and make sure the GitHub repo is public first so the link resolves.

## Settings

- **Privacy:** Public · **Visibility:** Open
- **Title:** `TheStrat Suite [Open Source] — Multi-Timeframe Signals, Targets & Stop Loss`
  (76 chars; limit is ~128, keep under 100. `[Open Source]` sits right after the brand so it survives truncation and disambiguates from the legacy listing, whose title can't change. "Stop Loss" over "FTFC" in the title: bigger query, real feature; FTFC stays in the description for the niche searchers. Fallback if a field ever caps shorter: swap "Multi-Timeframe" → "MTF".)
- **Categories:** Candlestick analysis · Multi-timeframe · Support and Resistance (or keep Pivot Points and Levels — both defensible; S&R has the larger browse audience)
- **Tags:** `thestrat`, `strat`, `stoploss`, `multitimeframe`, `priceaction`, `insidebar`, `ftfc`, `candlestickpatterns`, `alertsignals` (all genuinely relevant — irrelevant tags are a moderation risk)

## Description (paste below, review voice first)

---

TheStrat Suite is a free, open-source multi-timeframe indicator for TheStrat, Rob Smith's price action methodology. It classifies every candle as inside (1), directional (2u/2d), or outside (3), detects the core Strat setups across six configurable timeframes, and draws the levels that matter: entry triggers, magnitude targets, exhaustion levels, and stop loss levels — with Full Timeframe Continuity (FTFC) on every signal.

WHAT IT DETECTS

- Inside reversals and continuations (2-1-2 patterns)
- 2-2 reversals and continuations
- Failing 2s / Range Reclaims (F2u, F2d) with four selectable detection methods
- 3-2 expansions and outside bars
- Hammers and shooters (three selectable definitions)
- Domino setups — consecutive inside bars stacked across timeframes
- Full Timeframe Continuity across all monitored timeframes

WHAT IT DRAWS

- Trigger levels at the prior candle's high and low, colored by state (potential, in force, failed)
- Magnitude and exhaustion targets, with Take Action Windows between trigger and target
- Stop loss levels with an optional break-even move at magnitude or exhaustion
- A live data table of all six timeframes, in Strat notation or a plain-language Universal mode
- New in v3: bar coloring by Strat classification or by FTFC

HOW TO USE IT

1. Add it to your chart and pick a timeframe preset: TheStrat Classic, Scalp, Day Trade, Futures/Crypto, Swing Trade, or Investing.
2. Read the table: yellow/orange rows are inside setups forming; green/red means a signal is in force.
3. Set alerts: one consolidated alert covers every timeframe, or use the per-timeframe alert conditions.

DOES IT REPAINT?

No. Completed-bar signals are built from confirmed higher-timeframe data and do not change on reload. The forming candle updates in real time by design — that is the live trigger you are watching — and the engineering rules that enforce this are documented in the repository.

WHAT MAKES IT DIFFERENT

Most Strat indicators mark bar numbers. This one consolidates six timeframes into a single decision view: signal detection with targets and stops attached, FTFC and Lead Signal filtering, preview mode for planning before the open, and a documented no-repaint contract. It is the culmination of my price action work on TradingView.

OPEN SOURCE

Full source, engineering docs (no-repaint rules, multi-timeframe correctness), changelog, and settings reference: github.com/natebking/345-strategies — licensed MPL-2.0. Guides at TheStratSuite.com. This publication replaces my earlier invite-only listing of the same name; the Suite is now free for everyone.

---

## Legacy listing signpost (old invite-only publication)

Its description and title are locked. Available levers, in order of reliability:

1. **Final Update** — release notes: "Final update to this listing. TheStrat Suite is now free and open source → [link to new listing]."
2. **Author comment** on the listing saying the same (survives even if nothing else is editable).
3. **Author's instructions** — edit only if the UI still allows it post-publish: "This invite-only listing is legacy; existing users keep access. Current version: 'TheStrat Suite' (open-source badge) by SpinTrades."

## After publishing

- Boosts/comments drive TV surfacing: announce to the trading group and X, answer every early comment, keep updates flowing.
- Tell Claude to retitle CHANGELOG `[Unreleased]` → dated `[3.0.0]`.
- Link the TV listing from thestratsuite.com and the repo README (bidirectional links help the listing's Google ranking).
