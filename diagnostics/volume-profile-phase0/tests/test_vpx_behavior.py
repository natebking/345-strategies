#!/usr/bin/env python3
"""Focused tests for the fail-closed Phase 0 behavior evaluator."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import vpx_accept  # noqa: E402
import vpx_behavior  # noqa: E402


def _record(**fields: object) -> str:
    ordered = ["schema", "kind", "severity", "seq"]
    parts = ["VPX"]
    for key in ordered:
        parts.append(f"{key}={fields.pop(key)}")
    parts.extend(f"{key}={value}" for key, value in fields.items())
    return "|".join(parts)


def _error_codes(report: dict[str, object]) -> set[str]:
    return {
        str(error["code"])
        for error in report.get("errors", [])
        if isinstance(error, dict) and "code" in error
    }


DEFAULT_BARS = (
    (130, 131, 125, 126),
    (126, 127, 119, 121),
    (121, 130, 120, 128),
    (128, 129, 108, 109),
    (108, 109, 101, 102),
    (102, 103, 96, 97),
    (97, 99, 94, 94),
    (94, 95, 92, 93),
    (93, 96, 91, 95),
    (95, 97, 90, 96),
)


class BehaviorFixture:
    """Create a fully accepted, hash-bound one-minute attempt."""

    def __init__(
        self,
        root: Path,
        *,
        bars: tuple[tuple[int, int, int, int], ...] = DEFAULT_BARS,
        chart_timeframe: str = "1",
        include_ohlc: bool = True,
    ) -> None:
        self.logical_run_id = "behavior-run-1"
        self.logical_run_token = 101
        self.configuration_token = 303
        self.attempt_id = "behavior-attempt-1"
        self.attempt_token = 202
        self.start_ms = 60_000
        self.end_ms = self.start_ms + len(bars) * 60_000

        self.logical_dir = root / self.logical_run_id
        self.attempt_dir = self.logical_dir / self.attempt_id
        self.raw_dir = self.attempt_dir / "raw"
        self.raw_dir.mkdir(parents=True)
        self.manifest_path = self.logical_dir / "manifest.json"
        self.attempt_path = self.attempt_dir / "attempt.json"
        self.ui_path = self.attempt_dir / "ui_readback.json"
        self.logs_path = self.raw_dir / "pine_logs.csv"
        self.chart_path = self.raw_dir / "chart_data.csv"
        self.acceptance_path = self.attempt_dir / "acceptance.json"
        self.output_path = self.attempt_dir / "behavior.json"

        pine_settings = {
            "output_ticks": 4,
            "value_area_pct": 70,
        }
        chart_state = {
            "adjustment": "none",
            "calculation_timeframe": "1",
            "chart_timeframe": chart_timeframe,
            "chart_type": "standard",
            "contract": "ESU2026",
            "display_timezone": "America/Chicago",
            "locale": "en-US",
            "session_mode": "eth",
            "session_ui_label": "Electronic trading hours",
            "symbol": "CME_MINI:ESU2026",
        }
        manifest = {
            "schema": "vpx.logical-run/1",
            "experiment_id": "phase0-behavior-test",
            "logical_run_id": self.logical_run_id,
            "logical_run_token": self.logical_run_token,
            "configuration_token": self.configuration_token,
            "pine_settings": pine_settings,
            "pine_settings_hash": vpx_accept.canonical_hash(pine_settings),
            "chart_state": chart_state,
            "chart_state_hash": vpx_accept.canonical_hash(chart_state),
            "market": {"minimum_tick": 1},
            "window": {
                "warmup_start_ms": 0,
                "measurement_start_ms": self.start_ms,
                "measurement_end_ms": self.end_ms,
                "expected_sessions": [
                    {
                        "session_id": "RTH-test",
                        "start_ms": self.start_ms,
                        "end_ms": self.end_ms,
                        "bar_ms": 60_000,
                        "expected_count": len(bars),
                    }
                ],
            },
            "chart_csv": {
                "time_column": "time_ms",
                "time_format": "unix_ms",
                "identity_columns": {
                    "logical_run_token": "VPX.Run",
                    "attempt_token": "VPX.Attempt",
                    "configuration_token": "VPX.Config",
                },
                "value_columns": {
                    "VPX.PriorRTH.POC": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.PriorRTH.VAH": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.PriorRTH.VAL": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.ErrorMask": {
                        "nullable": False,
                        "integral": True,
                    },
                    "VPX.ChartCount": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.ChartFP": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.ProfileCount": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.ProfileFP": {
                        "nullable": True,
                        "integral": True,
                    },
                    "VPX.Terminal": {
                        "nullable": False,
                        "integral": True,
                    },
                },
                "overlap_groups": [
                    {
                        "record_kind": "PROFILE",
                        "match": {"family": "PRIOR_RTH"},
                        "start_field": "effective_start_ms",
                        "end_field": "effective_end_ms",
                        "fields": {
                            "poc_ticks": "VPX.PriorRTH.POC",
                            "vah_ticks": "VPX.PriorRTH.VAH",
                            "val_ticks": "VPX.PriorRTH.VAL",
                        },
                    }
                ],
                "source_columns": {
                    "chart_count": "VPX.ChartCount",
                    "chart_fp": "VPX.ChartFP",
                    "profile_count": "VPX.ProfileCount",
                    "profile_fp": "VPX.ProfileFP",
                    "error_mask": "VPX.ErrorMask",
                },
                "terminal_column": "VPX.Terminal",
                "na_values": ["", "NaN"],
            },
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.attempt_path.write_text(
            json.dumps(
                {
                    "schema": "vpx.attempt/1",
                    "experiment_id": "phase0-behavior-test",
                    "logical_run_id": self.logical_run_id,
                    "attempt_id": self.attempt_id,
                    "attempt_token": self.attempt_token,
                }
            ),
            encoding="utf-8",
        )
        self.ui_path.write_text(
            json.dumps(
                {
                    "schema": "vpx.ui-readback/1",
                    "logical_run_id": self.logical_run_id,
                    "attempt_id": self.attempt_id,
                    "attempt_token": self.attempt_token,
                    "chart_state": chart_state,
                    "chart_state_hash": vpx_accept.canonical_hash(chart_state),
                }
            ),
            encoding="utf-8",
        )

        identity = {
            "logical_run_id": self.logical_run_id,
            "attempt_id": self.attempt_id,
            "attempt_token": self.attempt_token,
        }
        records = [
            _record(
                schema=1,
                kind="RUN_BEGIN",
                severity="INFO",
                seq=1,
                **identity,
                logical_run_token=self.logical_run_token,
                config_token=self.configuration_token,
                pine_settings_hash=vpx_accept.canonical_hash(pine_settings),
            ),
            _record(
                schema=1,
                kind="CONFIG",
                severity="INFO",
                seq=2,
                **identity,
                config_token=self.configuration_token,
                key="output_ticks",
                value=4,
            ),
            _record(
                schema=1,
                kind="CONFIG",
                severity="INFO",
                seq=3,
                **identity,
                config_token=self.configuration_token,
                key="value_area_pct",
                value=70,
            ),
            _record(
                schema=1,
                kind="PROFILE",
                severity="INFO",
                seq=4,
                **identity,
                config_token=self.configuration_token,
                profile_id="RTH:test:B4",
                family="PRIOR_RTH",
                source_start_ms=-600_000,
                source_end_ms=0,
                effective_start_ms=self.start_ms,
                effective_end_ms=self.end_ms,
                poc_ticks=100,
                vah_ticks=120,
                val_ticks=80,
                complete=1,
            ),
            _record(
                schema=1,
                kind="RUN_END",
                severity="INFO",
                seq=5,
                **identity,
                config_token=self.configuration_token,
                profiles=1,
                events=0,
                warnings=0,
                errors=0,
                overflow=0,
                fp_algo="fold31_v1",
                chart_count=len(bars),
                chart_fp=1111,
                profile_count=len(bars) * 4,
                profile_fp=2222,
                error_mask=0,
            ),
        ]
        with self.logs_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Message"])
            for record in records:
                writer.writerow(["2026-07-25T00:00:00.000+00:00", record])

        hidden_columns = [
            "VPX.Run",
            "VPX.Attempt",
            "VPX.Config",
            "VPX.PriorRTH.POC",
            "VPX.PriorRTH.VAH",
            "VPX.PriorRTH.VAL",
            "VPX.ErrorMask",
            "VPX.ChartCount",
            "VPX.ChartFP",
            "VPX.ProfileCount",
            "VPX.ProfileFP",
            "VPX.Terminal",
        ]
        header = ["time_ms"]
        if include_ohlc:
            header.extend(["open", "high", "low", "close"])
        header.extend(hidden_columns)
        with self.chart_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            for index, ohlc in enumerate(bars):
                terminal = index == len(bars) - 1
                row: list[object] = [self.start_ms + index * 60_000]
                if include_ohlc:
                    row.extend(ohlc)
                row.extend(
                    [
                        self.logical_run_token,
                        self.attempt_token,
                        self.configuration_token,
                        100,
                        120,
                        80,
                        0,
                        len(bars) if terminal else "",
                        1111 if terminal else "",
                        len(bars) * 4 if terminal else "",
                        2222 if terminal else "",
                        1 if terminal else 0,
                    ]
                )
                writer.writerow(row)

        acceptance = vpx_accept.check_artifacts(
            manifest_path=self.manifest_path,
            attempt_path=self.attempt_path,
            logs_path=self.logs_path,
            chart_csv_path=self.chart_path,
            ui_readback_path=self.ui_path,
        )
        if not acceptance["accepted"]:
            raise AssertionError(acceptance)
        self.acceptance_path.write_text(
            json.dumps(acceptance, sort_keys=True),
            encoding="utf-8",
        )

    def evaluate(self, **kwargs: object) -> dict[str, object]:
        return vpx_behavior.evaluate_behavior(
            acceptance_path=self.acceptance_path,
            chart_csv_path=self.chart_path,
            **kwargs,
        )


class BehaviorTests(unittest.TestCase):
    def test_directional_touch_excursion_break_and_censoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp))
            report = fixture.evaluate(
                horizons_minutes=(3, 5),
                reaction_threshold_ticks=8,
                break_distance_ticks=2,
                break_consecutive_closes=2,
            )

            self.assertTrue(report["accepted"], report)
            levels = {
                level["level_type"]: level
                for level in report["levels"]
            }
            self.assertEqual(
                levels["VAH"]["touch"]["entry_direction"],
                "from_above",
            )
            self.assertEqual(
                levels["VAH"]["horizons"][0]["outcome_state"],
                "reaction_first",
            )
            self.assertEqual(
                levels["POC"]["touch"]["bar_index"],
                4,
            )
            poc_five = levels["POC"]["horizons"][1]
            self.assertEqual(poc_five["penetration_ticks"], 11)
            self.assertEqual(poc_five["far_edge_breach_ticks"], 7)
            self.assertEqual(poc_five["mfe_ticks"], 1)
            self.assertEqual(poc_five["mae_ticks"], 11)
            self.assertEqual(poc_five["break_state"], "confirmed")
            self.assertEqual(poc_five["outcome_state"], "break_first")
            self.assertEqual(
                poc_five["closes_beyond_break_threshold"]["max_consecutive"],
                3,
            )
            self.assertEqual(levels["VAL"]["touch"]["status"], "not_touched")
            self.assertTrue(
                levels["VAL"]["touch_search_censoring"]["right_censored"]
            )
            self.assertTrue(
                report["policy"]["thresholds_preregistered_not_sample_optimized"]
            )

    def test_late_touch_right_censors_long_horizon(self) -> None:
        bars = (
            (130, 131, 125, 126),
            (126, 127, 125, 126),
            (126, 127, 125, 126),
            (126, 127, 125, 126),
            (126, 127, 119, 121),
        )
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp), bars=bars)
            report = fixture.evaluate(horizons_minutes=(5,))
            vah = next(
                level
                for level in report["levels"]
                if level["level_type"] == "VAH"
            )
            horizon = vah["horizons"][0]
            self.assertTrue(horizon["right_censored"])
            self.assertEqual(horizon["censoring_reason"], "session_end")
            self.assertEqual(
                horizon["observed_bars_including_touch_bar"],
                1,
            )
            self.assertIsNone(horizon["mfe_ticks"])
            self.assertIsNone(horizon["mae_ticks"])

    def test_tampered_chart_csv_is_rejected_before_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp))
            fixture.chart_path.write_text(
                fixture.chart_path.read_text(encoding="utf-8").replace(
                    ",130,131,125,126,",
                    ",130,132,125,126,",
                    1,
                ),
                encoding="utf-8",
            )
            report = fixture.evaluate()
            self.assertFalse(report["accepted"])
            self.assertIn("EVIDENCE_HASH_MISMATCH", _error_codes(report))
            self.assertEqual(report["levels"], [])

    def test_tampered_acceptance_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp))
            acceptance = json.loads(
                fixture.acceptance_path.read_text(encoding="utf-8")
            )
            acceptance["record_counts"]["events"] = 99
            fixture.acceptance_path.write_text(
                json.dumps(acceptance),
                encoding="utf-8",
            )
            report = fixture.evaluate()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "ACCEPTANCE_REPORT_TAMPERED",
                _error_codes(report),
            )

    def test_unaccepted_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp))
            acceptance = json.loads(
                fixture.acceptance_path.read_text(encoding="utf-8")
            )
            acceptance["accepted"] = False
            fixture.acceptance_path.write_text(
                json.dumps(acceptance),
                encoding="utf-8",
            )
            report = fixture.evaluate()
            self.assertFalse(report["accepted"])
            self.assertIn("ACCEPTANCE_REQUIRED", _error_codes(report))

    def test_non_one_minute_chart_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(
                Path(tmp),
                chart_timeframe="5",
            )
            report = fixture.evaluate()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "ONE_MINUTE_CHART_REQUIRED",
                _error_codes(report),
            )

    def test_missing_ohlc_is_rejected_even_when_acceptance_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp), include_ohlc=False)
            report = fixture.evaluate()
            self.assertFalse(report["accepted"])
            self.assertIn("OHLC_COLUMN_MISSING", _error_codes(report))

    def test_cli_writes_report_and_exit_status_tracks_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = BehaviorFixture(Path(tmp))
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = vpx_behavior.main(
                    [
                        "--acceptance",
                        str(fixture.acceptance_path),
                        "--chart-csv",
                        str(fixture.chart_path),
                        "--horizons-minutes",
                        "3,5",
                        "--output",
                        str(fixture.output_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            written = json.loads(
                fixture.output_path.read_text(encoding="utf-8")
            )
            self.assertTrue(written["accepted"])
            self.assertEqual(
                written["policy"]["horizons_minutes"],
                [3, 5],
            )


if __name__ == "__main__":
    unittest.main()
