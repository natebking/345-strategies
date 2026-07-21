# TheStrat Suite — Documentation

Docs index and roadmap for the open-source release prep. Two audiences, two folders:

- **`concepts/`** (planned) — for traders using the indicator. What the signals mean, how to read the chart, how to configure it.
- **`engineering/`** — for builders forking or extending the script. How the engine works and the rules that keep it correct.

Engineering docs reference the code by function name and `FIX` tag (grep-able), not line number. Written against `pine/TheStratSuite_v2.2.6-split.pine`.

## Existing docs

| Doc | Audience | Notes |
|---|---|---|
| `engineering/repaint-prevention.md` | Builder | The no-repaint contract: 7 rules + contributor checklist |
| `v2.2.3_holiday_glue_fix.md` | Builder | Postmortem: CME holiday-glued bars (GLUE-1 / GLUE-2b) |
| `DESIGN_CONSTRAINTS.md` | Builder | Intentional design decisions — what reviewers must not flag as bugs |
| `TheStratSuite_v2.2.1_Settings_Reference.md` | Trader | Full settings reference (written for v2.2.1; needs a v2.2.6 refresh pass) |

## Planned

| Doc | Audience | Priority |
|---|---|---|
| `engineering/htf-correctness.md` — validTimeframe gate, HTF straddle, preview mode, daily reconstruction | Builder | Launch — next up |
| `concepts/bar-types.md` — 1/2u/2d/3, Failed 2s, gap handling, hammer/shooter definitions | Trader | Launch |
| `concepts/signals.md` — taxonomy: inside rev/cont, 2-2, 3-2 expansions, outside bars, reclaims | Trader | Launch |
| Root repo `README.md` rewrite for public audience + `LICENSE` (recommend MPL-2.0, Nate to confirm) | Both | Launch |
| `engineering/architecture.md` — the pipeline: security → preview shift → compute → filter → render | Builder | Fast-follow |
| `engineering/drawing-decisions.md` — shouldDrawC1Level tree, suppression rules | Builder | Fast-follow |
| `engineering/rendering.md` — x/y anchoring, update-in-place, label pool, consolidation | Builder | Fast-follow |
| `CHANGELOG.md` backfill from release notes + FIX history | Both | Fast-follow |
| `concepts/ftfc.md`, `concepts/targets-and-stops.md`, `concepts/reading-labels.md` | Trader | Later |
| `engineering/performance.md` — calc_bars_count tiers, tuple security calls, islast gating | Builder | Later |
| `CONTRIBUTING.md` + pre-publication scrub checklist (pricing refs, business details) | — | Later |

## Source material

- `FIX` comments in `pine/TheStratSuite_v2.2.6-split.pine` — each tag documents a solved bug and its rule
- `DESIGN_CONSTRAINTS.md` — the invariants list; feeds `architecture.md`
- `v2.2.3_holiday_glue_fix.md` — feeds `htf-correctness.md`
- `TheStratSuite_Project.md` — project history and business context; lives **outside this repo** (local working folder) deliberately, pending the pre-publication scrub
