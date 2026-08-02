# TradingView Listing Kit — TheStrat Suite (open-source publication)

Everything to paste into the Publish window. **The description is ONE-SHOT: on a public script, title/description/tags are editable for only 15 minutes after publishing, then frozen forever** (per the Pine publishing docs; after that, fixes require moderators). Review before publishing, reread within the 15-minute window, and make sure the GitHub repo is public first so the signature link resolves.

## Settings

- **Privacy:** Public · **Visibility:** Open
- **Title:** `TheStrat Suite [Open Source] — Entries, Targets, and Stop Loss`
  (62 chars — the publish field caps at ~63–64, measured 2026-07-30. Nate's phrasing: the complete trade lifecycle in natural trader English, avoids the "signals" spam cluster. `[Open Source]` sits right after the brand so it survives truncation and disambiguates from the legacy listing, whose title can't change. Multi-timeframe discovery is covered by the category, description line 1, and the multitimeframe tag; FTFC stays in the description.)
- **Categories:** Candlestick analysis · Multi-timeframe · Pivot Points and Levels (matches the legacy listing's proven category set; S&R is the alternative if a bigger browse audience matters more than continuity)
- **Tags:** `thestrat`, `strat`, `stoploss`, `multitimeframe`, `priceaction`, `insidebar`, `ftfc`, `candlestickpatterns`, `alertsignals` (all genuinely relevant — irrelevant tags are a moderation risk)

## Description (paste below, review voice first)

*Rebased 2026-08-02 on the legacy listing's moderation-proven description (Nate's direction) — original copy kept verbatim wherever the feature is unchanged, with new sections for what shipped since it was written: stop losses, timeframe presets, preview mode, universal labels, detailed alerts, bar coloring, the repaint contract, and the open-source close.*

---

TheStrat Suite automates the detection, visualization, and alerting of price action setups based on TheStrat methodology (developed by Rob Smith) across up to six configurable timeframes simultaneously.

The guiding principle: show only the most valuable information. Rather than cluttering charts with every possible level and signal, the indicator uses logic based on user settings to determine what's relevant and worth displaying at any given moment.

[b]WHAT IT DOES[/b]

The indicator identifies candle combinations (combos), actionable signals (inside bars, hammers, shooters), Failed 2s (range reclaims), and calculates magnitude and exhaustion targets — then draws entries, targets, stop losses, and take action windows directly on your chart. A real-time data table displays combo status, bar types, and Full Timeframe Continuity (FTFC) across all enabled timeframes. Candles themselves can be colored by Strat classification or by FTFC. Alerts can be filtered by timeframe continuity, signal type, specific timeframes, or Domino setups.

[b]HOW IT WORKS[/b]

[b]Multi-Timeframe Data Architecture[/b]
The indicator requests OHLC data from up to six user-configured timeframes in a single pass, then processes each timeframe's candle relationships independently. This allows the 5-minute, 60-minute, daily, and weekly structure to coexist on one chart without switching views.

[b]Candle Classification Logic[/b]
Each closed candle is classified by comparing its high and low to the prior candle's range. A candle entirely within the prior range is type 1 (inside). A candle that exceeds one side is type 2 (directional). A candle that exceeds both sides is type 3 (outside). Directional bias (u/d) is determined by comparing close to open. A Failed 2 (also known as a Range Reclaim, 2d Green, or 2u Red) occurs when a directional candle breaks one side of an inside bar but fails to continue.

[b]Hammer and Shooter Detection[/b]
The indicator offers three detection methods. Classic requires the candle to breach the prior candle's high or low but close back inside the prior range. Pin Bar adds a wick-to-body ratio requirement, filtering for candles where the rejecting wick is significantly longer than the body. Broad relaxes the close requirement, allowing the close to be near (not strictly inside) the prior range. Users select which method matches their trading style.

[b]Failed 2 / Range Reclaim Detection[/b]
A Failed 2 occurs when price breaks one side of an inside bar (type 1) but reverses through the opposite side. The indicator provides four detection methods. Open flags the setup when the reversal candle opens beyond the broken level. Reclaim flags when price closes back through the opposite side of the inside bar's range. Both requires both conditions (open beyond AND close reclaim). Either flags when either condition is met. This configurability lets traders match detection to their preferred confirmation style.

[b]Stop Loss Levels[/b]
When a signal fires with stops enabled, the indicator places a stop loss level on the opposite side of the trigger and locks it for the duration of the signal. The stop reference is selectable — the current candle for tighter risk, or C1 for wider invalidation — and an optional Break Even mode moves the stop to entry once magnitude or exhaustion is hit. A Smallest Timeframe Only mode draws just the tightest active stop when several timeframes are in force. Stop prices can be appended to alert messages.

[b]Level Hierarchy and Consolidation[/b]
When multiple timeframes produce levels at similar prices, the indicator intelligently consolidates them into combined labels rather than hiding important information. Higher timeframes take display priority over lower timeframes — a weekly level takes precedence over a daily level at the same price — but both are represented in the consolidated label. Actionable signals (inside bars, hammers, shooters with defined triggers) take priority over static reference levels. This prevents chart clutter while preserving all relevant information in a readable format.

[b]Intelligent Label Adaptation[/b]
Labels dynamically update as market structure changes. When a magnitude target from one timeframe coincides with a trigger level from another, the label consolidates to reflect both roles (e.g., "W MAG + D Trigger"). When levels are hit, invalidated, or superseded, labels update color and text to reflect current status rather than disappearing — preserving context for the trader.

[b]Full Timeframe Continuity (FTFC) Filtering[/b]
FTFC status is calculated by evaluating directional bias across all enabled timeframes. When all timeframes show bullish bias (closing up relative to open), FTFC is bullish. When all show bearish bias, FTFC is bearish. Mixed bias means no continuity. Users can filter signals to only appear when FTFC aligns with the signal direction, reducing noise during consolidation.

[b]Take Action Windows[/b]
When a signal forms on a higher timeframe, the indicator highlights the period during which that timeframe's candle remains open. This visual window reminds traders when a setup is "in force," providing a frame of reference for seeking entries on smaller timeframes.

[b]Domino Detection[/b]
A Domino setup occurs when a signal on one timeframe can trigger another signal on an adjacent timeframe. The indicator detects and alerts on these conditions.

[b]Bar Coloring[/b]
New in v3. Chart candles can be painted by their Strat classification or by the current Full Timeframe Continuity state, with optional highlighting when a bar flips to a Failing 2. One mode is active at a time, and coloring is off by default.

[b]Preview Mode[/b]
When the market is closed, the indicator shifts to the next period's levels so setups can be planned before the open. The Auto default detects the instrument type and activates during off-hours — weekends for futures, pre/post-market for equities, even holidays — and turns itself off when trading resumes.

[b]IMPLEMENTATION DETAILS[/b]

This implementation addresses several practical challenges traders face.
[list]
[*][b]Multi-timeframe consolidation:[/b] Rather than constantly switching chart timeframes or mentally tracking multiple structures, all analysis exists in one view with intelligent deduplication when levels overlap.

[*][b]Configurable detection methods:[/b] Hammer/shooter and Failed 2 detection aren't one-size-fits-all. The four Failed 2 methods and three hammer/shooter definitions let traders match the indicator to their specific confirmation requirements rather than accepting a single rigid definition.

[*][b]Dynamic level management:[/b] Levels don't just appear and disappear — they adapt. A target becoming a trigger, a level being hit, or a setup invalidating all produce specific visual feedback rather than simply removing information. This preserves market context as price develops.

[*][b]Alert filtering depth:[/b] Alerts can be filtered by FTFC alignment, signal type, specific timeframes, or Domino conditions — and the consolidated alert can append trigger, magnitude, exhaustion, and stop prices plus the FTFC state to each message — allowing traders to specify exactly which conditions warrant notification without building complex alert logic manually.

[*][b]Performance optimization:[/b] Multi-timeframe analysis can be computationally expensive. This implementation consolidates data requests and limits historical depth on intensive calculations to maintain fast load times without sacrificing real-time functionality.
[/list]

[b]HOW TO USE IT[/b]

[b]Setup[/b]
Pick a timeframe preset — TheStrat Classic, Scalp, Day Trade, Futures/Crypto, Swing Trade, or Investing — or set Custom to configure all six timeframe slots manually. Enable or disable specific bar combinations you want to see (e.g., 2-1, 3-2, etc.). Configure your preferred hammer/shooter and Failed 2 detection methods. Toggle FTFC filtering on/off based on your strategy.

[b]Reading the Display[/b]
Solid lines represent reference levels (prior high/low). Dashed lines represent actionable triggers. Stop loss levels sit on the opposite side of the trigger. Color indicates direction (configurable) and status (hit, failed, active). Labels show timeframe, level type, and price — in Strat notation (2d-1-2u HAM) or a plain-language Universal style (REVERSAL, CONTINUATION, INSIDE, OUTSIDE, EXPANSION, FAILING). The data table shows current combo, bar type, and FTFC status per timeframe, in a Full layout or a Compact color-coded row.

[b]Alerts[/b]
Set your chart timeframe equal to or lower than your lowest configured indicator timeframe, and set the alert interval accordingly. One consolidated alert covers every enabled timeframe with per-timeframe filtering, or use the individual alert conditions. Use alert filters to specify which conditions trigger notifications.

[b]DOES IT REPAINT?[/b]

No. Completed-bar signals are built from confirmed higher-timeframe data and do not change on reload. The forming candle updates in real time by design — that is the live trigger you are watching — and the engineering rules that enforce this are documented in the repository.

[b]DEFINITIONS[/b]
[list]
[*][b]Combo:[/b] Two or more numbers representing the relationship between consecutive candles (e.g., 2-1, 3-2, 2-1-2). Each number indicates the candle type in sequence.

[*][b]Candle Types:[/b] 1 = Inside, 2 = Directional, 3 = Outside.

[*][b]Directional Bias:[/b] u = price above open, d = price below open.

[*][b]C1/C2:[/b] C1 is the most recent closed candle, C2 is two bars back.

[*][b]Magnitude:[/b] The measured move target, typically the C2 high or low.

[*][b]Exhaustion:[/b] Extended targets beyond magnitude, indicating potential reversal zones.

[*][b]FTFC:[/b] Full Timeframe Continuity — all timeframes aligned in the same direction.

[*][b]Domino:[/b] A setup where one signal triggering can cascade into triggering adjacent timeframe signals.
[/list]

[b]KNOWN LIMITATIONS[/b]
[list]
[*]TradingView cannot request data from timeframes lower than your chart. Set chart timeframe accordingly.
[*]Bar replay performance is unreliable with small timeframes and can produce runtime errors with certain low-timeframe combinations (TradingView limitation).
[*]Exhaustion calculations are limited to recent bars for performance.
[*]Label overlap at similar price levels is a TradingView rendering limitation.
[/list]

[b]OPEN SOURCE[/b]

The complete source is published under the Mozilla Public License 2.0, together with the engineering documentation (the no-repaint contract, the multi-timeframe correctness rules), a full changelog, and a settings reference. The repository and setup-guide links are in my signature and on my profile. This publication open-sources my earlier invite-only listing of the same name; that listing stays up for its existing users, and updates continue here.

[i]Trading involves risk. This is a charting tool, not financial advice. Past performance does not guarantee future results.[/i]

---

## Links: what TradingView allows (verified vs House Rules, 2026-07-30)

- **External links/references are BANNED in descriptions, release notes, comments, and code** — the promotion rule names "links or references to any website" across "all types of publications and updates … script release notes." No open-source or GitHub carve-out exists. This is why the description above contains no URLs.
- **The Signature field (Premium+) is the sanctioned home**: it renders under every script and idea. BEFORE publishing, set the signature to carry both links, e.g. `TheStratSuite.com · github.com/natebking/345-strategies`, and put them on the profile About page too.
- **TV-internal references are safe by name**: "search 'TheStrat Suite' (open-source) on my profile @SpinTrades." Use this form in release notes instead of URLs.
- Exception that stays: the invite-only **Author's Instructions** field is designed for a vendor access link (the current "Get Access: TheStratSuite.com" has lived there unmoderated) — fine to keep using it for the legacy signpost.

## Release-notes template for the legacy listing's final update (link-free)

> TheStrat Suite is now free and open source. This invite-only listing is legacy — existing users keep access and nothing changes on your charts. The current version is published as an open-source script: find "TheStrat Suite" on my profile (@SpinTrades), marked with the OPEN-SOURCE badge. Repository and documentation links are in my signature.

## Legacy listing signpost (old invite-only publication)

Legacy listing URL: https://www.tradingview.com/script/NNDIyA45-TheStrat-Suite-Multi-Timeframe-Price-Action-Signals-w-Alerts/ ("TheStrat Suite: Multi-Timeframe Price Action Signals w/ Alerts"). Its original benefit copy is preserved in the local working folder (`reference-original-tv-listing.md`) as source material.

Its description and title are locked. Available levers, in order of reliability:

1. **Final Update** — push v3.0.0 as an Update with the link-free release-notes template above (links/references are banned in release notes; TV-internal pointers by name only). Do this IMMEDIATELY after the open listing goes live: on paper, the old closed listing violates "closed-source scripts that reproduce what open-source scripts already do" once the open version exists — no retroactive enforcement is documented, but a hidden script can never be updated, so the signpost must land first. Release notes freeze the moment they post; final wording only.
2. **Author comment** on the listing saying the same (survives even if nothing else is editable).
3. **Author's instructions** — edit only if the UI still allows it post-publish: "This invite-only listing is legacy; existing users keep access. Current version: 'TheStrat Suite' (open-source badge) by SpinTrades."

## After publishing

- Boosts/comments drive TV surfacing: announce to the trading group and X, answer every early comment, keep updates flowing.
- Tell Claude to retitle CHANGELOG `[Unreleased]` → dated `[3.0.0]`.
- Link the TV listing from thestratsuite.com and the repo README (bidirectional links help the listing's Google ranking).
