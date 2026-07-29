# Volume Profile Phase 0 Probe

Status: diagnostic research build

Pine behavior version: `0.1.0`

Wire protocol: `VPX|schema=1`

Experiment tag: `VP0-GRID-1`

## Live validation status

Accepted ESU2026 1-, 5-, 15-, and 60-minute display-timeframe cells passed
the full local evidence gate on 2026-07-25. The cross-timeframe comparator
classified the matched source vintage as invariant: both profile paths consumed
the same 405 one-minute footprints and returned identical POC, VAH, VAL, volume,
row count, source fingerprint, and diagnostics. The 5-minute cell also has a
same-vintage repeat.

This is one locked-window implementation sentinel. The planned 30-range matrix,
independent numerical oracle, native TradingView comparison, and live/reload
tests remain required before broader conclusions.

## Purpose

This probe answers one implementation question before any trading logic is built:

> Can a custom Volume Profile produce the same frozen levels from the same source observations when the display chart timeframe changes?

It is not a strategy and does not claim that a profile level predicts support, resistance, or a profitable trade. It generates research evidence for two deliberately small profile families:

- the most recent complete TradingView RTH session, defined as `[08:30, 15:15)` in `America/Chicago`; and
- one manually specified frozen range, defined by exact UTC millisecond boundaries `[start, end)`.

## Information budget

The probe creates no visible chart drawings, profile histogram, boxes, labels, signals, alerts, or orders. Its only plots use `display.data_window`, which exposes numeric values to TradingView's chart-data CSV export without painting them on the chart.

This preserves the product requirement: the eventual trading indicator may calculate extensively backstage, but a blank chart is the correct default when no level has passed a locked evidence gate.

## Fixed construction policy

- Calculation source: native footprint rows requested in a fixed one-minute context.
- Primitive grid: one minimum tick per requested footprint row.
- Output grid: a configurable whole number of minimum ticks per row, initially four for ES/MES.
- Grid origin: global integer-tick zero, not the selected range low.
- Volume assignment: a primitive row is assigned by its midpoint tick to one output bin.
- POC tie break: highest volume, then closest to the profile's volume-weighted mean bin center, then the lower bin.
- Value Area: contiguous expansion from POC toward the requested target. Compare the next row above and below, prefer greater volume, then proximity to POC, then the upper row. Do not add a row that would overshoot the target.
- Exported boundaries: POC lower/upper tick boundaries, VAL lower boundary, and VAH upper boundary. The Data Window-only POC plot uses the row midpoint.
- Frozen-only output: developing profile levels are not exported as accepted levels.

The one-minute calculation context is independent of the display chart. Phase 0 supports standard time-based chart timeframes from one through 60 minutes. A run on another chart type or an unsupported timeframe is invalid.

For CME futures, record the chart UI session semantically as `eth` or `rth`. TradingView's Pine session name uses a different namespace: ES/MES with Electronic Trading Hours selected reports `regular`, while the shortened RTH selection reports `us_regular`. The UI readback is authoritative for the chart-selection field.

## Data requirements and limitations

`request.footprint()` requires a TradingView Premium or Ultimate plan and Pine permits only one footprint request per script. The probe therefore makes one footprint-dependent lower-timeframe request and immediately converts returned footprint objects into primitive numeric state.

TradingView can return `na` for unavailable footprint history. A complete profile never silently substitutes chart-bar volume or another approximation. Missing source observations, nonstandard sessions, row-alignment problems, or resource limits make the affected run/profile ineligible.

The normal RTH baseline requires:

- an exact 08:30 Central first source minute;
- an exact 15:14 Central last included source minute;
- 405 included one-minute observations; and
- no missing footprint object on an included observation.

Shortened sessions are excluded from this first baseline rather than reinterpreted as normal days. The manual profile requires its configured expected source-observation count and full coverage of both boundaries.

## Files

- `Volume_Profile_Phase0_Probe_v0.1.0.pine` — personal Pine v6 diagnostic.
- `vpx_accept.py` — local, standard-library-only artifact acceptance checker.
- `vpx_invariance.py` — cross-display-timeframe fixed-source profile comparator.
- `vpx_matrix.py` — deterministic session-matrix generator and offline batch
  evidence auditor.
- `vpx_behavior.py` — fail-closed, one-minute first-touch behavior evaluator
  for accepted PRIOR_RTH POC, VAH, and VAL evidence.
- `schemas/vpx-1.json` — parsed record contract for the `VPX` wire format.
- `schemas/vpx-session-plan-1.json` — locked session-plan input contract.
- `schemas/vpx-behavior-1.json` — behavior-report contract.
- `examples/` — non-production logical-run, attempt, and UI-readback examples.
- `tests/test_vpx_accept.py` — synthetic acceptance and deliberate-rejection cases.
- `tests/test_vpx_invariance.py` — profile-invariance and tamper-rejection cases.
- `tests/test_vpx_matrix.py` — deterministic generation, alignment, idempotency,
  conflict, coverage, and audit cases.
- `tests/test_vpx_behavior.py` — touch semantics, excursions, break/reaction,
  censoring, and evidence-tamper cases.

Generated TradingView logs, CSV files, screenshots, hashes, and parsed results do not belong in Git. Store them in a local study workspace outside the repo, e.g.:

```text
../volume-profile-study/runs/
```

Run the offline contract suite from the repo root with:

```bash
cd diagnostics/volume-profile-phase0
PYTHONPYCACHEPREFIX=/private/tmp/vpx-phase0-pycache \
  python3 -m unittest discover -s tests -v
```

Validate one captured attempt without overwriting an existing result:

```bash
python3 vpx_accept.py check \
  --manifest manifest.json \
  --attempt attempt.json \
  --logs raw/pine_logs.csv \
  --chart-csv raw/chart_data.csv \
  --ui-readback raw/ui_readback.json \
  --output acceptance.json
```

Compare two already accepted attempts:

```bash
python3 vpx_accept.py compare acceptance-a.json acceptance-b.json
```

Compare two or more accepted cells from distinct display timeframes. The
comparator verifies each sibling manifest and Pine Logs file against the hashes
stored in its acceptance report, compares the complete profile projection, and
explicitly permits display-chart counts/fingerprints and chart-state hashes to
differ:

```bash
python3 vpx_invariance.py \
  acceptance-1m.json \
  acceptance-5m.json \
  acceptance-15m.json \
  acceptance-60m.json \
  --output display-timeframe-invariance.json
```

Generate hash-consistent 1-, 5-, 15-, and 60-minute logical-run manifests
from one base manifest and a session plan:

```bash
python3 vpx_matrix.py generate \
  --plan examples/session-plan.phase0.json \
  --template examples/manifest.phase0.json \
  --output-dir /path/to/generated-matrix \
  --report /path/to/generated-matrix/generation.json
```

Generation creates one directory per logical run plus `matrix-index.json`.
Logical-run IDs, exact Pine tokens, configuration tokens, settings hashes,
chart-state hashes, expected bar starts, and expected bar counts are
deterministic. Re-running the same plan is idempotent; the generator refuses to
replace an existing file whose contents differ.

The plan's `measurement.bar_anchor_ms` is the timestamp grid used to align
display bars. For the example ETH chart, an epoch anchor of `0` leaves the
08:30 Central start aligned at 1, 5, and 15 minutes, while the first eligible
60-minute bar begins at 09:00 Central. This produces expected counts of
405/81/27/7 for the four display timeframes. Use an anchor that matches the
actual chart/session convention; it is part of the locked plan, not an
inference made after export.

Audit acceptance and invariance reports already present on disk, optionally
checking coverage against the generated index:

```bash
python3 vpx_matrix.py audit \
  --root /path/to/volume-profile-study \
  --index /path/to/generated-matrix/matrix-index.json \
  --output /path/to/matrix-audit.json
```

The audit command is read-only with respect to evidence and never controls
TradingView. It reports accepted and rejected attempts, accepted logical runs,
invariant and non-invariant comparisons, scan errors, and any planned cells
that are still missing or unaccepted.

Evaluate descriptive first-touch behavior from one accepted one-minute cell:

```bash
python3 vpx_behavior.py \
  --acceptance /path/to/attempt/acceptance.json \
  --chart-csv /path/to/attempt/raw/chart_data.csv \
  --horizons-minutes 5,15,30,60 \
  --reaction-threshold-ticks 8 \
  --break-distance-ticks 4 \
  --break-consecutive-closes 2 \
  --output /path/to/attempt/behavior.json
```

The evaluator re-runs the complete acceptance gate and requires the supplied
CSV and all inferred sibling evidence to match the hashes in
`acceptance.json`. It accepts only a complete one-minute next-RTH path. POC is
represented by its complete output row; VAH and VAL use the one output row
immediately inside Value Area. Touch is an inclusive OHLC overlap with that
closed price interval.

Entry direction is derived from the touch-bar open with a guard for an
unobserved gap through the entire zone. Penetration and close-beyond counts
include the touch bar. Directional MFE/MAE begin with the following bar because
OHLC cannot establish whether a touch-bar extreme happened before or after
first touch. Break confirmation requires the configured number of consecutive
closes at the configured distance beyond the far edge. Reaction, break,
same-bar ambiguity, no-touch censoring, and session-end horizon censoring are
reported explicitly. All prices and thresholds are integer ticks.

The default horizons and thresholds are fixed implementation defaults, not
values selected from captured outcomes. A behavior report is descriptive
evidence only; it does not establish support, resistance, prediction, or
trading performance.

The files under `examples/` are internally hash-consistent worked examples, not captured market evidence. Recalculate the canonical settings/chart hashes and source digest whenever their corresponding values change.

## Export channels

The probe uses two independent channels:

1. Pine Logs contain the run header, ordered effective configuration, frozen profile records, source fingerprints, diagnostics, and exactly one terminal record.
2. Data Window-only plots contain exact 31-bit identity tokens, frozen profile levels, source fingerprints/counts, and the error mask for reconciliation through TradingView's **Export chart data** CSV.

Every machine log line starts with `VPX|schema=1`. Sequence numbers begin at one, remain contiguous, and end with one `RUN_END` or `RUN_ABORT`. UTC millisecond fields inside the message are authoritative; the Pine Logs pane's displayed timezone is not.

The CSV contains exactly one row where the configured terminal column equals `1`. Final chart/profile counts and fingerprints may be blank on every earlier row, but they must be present on that terminal row and equal the `RUN_END` record. The error mask must be zero on every applicable measurement row and on the terminal row. Any missing or duplicate terminal marker, nonzero applicable error mask, or log/CSV disagreement rejects the attempt.

## Error mask

| Bit | Value | Meaning |
|---|---:|---|
| 0 | 1 | Unsupported display timeframe or chart type |
| 1 | 2 | Footprint data unavailable |
| 2 | 4 | Manual range incomplete |
| 3 | 8 | RTH session incomplete |
| 4 | 16 | Unexpected footprint-row span or grid alignment |
| 5 | 32 | Output-bin capacity exceeded |
| 6 | 64 | Footprint row-volume sum does not reconcile |
| 7 | 128 | Invalid input configuration |
| 8 | 256 | Lower-timeframe result arrays have different lengths |

An error bit is evidence, not a warning to ignore. The local checker rejects an attempt when an applicable run-invalidating bit is set.

## First-run protocol

Use a dedicated TradingView layout such as `VP Phase 0 Research`. Do not use the working trading layout and do not delete or hide unrelated drawings.

For the first three runs:

1. Use a standard ES or MES time chart and a window with one known normal RTH session plus one exact manual range.
2. Apply the immutable logical-run manifest values once.
3. Confirm the Pine script compiles and reaches a matching terminal record.
4. Download the complete, unfiltered Pine Logs CSV.
5. Export chart data with the probe's Data Window-only plot columns.
6. Save semantic chart-state readback and one audit screenshot.
7. Run the local acceptance checker before comparing any levels.
8. Repeat the identical logical run with a new attempt ID **and** attempt token. When the full data-vintage tuple—fingerprint algorithm, chart count/fingerprint, and profile count/fingerprint—matches, the profile/event payload must reproduce exactly.
9. Repeat on 1-, 5-, 15-, and 60-minute display charts without changing the logical profile specification.

Only after this path succeeds should the study run the 30-range parity/stability matrix against TradingView's native Fixed Range and Session profiles.

## Promotion boundary

Phase 0 validates calculation integrity only. POC, VAH/VAL, HVN, or LVN roles remain hypotheses until the preregistered level tests beat matched placebo and simple-price benchmarks out of sample. None of those features should create a routine chart object merely because the probe can calculate it.
