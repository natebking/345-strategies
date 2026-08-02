# TradingView Listing Kit — TheStrat Suite (open-source publication)

Everything to paste into the Publish window. **The description is ONE-SHOT: on a public script, title/description/tags are editable for only 15 minutes after publishing, then frozen forever** (per the Pine publishing docs; after that, fixes require moderators). Review before publishing, reread within the 15-minute window, and make sure the GitHub repo is public first so the signature link resolves.

## Settings

- **Privacy:** Public · **Visibility:** Open
- **Title:** `TheStrat Suite [Open Source] — Entries, Targets, and Stop Loss`
  (62 chars — the publish field caps at ~63–64, measured 2026-07-30. Nate's phrasing: the complete trade lifecycle in natural trader English, avoids the "signals" spam cluster. `[Open Source]` sits right after the brand so it survives truncation and disambiguates from the legacy listing, whose title can't change. Multi-timeframe discovery is covered by the category, description line 1, and the multitimeframe tag; FTFC stays in the description.)
- **Categories:** Candlestick analysis · Multi-timeframe · Support and Resistance (or keep Pivot Points and Levels — both defensible; S&R has the larger browse audience)
- **Tags:** `thestrat`, `strat`, `stoploss`, `multitimeframe`, `priceaction`, `insidebar`, `ftfc`, `candlestickpatterns`, `alertsignals` (all genuinely relevant — irrelevant tags are a moderation risk)

## Description (paste below, review voice first)

---

TheStrat Suite is an open-source multi-timeframe indicator for TheStrat, Rob Smith's price action methodology. It classifies every candle as inside (1), directional (2u/2d), or outside (3), detects the core Strat setups across six configurable timeframes, and draws the levels that matter: entry triggers, magnitude targets, exhaustion levels, and stop loss levels — with Full Timeframe Continuity (FTFC) on every signal.

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

Levels don't just appear and disappear — they adapt. A target becoming a trigger, a level being hit, or a setup invalidating all produce specific visual feedback.

HOW TO USE IT

1. Add it to your chart and pick a timeframe preset: TheStrat Classic, Scalp, Day Trade, Futures/Crypto, Swing Trade, or Investing.
2. Read the table: yellow/orange rows are inside setups forming; green/red means a signal is in force.
3. Set alerts: one consolidated alert covers every timeframe, or use the per-timeframe alert conditions.

DOES IT REPAINT?

No. Completed-bar signals are built from confirmed higher-timeframe data and do not change on reload. The forming candle updates in real time by design — that is the live trigger you are watching — and the engineering rules that enforce this are documented in the repository.

WHAT MAKES IT DIFFERENT

Most Strat indicators mark bar numbers. This one consolidates six timeframes into a single decision view: signal detection with targets and stop losses attached, FTFC and Lead Signal filtering, preview mode for planning before the open, and a documented no-repaint contract. The guiding principle is to show only the most valuable information — the indicator decides what is relevant and worth displaying at any given moment rather than cluttering the chart with every possible level. It is the culmination of my price action work on TradingView.

OPEN SOURCE

The complete source is published under the Mozilla Public License 2.0, together with the engineering documentation (the no-repaint contract, the multi-timeframe correctness rules), a full changelog, and a settings reference. The repository and setup-guide links are in my signature and on my profile. This publication open-sources my earlier invite-only listing of the same name; that listing stays up for its existing users, and updates continue here.

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
