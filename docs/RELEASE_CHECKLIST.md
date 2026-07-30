# Open-Source Release — Pre-Flight Checklist

The repo is currently **private**. This is everything between here and flipping it public. Prep items are done; the release-moment items are deliberately left for Nate.

## Done (release prep, 2026-07-21)

- [x] `LICENSE` — MPL-2.0, canonical text. Current source file carries the MPL header block.
- [x] Public `README.md` — confidential/archive framing removed.
- [x] Launch docs: `concepts/bar-types.md`, `concepts/signals.md`, `engineering/repaint-prevention.md`, `engineering/htf-correctness.md`, docs index.
- [x] NOTATION-1 shipped in v2.2.7-split (canonical F2u/F2d, matches priceactionapi).
- [x] Scrub grep of tracked files: no Whop/pricing/subscription references, no PASS/StratDB references. Two local `/Users/…` paths found in docs and removed (DESIGN_CONSTRAINTS.md, Settings Reference §note).
- [x] Repo renamed `thestratsuite` → `345-strategies` (2026-07-30): the repo is the 345 Strategies workshop; "TheStrat Suite" names the indicator product only (boundary rule in root README). Old GitHub URLs and remotes redirect automatically.
  - **Standing rule: never create a new repo named `natebking/thestratsuite`.** The redirect only lives while the old name stays unused — reusing it would silently capture every old link and clone remote.

## Nate — before or at the flip

- [x] **Sync the TradingView Pine editor with the repo.** Done 2026-07-30 at v3.0.0 (superseded the v2.2.7 paste): compile-verified and running on chart. Note: this is the *editor* copy — publishing the 3.0.0 update to the TV listing is a separate go decision; on publish, retitle CHANGELOG `[Unreleased]` to a dated `[3.0.0]` heading.
- [ ] **Read the docs with fresh eyes** — they were drafted from the code and fix history; you'll catch voice or emphasis issues I can't.
- [ ] **Git history call.** The pre-rewrite README (with "private archive / Confidential" wording) and the removed local paths remain visible in commit history. Low risk — nothing sensitive beyond framing and a home-directory path — but it's your name on it. Options: accept as-is (recommended; rewriting history is churn for no real gain) or squash-recreate the repo before flipping.
- [ ] **Flip visibility**: GitHub → Settings → Danger Zone → Change visibility → Public.
- [ ] **After the flip**: add topics (`pine-script`, `tradingview`, `thestrat`, `trading`, `indicator`) so it's findable.
- [ ] **After the flip**: publish the canonical URL `github.com/natebking/345-strategies` anywhere you link the repo (thestratsuite.com, TV listings). The old `thestratsuite` URL redirects, but don't rely on it in public copy.
- [ ] **TradingView open-source migration** (verified against TV docs 2026-07-30: a published script's privacy/visibility are PERMANENT — update dialog greys them out; no conversion path exists):
  - [ ] Flip this repo public first, so the TV description's GitHub link resolves.
  - [ ] Publish v3.0.0 as a NEW publication: Privacy = Public, Visibility = Open. TV applies MPL-2.0 to open scripts by default — matches this repo's license automatically.
  - [ ] Title the new listing exactly "TheStrat Suite" — no "[Open Source]" suffix (TV badges open scripts itself; the new listing is the canonical product). Rename the old listing via Edit to "TheStrat Suite (Legacy)"; no version numbers in either title.
  - [ ] New description explains the lineage (replaces the invite-only listing; now free and open source) per the house rules' explain-in-description pattern, plus the SpinTrades story and the repo link.
  - [ ] Repurpose the old invite-only listing as a signpost: final update with release notes pointing to the new listing; edit description and Author's instructions ("Get Access" → "now free and open source"). It cannot be deleted; existing invited users keep working.
  - [ ] After TV publish: retitle CHANGELOG [Unreleased] → dated [3.0.0].
- [ ] **Lite/paid positioning**: decide how the existing TV listings relate to the open repo. Deliberately not addressed anywhere in the repo docs.

## Deliberately excluded from the repo

- `TheStratSuite_Project.md` (business strategy, pricing, personal trading details) — stays in the local working folder.
- Older pine versions don't carry MPL headers — they're archive; the current build does. Add headers on future versions as they're cut.

## Post-launch docs backlog

Done (2026-07-28) — the full backlog is written and verified: architecture.md, drawing-decisions.md, rendering.md, performance.md, CHANGELOG backfill, Settings Reference refreshed to v2.2.7, CONTRIBUTING.md, and the remaining concepts docs (ftfc, targets-and-stops, reading-labels). `docs/README.md` is the current index.
