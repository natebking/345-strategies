# Volume Profile research visuals

## `VP_RSD_Macro_Wall_Preview_v0.1.0.pine`

This research adapter mirrors RSD v1.7's Macro broadening-wall selector and
shows the selected time interval as one faint dashed box. Routine mode does not
draw profile-derived levels; apply TradingView's native Fixed Range Volume
Profile to the same timestamps for evaluation.

Its optional Research-mode histogram uses synthetic one-minute OHLCV allocation
and is explicitly non-evaluable. It is present only to exercise the rendering
path while the exact, confirmation-aware footprint accumulator is built.

## `VP_Sparse_Visual_Fixture_v0.0.1.pine`

This is a manual visual-design fixture, not the Volume Profile selector.

It renders one already-validated Value Area edge as:

- one faint one-bin halo;
- one thin neutral center line; and
- one small `EXP VA EDGE` label.

The fixture is off by default and fails closed unless the exact configured
ticker and time window match. It does not calculate a profile, score a level,
generate an alert, or make a support/resistance claim.

Its sole purpose is to evaluate the information budget before implementing the
automated research preview specified in `RESEARCH_PREVIEW_V0_2_SPEC.md`, kept
in the local volume-profile study workspace outside this repo.
