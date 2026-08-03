# Bar Types & Notation

Every candle in TheStrat is classified by one question: **what did it do to the previous candle's range?** This doc defines the three structures, the notation the Suite uses for them, and the rules that resolve the ambiguities. Where the broader Strat community never standardized something, I picked a rule and wrote down why.

Applies to v2.2.7-split and later. (v2.2.6 and earlier used lowercase `f2u`/`f2d` for a live Failing 2 - see the notation rule below for why that was retired.)

---

## The three structures

| Type | Name | Definition (vs prior candle) |
|---|---|---|
| **1** | Inside | Broke neither side: high <= prior high AND low >= prior low |
| **2** | Directional | Broke exactly one side: `2u` took out the prior high only, `2d` the prior low only |
| **3** | Outside | Broke both sides |

Three edge rules the definitions imply:

- **Equal is not a break.** A high that exactly matches the prior high has not crossed it. A bar with an equal high and a held low is still an inside bar.
- **Gaps don't get their own type.** A gap-up open above the prior high already makes the bar at least a `2u` (its high is above the prior high by definition); if it also trades below the prior low, it's a `3`. Classification is always the range test, never the open.
- **A `2u` can be red.** The `u` in `2u` names *which side broke*, not the candle's color. A bar that pokes above the prior high and fades to close red is still a `2u` - that failure mode has its own name below.

## The second channel: close vs open

Independent of structure, every candle either closed above its open or didn't. This is a separate piece of information - it drives Full Timeframe Continuity, the data-table colors (yellow = inside closing above open, orange = inside closing below), and the direction suffix on types where "which side broke" can't provide one:

| Token | The digit says | The u/d says |
|---|---|---|
| `2u` / `2d` | one side broke | **which side broke** |
| `1u` / `1d` | nothing broke | close above / below open |
| `3u` / `3d` | both sides broke | close above / below open |

Read that table twice - **the u/d suffix means two different things depending on the digit.** It's the single most common misreading of Strat notation. The Suite keeps the community convention on-chart, but treats the two meanings as separate channels internally, and so should you: *structure* (1/2/3 + break side) and *sign* (close vs open) are orthogonal facts about the same candle.

One tie-break: a close exactly at the open counts as **not above** - it buckets down (`1d`, `3d`).

## Failing 2s: `F2u` / `F2d`

A **Failing 2** is a directional bar whose break got rejected: price took out one side of the prior range, then came back. `F2u` = a failed upside break (bearish implication). `F2d` = a failed downside break (bullish implication). Note the direction letter names *the break that failed*, not the trade it sets up - an `F2u` is a short setup.

Also known in the community as a **Range Reclaim**, **Potential 3**, or **1-bar Rev Strat**. The Suite's settings use "Failing 2s (Range Reclaims)."

The Suite offers four detection methods (Advanced -> Failing 2 Detection):

- **Reclaim** (default): the bar closes back inside the prior candle's range.
- **Open**: the bar closes against its breakout direction (a `2u` closing below its open).
- **Reclaim + Open**: both required.
- **Reclaim OR Open**: either suffices.

### The notation rule (decided 2026-07-21, v2.2.7)

**Notation is tense-free: always uppercase `F2u`/`F2d`, live or closed.** Earlier versions wrote a *forming* Failing 2 in lowercase (`f2u`) to signal "this is still in progress." That case distinction was retired because it was a liveness marker applied to exactly one bar type - a forming `2u` that might still become a `3u` was never written differently - and because case-significant notation fails everywhere it matters: it can't be spoken aloud, it's illegible at small label sizes, and it's a footgun in any API or query context.

Liveness is carried where it's carried for every other bar type:

- **Position** - the last token of a combo is always the forming candle.
- **`*` prefix** - a potential state that hasn't confirmed (a pre-F2 open level shows `*F2d`).
- **Words** - Universal mode says `FAILING` while live; past tense is failed. Humans get tense from language, not casing.

## Hammers & Shooters (`HAM` / `SHO`)

Not bar types - **proportion patterns** layered on top of any structure, defined by where the body sits in the candle's range. A hammer rejected the low (conviction for upside); a shooter rejected the high. The Suite offers three definitions (Filters -> Hammer/Shooter Detection):

- **Broad** (default): open *and* close both in the upper half (hammer) or lower half (shooter). A body centered exactly at the midpoint is neither.
- **Classic**: small body (<=30% of range), rejection wick >=3x the body, body confined to the top/bottom third, close near the rejected extreme.
- **Pin Bar** (strict): open *and* close both inside the extreme quarter of the range.

An optional color filter requires hammers to be green and shooters red. In Strat notation these appear as ` HAM`/` SHO` suffixes; Universal mode marks them with `◆`.

## Reading combo strings

`2d-1-2u` reads oldest -> newest: the candle two back (`C2`) was a `2d`, the prior candle (`C1`) was inside, the current candle (`CC`) broke up. Conventions:

- **`*` prefix** = potential - the current candle hasn't broken the trigger yet (`*2d-1-2u` is a setup, not a signal).
- **`F` inside a combo** marks a slot that was itself a Failing 2: `F2d-2u` means the prior bar failed its downside break and the current bar is following through up.
- Dashes are a display setting; `2d12u` and `2d-1-2u` are the same string.

## The canonical model (builders & API consumers)

Every classification above is a rendering of one four-field tuple - this is the model to use in any programmatic context, and it's how the Suite and priceactionapi (an external API serving the same bar classifications - traders can skip its column) stay mutually translatable:

| Field | Values | Suite rendering | priceactionapi |
|---|---|---|---|
| `structure` | `1`, `2u`, `2d`, `3` | the digit + break side | same, uppercase family |
| `above_open` | true / false | `u`/`d` on 1s and 3s; table colors; FTFC | `>` / `<` (`ao` flag) |
| `failed` | true / false | `F` prefix | `F` prefix (`is_failed`) |
| `live` | forming / closed | last combo slot; `*` when unconfirmed | `provisional` |

Rule of thumb: **the tuple is the truth; notations are projections.** When two displays seem to disagree, resolve them back to the tuple before assuming a bug.

---

*Engine internals: `calcBarType`, `detectBarTypeAndFailed`, `detectFailed2` - see `../engineering/` docs.*
