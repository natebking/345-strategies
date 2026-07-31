# Volume Profile research track

Standalone research diagnostics exploring whether a Volume Profile feature can earn its way into the Suite. Nothing in this directory is a trading indicator: every script is diagnostic-only, fails closed on defective source data, and makes no entry, exit, support/resistance, or prediction claim. Superseded versions are kept in place — the chain's history is part of the evidence trail.

Companion track: `diagnostics/volume-profile-phase0/` holds the locked evidence contract these experiments must eventually satisfy. See [How this relates to the evidence gate](#how-this-relates-to-the-evidence-gate).

---

## Status at a glance

| File | Status |
|---|---|
| `VP_RSD_Macro_Wall_Preview_v0.1.0.pine` | Active — range-selection adapter |
| `VP_RSD_Fixed_Range_Shelf_Diagnostic_v0.2.0.pine` | Active — footprint shelf instrument |
| `VP_RSD_Macro_Wall_Profile_Diagnostic_v0.2.0.pine` | Active — footprint parity vs native FRVP |
| `VP_RSD_Native_Like_Bar_Profile_Diagnostic_v0.3.0.pine` | **Superseded by v0.3.1** — kept for history |
| `VP_RSD_Native_Like_Bar_Profile_Diagnostic_v0.3.1.pine` | Active — OHLCV native-like reconstruction |
| `VP_RSD_Multi_Resolution_Consensus_Diagnostic_v0.4.0.pine` | Active — row-size perturbation consensus |
| `VP_RSD_Paired_Node_Consensus_Diagnostic_v0.5.0.pine` | **Superseded by v0.5.1** — kept for history |
| `VP_RSD_Local_Node_Edge_Consensus_Diagnostic_v0.5.1.pine` | Active — manual immutable-range calibration harness |
| `VP_RSD_Automatic_Local_Node_Edge_Consensus_Diagnostic_v0.6.0.pine` | Active — current automatic RSD-range head |
| `VP_Research_Preview_v0.2.0_Profile_Parity_Shell.pine` | Active — evidence-gate instrument |
| `VP_Source_Bundle_Exporter_v0.1.0.pine` | Active — evidence-gate instrument |
| `VP_Sparse_Visual_Fixture_v0.0.1.pine` | Active — visual-design fixture |

---

## The RSD diagnostic chain

"RSD" names the range-selection logic these diagnostics borrow: its v1.7 Macro swing/broadening-wall selector chooses *when* a profile is measured, so the profile scripts can concentrate on *what* sits inside the range. RSD itself is a separate production study, not part of this repo — the preview adapter below reimplements only the anchor path it needs.

The chain iterates on one question: given a frozen time range, which volume structure (a shelf boundary, a node with two edges) is real enough to survive scrutiny? Each version keeps its predecessor's construction and adds one stricter test.

### `VP_RSD_Macro_Wall_Preview_v0.1.0.pine`

This research adapter mirrors RSD v1.7's Macro broadening-wall selector and shows the selected time interval as one faint dashed box. Routine mode does not draw profile-derived levels; apply TradingView's native Fixed Range Volume Profile to the same timestamps for evaluation.

Its optional Research-mode histogram uses synthetic one-minute OHLCV allocation and is explicitly non-evaluable — it exists only to exercise the rendering path while the exact, confirmation-aware footprint accumulator is built. Every derived profile visual is labelled APPROX / NON-EVALUABLE, because spreading a minute's volume evenly through touched rows can manufacture or erase apparent shelves.

Chain position: the entry point. It answers "which range?" and deliberately nothing else.

### `VP_RSD_Fixed_Range_Shelf_Diagnostic_v0.2.0.pine`

A static-range footprint instrument. The start and end-exclusive timestamps are fixed inputs, so Pine knows the complete interval when it replays chart history — no RSD wall selection, route gating, alerts, or orders. It builds a one-tick-primitive profile from native footprint rows and surfaces up to `TOP_CANDIDATES` raw shelf boundaries ranked only by a 3-row-median log-volume change. The tooltip says it plainly: unfiltered research candidates, not trade levels. Any source, sequencing, reconciliation, or capacity defect sets a bit in the error mask and blanks the output.

Chain position: the first "what's inside the range?" instrument — candidate detection with no filtering, so later gates have something honest to filter.

### `VP_RSD_Macro_Wall_Profile_Diagnostic_v0.2.0.pine`

Joins the two halves. The automatic RSD adapter draws the Macro broadening-wall interval it *would* select, but the native-footprint profile does not consume that late-confirmed interval automatically — it uses immutable 15-minute start/end inputs that are known when Pine replays history. The workflow is manual by design: copy the two visible swing-bar times from the RSD box into the inputs, then compare the output against TradingView's native Fixed Range Volume Profile over the same inclusive bars.

Source contract: one fixed 1-minute request, one nested `request.footprint()` call, one-tick primitive rows, a fixed ticks-per-row output grid, and no OHLCV fallback. Output fails blank on source, footprint, primitive-row, volume-reconciliation, ordering, or capacity defects.

Chain position: the footprint-parity checkpoint — does our construction match the native tool when both see the same range?

### `VP_RSD_Native_Like_Bar_Profile_Diagnostic_v0.3.0.pine` — superseded

Kept for history; use v0.3.1. First version to approximate the native Fixed Range Volume Profile from lower-timeframe OHLCV bars instead of footprints, with an immutable RSD-derived 15-minute range, a selectable fixed source timeframe (1/3/5/15 minutes), and exact high/low overlap as the only volume-allocation rule. Source timeframes are deliberately explicit because the native tool can step up its internal timeframe for long ranges — the script does not claim parity, it exists to compare reconstructions with the native drawing.

### `VP_RSD_Native_Like_Bar_Profile_Diagnostic_v0.3.1.pine`

Same construction as v0.3.0 plus three explicit total-volume allocation modes — high/low overlap, close bin, and HLC3 bin — so allocation itself becomes a controlled variable in the parity comparison rather than a baked-in assumption. The included scorer remains discovery instrumentation: it displays clean log-jump boundaries and creates no production visibility decisions.

Chain position: the bridge from footprint-grade evidence to bar-grade approximation, and the construction every consensus diagnostic below inherits.

### `VP_RSD_Multi_Resolution_Consensus_Diagnostic_v0.4.0.pine`

Keeps the v0.3 native-like construction, fixes the source stream at 15-minute bars, and builds three independent profiles on perturbed grids: fine = round(base × 0.8), base, coarse = round(base × 1.2). The provisional local log-jump gates run on each grid independently; a shelf becomes a *consensus* shelf only when gated candidates from at least two distinct grids cluster within the configured base-row radius. Optional structural bounds can suppress consensus shelves too close to the RSD range low or high — suppression inputs, not additional evidence.

Chain position: the first robustness test — does a price-distribution boundary survive reasonable row-size perturbation?

### `VP_RSD_Paired_Node_Consensus_Diagnostic_v0.5.0.pine` — superseded

Kept for history; use v0.5.1. Adds the paired-node test to the v0.4 construction: every retained boundary keeps the direction of its dense side, each grid traces the contiguous high-volume component on that side and looks for a clean exit boundary, and a node is drawn only when the base-grid pair is complete and at least one neighboring grid agrees on direction and both endpoints within the consensus radius. Stable pairs rank by grid support, worst cross-grid node prominence, then minimum anchor z-score; unpaired consensus anchors remain eligible as standalones.

### `VP_RSD_Local_Node_Edge_Consensus_Diagnostic_v0.5.1.pine`

The manual calibration head. Replaces v0.5.0's component trace with a *local* paired-node test: starting at the anchor, each grid scans outward on the dense side and accepts the nearest material local maximum in opposite-direction clean strength that encloses a local volume bulge. The local-maximum test prevents tiny ripples inside one transition from becoming edges; a width cap prevents a local edge from swallowing a broad composite distribution. Anchor clustering keeps its configurable radius, mate endpoints use the stricter fixed radius of one base row, and neighbor grids are evaluated pair-aware instead of inheriting the preselected standalone neighbor.

Chain position: the frozen-range regression instrument. Its manual timestamps remain useful for reproducing an exact historical comparison, but it is not the intended browsing workflow.

### `VP_RSD_Automatic_Local_Node_Edge_Consensus_Diagnostic_v0.6.0.pine`

The current head of the exploratory chain. It joins the confirmed, swing-only RSD v1.7 Macro broadening-wall selector to the unchanged v0.5.1 local paired-node detector. The newest eligible Macro wall automatically supplies the range: same-side Far/Prior pivot to included Outer pivot. Both Macro timestamps must refine to exact 15-minute bars that printed the pivot prices; otherwise the indicator abstains. The fixed 15-minute chart bars are then reconstructed retrospectively into independent fine/base/coarse profiles, so no manual range timestamps are required.

The profile cache rebuilds only for a new confirmed structural range. The steep-wall test latches a confirmed ATR snapshot to each Macro pivot tuple, so an accepted interval cannot switch merely because current ATR drifts. While a new range is awaiting the next confirmed 15-minute close, the old profile is blanked instead of being shown against new endpoints. Source history, range length, allocation work, profile-bin capacity, volume reconciliation, and endpoint coverage all fail closed. The preferred base row may widen only when needed to keep the fine profile under the fixed 400-row capacity.

Scope limitation: the embedded adapter matches RSD v1.7 with HTF confluence OFF; Pine cannot read another applied study's private settings or state. The default 240-minute Macro timeframe, Multi-N OFF, N values, two-sided gate, and steep-wall filter must remain aligned with the production RSD used for comparison.

Chain position: the first no-date-entry browsing instrument — does automatic structural range selection plus stable two-edge node detection behave sensibly across charts before any behavioral or profitability claims are tested?

---

## Evidence-gate instruments

These three scripts serve the formal evidence pipeline rather than on-chart exploration.

### `VP_Research_Preview_v0.2.0_Profile_Parity_Shell.pine`

Slice 1 only: a headless source/profile parity shell with no lifecycle or rendering logic. Its constants — one-tick primitives, global grid origin, the POC and Value Area algorithms, the fingerprint hash family — intentionally match the Phase 0 parity core, and they are constants, not inputs: Slice 1 has no user-configurable row size or VA target. Run identity is manifest-supplied through a bounded audit envelope, and machine output uses the `VPX2|schema=1` wire prefix so captured runs can be checked by the same style of offline tooling as Phase 0.

### `VP_Source_Bundle_Exporter_v0.1.0.pine`

A headless OHLCV export aid for the frozen Volume Profile source bundle. It performs no profile calculation and draws no chart objects: it validates the environment (standard chart, exact actual-month ES/MES contract, expected tick size), per-bar OHLC tick alignment and shape, volume, and bundle identity, then emits one `VPB|schema=1` terminal record and Data Window-only plots for CSV export. Any defect sets the error mask and marks the export invalid — the bundle is evidence or it is nothing.

### `VP_Sparse_Visual_Fixture_v0.0.1.pine`

This is a manual visual-design fixture, not the Volume Profile selector.

It renders one already-validated Value Area edge as:

- one faint one-bin halo;
- one thin neutral center line; and
- one small `EXP VA EDGE` label.

The fixture is off by default and fails closed unless the exact configured ticker and time window match. It does not calculate a profile, score a level, generate an alert, or make a support/resistance claim.

Its sole purpose is to evaluate the information budget before implementing the automated research preview specified in `RESEARCH_PREVIEW_V0_2_SPEC.md`, kept in the local volume-profile study workspace outside this repo.

---

## How this relates to the evidence gate

`diagnostics/volume-profile-phase0/` is the contract; this directory is the sketchbook. The Phase 0 README defines the full evidence gate — the `VPX|schema=1` wire format, the acceptance checker, the cross-display-timeframe invariance comparator, the session-matrix generator/auditor, and the fail-closed behavior evaluator — plus the promotion boundary: POC, VAH/VAL, HVN, or LVN roles remain hypotheses until preregistered level tests beat matched placebo and simple-price benchmarks out of sample.

The traffic between the two tracks flows one way:

1. Scripts here generate candidates, constructions, and eyeball comparisons against TradingView's native tools.
2. Anything that looks promising gets formalized into a locked, manifest-driven run and pushed through the Phase 0 acceptance/invariance/behavior pipeline.
3. Only levels that pass that gate may ever create a routine chart object in the production Suite. Looking convincing on a chart in this directory promotes nothing.

Captured evidence — TradingView logs, CSV exports, screenshots, hashes, parsed results — does not belong in Git. Store it in a local study workspace outside the repo, alongside the research specs it documents.

---

## Contributor checklist

Before adding or revising anything in this directory:

1. Does the header state the script's diagnostic-only scope — and explicitly list what it does *not* claim (entries, exits, support/resistance, production visibility)?
2. Does every defective-source path fail closed — blank output plus an error-mask bit — rather than silently substituting chart-bar volume or another approximation?
3. Is any non-evaluable visual labelled APPROX / NON-EVALUABLE on the chart itself, not just in comments?
4. Is a revision shipped as a *new* versioned file, with the old file left in place and marked superseded in this README? Delete nothing.
5. Is all captured evidence kept in the local study workspace outside the repo — and is anything aimed at the production Suite routed through the `diagnostics/volume-profile-phase0/` evidence gate first?
