# TheStrat Suite

Multi-timeframe price action indicator for TradingView (Pine Script v6), implementing Rob Smith's TheStrat methodology. Six configurable timeframes on one chart: bar classification, signal detection with magnitude and exhaustion targets, Full Timeframe Continuity, stop levels, Domino detection, consolidated alerts, and a live multi-timeframe data table.

Setup guides and background: [thestratsuite.com](https://thestratsuite.com)

## Quick start

1. Copy `pine/TheStratSuite_v2.2.7-split.pine` into the TradingView Pine editor and add it to a chart.
2. Pick a Timeframe Preset (TheStrat Classic, Scalp, Day Trade, Futures/Crypto, Swing Trade, Investing) — or set Custom and configure the six slots yourself.
3. Read `docs/concepts/bar-types.md` and `docs/concepts/signals.md` to learn what you're looking at.

## Contents

### `pine/` — indicator source (newest first)

- **`TheStratSuite_v2.2.7-split.pine`** — current build. NOTATION-1: canonical uppercase F2u/F2d
  (lowercase live-'f' retired; liveness = slot position / '*' prefix / words).
- `TheStratSuite_v2.2.6-split.pine` — RECON-KEY-1 (+12h key normalization for daily
  reconstruction) and TFCOLOR-1 (in-force column no longer highlights inside bars).
- `TheStratSuite_v2.2.4-split.pine` — GLUE milestone: HTF-straddle fix line plus GLUE-1 / GLUE-2b
  (CME holiday-glued-bar handling).
- `TheStratSuite_v2.2.2-split.pine` — HTF-straddle T1 period shift + T3 daily reconstruction.
- `TheStratSuite_v2.2.0.pine` — pre-split baseline.
- `TheStratSuite_v180_June16_2026.pine` — June 2026 pre-audit original.
- `research/` — Volume Profile research fixtures and diagnostics (MPL-headered; not part of the
  shipped indicator). See `pine/research/README.md`.

### `docs/`

Start at `docs/README.md` (the index). Trader-facing docs live in `docs/concepts/`, engineering docs in `docs/engineering/`. Highlights:

- `concepts/bar-types.md` — bar structures, notation rules, Failing 2s, hammers/shooters.
- `concepts/signals.md` — the seven signal types, defaults, filters, in-force mechanics.
- `engineering/repaint-prevention.md` — the no-repaint contract: 7 rules + contributor checklist.
- `engineering/htf-correctness.md` — multi-timeframe correctness: straddle/glue handling, +12h
  normalization, daily reconstruction, preview mode.
- `TheStratSuite_v2.2.1_Settings_Reference.md` — full settings reference (v2.2.1; refresh pending).
- `DESIGN_CONSTRAINTS.md` — intentional design decisions reviewers should not flag as bugs.
- `v2.2.3_holiday_glue_fix.md` — postmortem of the CME holiday-glue incident.

### `diagnostics/`

Not part of the shipped indicator. Two kinds of material: throwaway probe scripts from the
HTF-straddle investigation (retained because they document how the straddle behavior was
measured), and `volume-profile-phase0/` — the offline evidence-gate tooling for the Volume
Profile research track (four Python `vpx` tools with unit tests, schemas, and worked examples;
see its README).

## Engineering ground rules

- **No-repaint is a hard, zero-tolerance requirement.** What you saw live is what a reload shows. The rules are documented, with case studies, in `docs/engineering/repaint-prevention.md`.
- Fix history is inline via `// FIX <id>` comments (P0/P1/P2, BTC, CSS, TAW, MOD, HTF-STRADDLE, GLUE, RECON-KEY, TFCOLOR, NOTATION). Every tag marks a solved bug and the rule that came out of it — grep for them.
- Contributions should pass the contributor checklists at the end of the two engineering docs before review.

## License

Mozilla Public License 2.0 — see `LICENSE`. Source files carry the standard MPL header.
