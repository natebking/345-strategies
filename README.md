# TheStrat Suite - private archive

Confidential, proprietary source for **TheStrat Suite** - a commercial multi-timeframe
TheStrat price-action indicator for TradingView (Pine Script v6), sold at thestratsuite.com.

> **This repository is PRIVATE and for archival / posterity only. Confidential proprietary
> code - do not share, publish, or redistribute.**

## Contents

### `pine/` - indicator source (newest first)
- **`TheStratSuite_v2.2.4-split.pine`** - current working build. HTF-straddle fix line
  (session-aware detection + daily-bar reconstruction of the forming HTF candle) plus
  GLUE-1 / GLUE-2b (CME holiday-glued-bar handling for Auto-preview and the straddle test).
- `TheStratSuite_v2.2.2-split.pine` - prior build (HTF-straddle T1 period shift + T3 daily reconstruction).
- `TheStratSuite_v2.2.0.pine` - pre-split public release baseline.
- `TheStratSuite_v180_June16_2026.pine` - June 16 2026 baseline (pre-audit original).

### `docs/`
- `TheStratSuite_v2.2.1_Settings_Reference.md` - full settings / options reference.
- `DESIGN_CONSTRAINTS.md` - design constraints and invariants.

### `diagnostics/`
- `HTF_Timestamp_Probe.pine`, `HTF_Recon_Probe_v2.pine` - throwaway diagnostics from the
  HTF-straddle investigation. Not part of the shipped product; retained for development history.

## Notes
- Pine Script v6. No-repaint is a hard, zero-tolerance requirement throughout.
- Fix history is documented inline via `// FIX <id>` comments (P0/P1/P2, BTC, CSS, TAW, MOD,
  HTF-STRADDLE, GLUE).
- Archived 2026-07-07.
