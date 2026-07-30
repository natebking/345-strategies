# Full Timeframe Continuity (FTFC)

One question, asked on every timeframe at once: **is the current candle trading above or below its open?** When every timeframe you monitor gives the same answer, you have Full Timeframe Continuity — the 30-minute candle, the daily, and the monthly are all being pushed the same way at the same moment. FTFC doesn't generate trades; it tells you which trades are swimming with the current and which are fighting it.

Bar-type notation is defined in `bar-types.md` — this doc assumes it. Applies to v2.2.7-split.

---

## The idea

Every candle carries two independent facts (`bar-types.md` calls them channels): its *structure* — what it did to the prior range — and its *sign* — close above or below its own open. FTFC is built entirely from the sign channel. Structure tells you what a setup is; continuity tells you whether the broader stack is leaning with it.

Three readings:

| Reading | Meaning |
|---|---|
| **FTFC Up** | Every monitored timeframe's current candle is above its open |
| **FTFC Down** | Every monitored timeframe's current candle is at or below its open |
| **Conflict** | Anything else — the timeframes disagree |

Conflict is the market's resting state. Full continuity is the exception, and that's exactly what makes it information: when every enabled timeframe agrees, participants at every scale are positioned the same way, and a trade against them needs all of them to be wrong.

---

## How the Suite computes it

`calculateFTFC` re-evaluates on every chart update. Each **enabled** timeframe slot contributes its *forming* candle — not the last completed one — and the test is close-so-far versus open. All above → Up. All at-or-below → Down. Mixed → Conflict.

The details that matter:

- **It's live by design.** The forming candle's close moves tick by tick, so FTFC can flip intrabar — especially when a big timeframe is hovering at its open. That's the point: continuity is a statement about *now*.
- **Flat buckets down.** A close exactly at the open counts as *not above* — it blocks FTFC Up, not FTFC Down. Same tie-break as everywhere else in the Suite (`bar-types.md`).
- **Only enabled slots vote.** The Timeframe Preset (or your Custom rows) decides which of the six slots are live; a disabled slot contributes nothing — no levels, no table row, no FTFC vote. Slots with no data yet (young symbols) are skipped rather than counted against continuity.
- **Preview Mode doesn't distort it.** FTFC always reads the real forming candles, never the preview-shifted synthetic ones.
- **Keep the chart at or below Timeframe 1.** Slots below the chart's timeframe are refused for signals and greyed in the table (see `../engineering/htf-correctness.md`) — don't leave them enabled expecting a meaningful vote.

---

## Where you see it

**The data table row.** Both table modes render a merged full-width FTFC cell: green **FTFC Up**, red **FTFC Down**, gray **Conflict**. With Label Style = Universal the same cell reads **Trend Up** / **Trend Down** / **No Trend**. The table is FTFC's only on-chart readout — hide the table and you lose the display (alerts still work).

**Don't reconstruct it from the CC column.** A `2u` can close red — on 2s the suffix names the break side, not the sign (`bar-types.md`, the u/d overload). Only `1u/1d` and `3u/3d` suffixes carry close-vs-open. The FTFC cell is the authoritative read.

**Alerts.** Two surfaces:

- **Include FTFC** (Alerts - Detailed → Include FTFC, off) appends the state to consolidated alert text: `1H 2d-1-2u HAM @ 542.10 … | FTFC Up`.
- Four dedicated alert conditions — **FTFC Shifted**, **FTFC Up**, **FTFC Down**, **FTFC Conflict** — fire on the *transition into* that state, not continuously while it holds.

---

## The settings that touch it

| Setting | Where | Default | What it does |
|---|---|---|---|
| **FTFC** checkbox, per signal family | Each Signals group — all seven families have one | Off | Suppresses that family's setups when continuity stands against them |
| **Exhaustion Excludes from FTFC** | Advanced → Exhaustion Behavior | Off | Table cell only: drops structurally finished timeframes from the reading |
| **Include FTFC** | Alerts - Detailed | Off | Appends the FTFC state to consolidated alert messages |
| **Preset / Timeframes 1–6** | Timeframe Preset, Timeframes | TheStrat Classic | Decides which slots vote |

### How the filter actually gates

The per-family FTFC checkbox is a **veto, not a prerequisite**. With it on, a bullish setup is suppressed while FTFC reads full **Down** — and only then. Conflict, the usual state, does not suppress:

| FTFC reading | Bullish setup, filter on | Bearish setup, filter on |
|---|---|---|
| Up | shows | suppressed |
| Conflict | shows | shows |
| Down | suppressed | shows |

So the filter removes the lowest-probability case — a setup fighting a fully aligned stack — without demanding the stack already agree with you before a setup can appear. (The gate lives in `shouldDrawC1Level`; each family's checkbox is wired to the family a setup *resolves to* — a hammer reversal obeys the 2-2 Reversals toggle, not Inside Reversals' — `FIX BTC-1`.)

Two places are deliberately stricter — they demand agreement *with* the trade, not just absence of opposition:

- **Failing 2 in-force.** With the Reclaims FTFC filter on, a bullish `F2d` goes in force (and alerts) only under full FTFC Up; its levels still draw under Conflict. A reclaim fades a just-failed breakout, so the filter insists the whole stack back the fade. Expect far fewer F2 signals with this on.
- **Outside-bar targets.** With the Outside Bars FTFC filter on, a `3u`'s magnitude and exhaustion targets require full FTFC Up (mirrored for `3d`).

### Exhaustion Excludes from FTFC

A timeframe that has already hit its exhaustion target (or magnitude, when no exhaustion level exists) has structurally finished its move — arguably it shouldn't keep blocking the reading. Turn this on and exhausted timeframes are dropped from the calculation: if five of six are bearish and the lone bullish one has already hit exhaustion, the cell reads **FTFC Down** instead of **Conflict**.

**Display only** (`FIX P1-e`): this changes the data-table cell and nothing else. Signal gating and alerts always use the raw reading, so toggling it will never make signals appear or disappear. Treat it as a read aid, not a filter.

---

## Using it

1. **As context first.** The row is a one-glance regime check: Conflict says pick your spots; full continuity says one side owns every timeframe right now.
2. **Continuations pair naturally.** `2u-1-2u` under FTFC Up is a pullback resuming a move the whole stack agrees on — the classic use, and the recommended way to tame 2-2 Continuations' noise (`signals.md`).
3. **On reversals it trims, not chokes.** Because the filter is a veto, a bullish reversal survives Conflict — it only disappears while every timeframe is against it, which is precisely when fading is most expensive.
4. **Reclaims + FTFC is strict on purpose.** Turn it on only if you want F2s exclusively when the full stack backs the fade.
5. **FTFC Shifted as a regime ping.** One alert that fires whenever the stack changes its answer — useful even if you never enable a single filter checkbox.

---

*The close-vs-open channel and the u/d overload: `bar-types.md`. The families each FTFC checkbox filters: `signals.md`. Where the gate sits in the draw pipeline: `../engineering/drawing-decisions.md`.*
