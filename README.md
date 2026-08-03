# 345 Strategies

Open-source price-action trading tools for TradingView, built and maintained by 345 Strategies. The flagship is **TheStrat Suite**; sibling tools and the shared definitions live alongside it.

**What counts as "TheStrat Suite":** whatever ships inside the one TheStrat Suite indicator script on TradingView. Tools that ship as their own scripts are siblings under this roof with their own names - if one later merges into the indicator, it joins the Suite. Distribution decides, not methodology.

## TheStrat Suite - flagship indicator

Multi-timeframe price action indicator (Pine Script v6), implementing Rob Smith's TheStrat methodology. Six configurable timeframes on one chart: bar classification, signal detection with magnitude and exhaustion targets, Full Timeframe Continuity, stop levels, Domino detection, consolidated alerts, and a live multi-timeframe data table.

**Get it on TradingView:** [TheStrat Suite [Open Source] - Entries, Targets, and Stop Loss](https://www.tradingview.com/script/dnJOzGmk-TheStrat-Suite-Open-Source-Entries-Targets-and-Stop-Loss/)

Setup guides and background: [thestratsuite.com](https://thestratsuite.com)

### Quick start

1. Add [the indicator](https://www.tradingview.com/script/dnJOzGmk-TheStrat-Suite-Open-Source-Entries-Targets-and-Stop-Loss/) to your chart on TradingView - or copy `pine/TheStratSuite_v3.0.0.pine` into the Pine editor.
2. Pick a Timeframe Preset (TheStrat Classic, Scalp, Day Trade, Futures/Crypto, Swing Trade, Investing) - or set Custom and configure the six slots yourself.
3. Read `docs/concepts/bar-types.md` and `docs/concepts/signals.md` to learn what you're looking at.

## Repository contents

### `pine/` - indicator source (newest first)

- **`TheStratSuite_v3.0.0.pine`** - current build, published on TradingView as the open-source
  listing. BARCOLOR-1 (bar coloring by Strat classification or FTFC) and STOP-SMALLEST-1
  (Smallest Timeframe Only stop display).
- `TheStratSuite_v2.2.7-split.pine` - NOTATION-1: canonical uppercase F2u/F2d
  (lowercase live-'f' retired; liveness = slot position / '*' prefix / words).
- `TheStratSuite_v2.2.6-split.pine` - RECON-KEY-1 (+12h key normalization for daily
  reconstruction) and TFCOLOR-1 (in-force column no longer highlights inside bars).
- `TheStratSuite_v2.2.4-split.pine` - GLUE milestone: HTF-straddle fix line plus GLUE-1 / GLUE-2b
  (CME holiday-glued-bar handling).
- `TheStratSuite_v2.2.2-split.pine` - HTF-straddle T1 period shift + T3 daily reconstruction.
- `TheStratSuite_v2.2.0.pine` - pre-split baseline.
- `TheStratSuite_v180_June16_2026.pine` - June 2026 pre-audit original.

### `pine/tools/` - sibling tools

Separate scripts, each with its own name and its own TradingView listing. They share
the methodology and the repository, not the Suite's script.

- **`PA_Invalidation_Stop.pine`** - Price Action Invalidation Stop Loss. A stop placed where
  the trade would be wrong (the prior completed 30m/60m level) rather than at a fixed
  distance, ratcheting one way and tightening when structure confirms. Six selectable
  versions. See `docs/tools/invalidation-stop.md`.
- **`PowerBar.pine`** - marks candles that are nearly all body, measured against a
  session-aware, time-of-day-adjusted expected range. A context marker, not an entry
  signal. See `docs/tools/powerbar.md`.

### `core/` - the definitions, as Python

`strat_core` is the same vocabulary the Pine implements, in a dependency-free Python
package: bar-state classification, combos, timeframe continuity, hammers and shooters,
the PowerBar shape. Standard library only - no I/O, no dataframes, no plotting.

```python
from strat_core import Candle, classify, combo, timeframe_continuity

classify(prev, curr).token     # 'F2u'
combo([c2_state, c1_state, cc_state])   # '2d-1-2u'
```

Start at `core/README.md`. Tests: `cd core && python3 -m unittest discover -s tests`.

### `docs/`

Start at `docs/README.md` (the index). Trader-facing docs live in `docs/concepts/`, engineering docs in `docs/engineering/`. Highlights:

- `concepts/bar-types.md` - bar structures, notation rules, Failing 2s, hammers/shooters.
- `concepts/signals.md` - the seven signal types, defaults, filters, in-force mechanics.
- `engineering/repaint-prevention.md` - the no-repaint contract: 8 rules + contributor checklist.
- `engineering/htf-correctness.md` - multi-timeframe correctness: straddle/glue handling, +12h
  normalization, daily reconstruction, preview mode.
- `Settings_Reference.md` - full settings reference, every input in panel order.
- `DESIGN_CONSTRAINTS.md` - intentional design decisions reviewers should not flag as bugs.
- `v2.2.3_holiday_glue_fix.md` - postmortem of the CME holiday-glue incident.
- `tools/` - one page per sibling tool: `invalidation-stop.md`, `powerbar.md`.

Version history lives in the root `CHANGELOG.md` - one entry per released `.pine` snapshot, every fix cited by its `FIX` tag.

### `diagnostics/`

Not part of the shipped indicator. Throwaway probe scripts from the HTF-straddle
investigation, retained because they document how the straddle behavior was measured.

## Engineering ground rules

- **No-repaint is a hard, zero-tolerance requirement.** What you saw live is what a reload shows. The rules are documented, with case studies, in `docs/engineering/repaint-prevention.md`.
- Fix history is inline via `// FIX <id>` comments (P0/P1/P2, BTC, CSS, TAW, MOD, HTF-STRADDLE, GLUE, RECON-KEY, TFCOLOR, NOTATION). Every tag marks a solved bug and the rule that came out of it - grep for them.
- Contributions: start with `CONTRIBUTING.md` (required reading, `FIX`-tag conventions, manual verification workflow), and pass the contributor checklists at the end of the engineering docs before review.

## License

Mozilla Public License 2.0 - see `LICENSE`. Source files carry the standard MPL header.
