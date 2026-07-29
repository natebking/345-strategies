#!/usr/bin/env python3
"""Synthetic tests for the Volume Profile Phase 0 acceptance gate."""

from __future__ import annotations

import csv
import contextlib
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


class Fixture:
    def __init__(
        self,
        root: Path,
        *,
        attempt_id: str = "attempt-1",
        attempt_token: int = 202,
        log_attempt_id: str | None = None,
        log_attempt_token: int | None = None,
        log_format: str = "csv",
        terminal: str = "RUN_END",
        omit_begin: bool = False,
        config_row_ticks: int = 4,
        ui_symbol: str = "CME_MINI:ES1!",
        profile_poc: int = 100,
        csv_poc: int | None = None,
        csv_attempt_token: int | None = None,
        chart_fp: int = 1111,
        profile_fp: int = 2222,
        csv_chart_fp: int | None = None,
        error_mask: int = 0,
        terminal_times: tuple[int, ...] = (3000,),
        omit_profile_fp: bool = False,
        csv_times: tuple[int, ...] = (1000, 2000, 3000),
    ) -> None:
        self.root = root
        self.manifest_path = root / "manifest.json"
        self.attempt_path = root / "attempt.json"
        self.logs_path = root / (
            "pine_logs.csv" if log_format == "csv" else "pine_logs.txt"
        )
        self.chart_csv_path = root / "chart_data.csv"
        self.ui_readback_path = root / "ui_readback.json"
        self.output_path = root / "acceptance.json"

        self.logical_run_id = "logical-run-1"
        self.logical_run_token = 101
        self.configuration_token = 303
        self.attempt_id = attempt_id
        self.attempt_token = attempt_token
        self.pine_settings = {
            "row_ticks": 4,
            "value_area_pct": 70,
        }
        self.chart_state = {
            "adjustment": "none",
            "calculation_timeframe": "1",
            "chart_timeframe": "5",
            "chart_type": "standard",
            "contract": "ESU2026",
            "display_timezone": "America/Chicago",
            "locale": "en-US",
            "session_mode": "eth",
            "session_ui_label": "Electronic trading hours",
            "symbol": "CME_MINI:ES1!",
        }

        manifest = {
            "schema": "vpx.logical-run/1",
            "experiment_id": "phase0-test",
            "logical_run_id": self.logical_run_id,
            "logical_run_token": self.logical_run_token,
            "configuration_token": self.configuration_token,
            "pine_settings": self.pine_settings,
            "pine_settings_hash": vpx_accept.canonical_hash(
                self.pine_settings
            ),
            "chart_state": self.chart_state,
            "chart_state_hash": vpx_accept.canonical_hash(self.chart_state),
            "window": {
                "warmup_start_ms": 1000,
                "measurement_start_ms": 1000,
                "measurement_end_ms": 4000,
                "expected_sessions": [
                    {
                        "session_id": "session-1",
                        "start_ms": 1000,
                        "end_ms": 4000,
                        "bar_ms": 1000,
                        "expected_count": 3,
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
        root.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        attempt = {
            "schema": "vpx.attempt/1",
            "experiment_id": "phase0-test",
            "logical_run_id": self.logical_run_id,
            "attempt_id": attempt_id,
            "attempt_token": attempt_token,
        }
        self.attempt_path.write_text(
            json.dumps(attempt),
            encoding="utf-8",
        )

        actual_ui_state = dict(self.chart_state)
        actual_ui_state["symbol"] = ui_symbol
        ui = {
            "schema": "vpx.ui-readback/1",
            "logical_run_id": self.logical_run_id,
            "attempt_id": attempt_id,
            "attempt_token": attempt_token,
            "chart_state": actual_ui_state,
            "chart_state_hash": vpx_accept.canonical_hash(actual_ui_state),
        }
        self.ui_readback_path.write_text(
            json.dumps(ui),
            encoding="utf-8",
        )

        record_attempt_id = log_attempt_id or attempt_id
        record_attempt_token = (
            log_attempt_token
            if log_attempt_token is not None
            else attempt_token
        )
        identity = {
            "logical_run_id": self.logical_run_id,
            "attempt_id": record_attempt_id,
            "attempt_token": record_attempt_token,
        }
        records: list[str] = []
        if not omit_begin:
            records.append(
                _record(
                    schema=1,
                    kind="RUN_BEGIN",
                    severity="INFO",
                    seq=1,
                    **identity,
                    logical_run_token=self.logical_run_token,
                    config_token=self.configuration_token,
                    pine_settings_hash=vpx_accept.canonical_hash(
                        self.pine_settings
                    ),
                )
            )
        if terminal == "RUN_ABORT":
            records.append(
                _record(
                    schema=1,
                    kind="RUN_ABORT",
                    severity="ERROR",
                    seq=2,
                    **identity,
                    code="LOG_CAP",
                    overflow=1,
                )
            )
        else:
            records.extend(
                [
                    _record(
                        schema=1,
                        kind="CONFIG",
                        severity="INFO",
                        seq=2,
                        **identity,
                        key="row_ticks",
                        value=config_row_ticks,
                    ),
                    _record(
                        schema=1,
                        kind="CONFIG",
                        severity="INFO",
                        seq=3,
                        **identity,
                        key="value_area_pct",
                        value=70,
                    ),
                    _record(
                        schema=1,
                        kind="PROFILE",
                        severity="INFO",
                        seq=4,
                        **identity,
                        profile_id="profile-1",
                        family="PRIOR_RTH",
                        effective_start_ms=1000,
                        effective_end_ms=4000,
                        poc_ticks=profile_poc,
                        vah_ticks=104,
                        val_ticks=96,
                    ),
                ]
            )
            trailer_fields: dict[str, object] = {
                "schema": 1,
                "kind": "RUN_END",
                "severity": "INFO",
                "seq": 5,
                **identity,
                "profiles": 1,
                "events": 0,
                "warnings": 0,
                "errors": 0,
                "overflow": 0,
                "fp_algo": "poly31-v1",
                "chart_count": 3,
                "chart_fp": chart_fp,
                "profile_count": 12,
            }
            if not omit_profile_fp:
                trailer_fields["profile_fp"] = profile_fp
            records.append(_record(**trailer_fields))

        if log_format == "csv":
            with self.logs_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.writer(handle)
                writer.writerow(["Date", "Message"])
                for index, record in enumerate(records):
                    writer.writerow(
                        [
                            f"2026-07-25T00:00:0{index}.000+00:00",
                            record,
                        ]
                    )
        else:
            self.logs_path.write_text(
                "\n".join(
                    f"2026-07-25 INFO {record}" for record in records
                )
                + "\n",
                encoding="utf-8",
            )

        actual_csv_poc = profile_poc if csv_poc is None else csv_poc
        actual_csv_attempt = (
            attempt_token
            if csv_attempt_token is None
            else csv_attempt_token
        )
        with self.chart_csv_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "time_ms",
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
            )
            actual_csv_chart_fp = (
                chart_fp if csv_chart_fp is None else csv_chart_fp
            )
            for time_ms in csv_times:
                is_terminal = time_ms in terminal_times
                writer.writerow(
                    [
                        time_ms,
                        self.logical_run_token,
                        actual_csv_attempt,
                        self.configuration_token,
                        actual_csv_poc,
                        104,
                        96,
                        error_mask,
                        3 if is_terminal else "",
                        actual_csv_chart_fp if is_terminal else "",
                        12 if is_terminal else "",
                        profile_fp if is_terminal else "",
                        1 if is_terminal else 0,
                    ]
                )

    def check(self) -> dict[str, object]:
        return vpx_accept.check_artifacts(
            manifest_path=self.manifest_path,
            attempt_path=self.attempt_path,
            logs_path=self.logs_path,
            chart_csv_path=self.chart_csv_path,
            ui_readback_path=self.ui_readback_path,
        )


class VpxAcceptanceTests(unittest.TestCase):
    def test_golden_downloaded_csv_and_plain_text(self) -> None:
        for log_format in ("csv", "text"):
            with self.subTest(log_format=log_format):
                with tempfile.TemporaryDirectory() as tmp:
                    fixture = Fixture(Path(tmp), log_format=log_format)
                    report = fixture.check()
                    self.assertTrue(report["accepted"], report["errors"])
                    self.assertEqual(report["csv_rows"], 3)
                    self.assertEqual(
                        report["source_vintage"]["chart_fp"],
                        1111,
                    )

    def test_nullable_profile_values_outside_effective_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            with fixture.chart_csv_path.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.reader(handle))
            rows.insert(
                1,
                [
                    0,
                    fixture.logical_run_token,
                    fixture.attempt_token,
                    fixture.configuration_token,
                    "",
                    "",
                    "",
                    0,
                    "",
                    "",
                    "",
                    "",
                    0,
                ],
            )
            with fixture.chart_csv_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                csv.writer(handle).writerows(rows)
            report = fixture.check()
            self.assertTrue(report["accepted"], report["errors"])

    def test_abort_is_archived_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                terminal="RUN_ABORT",
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn("RUN_ABORT", _error_codes(report))

    def test_abort_requires_explicit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp), terminal="RUN_ABORT")
            fixture.logs_path.write_text(
                fixture.logs_path.read_text(encoding="utf-8").replace(
                    "|code=LOG_CAP",
                    "",
                ),
                encoding="utf-8",
            )
            report = fixture.check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "RUN_ABORT_CODE_MISSING",
                _error_codes(report),
            )

    def test_stale_prior_attempt_log_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                log_attempt_id="attempt-old",
                log_attempt_token=201,
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn("ATTEMPT_ID_MISMATCH", _error_codes(report))

    def test_truncated_log_sequence_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(Path(tmp), omit_begin=True).check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "LOG_SEQUENCE_NOT_CONTIGUOUS",
                _error_codes(report),
            )

    def test_config_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                config_row_ticks=8,
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn("PINE_SETTINGS_MISMATCH", _error_codes(report))

    def test_ui_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                ui_symbol="CME_MINI:NQ1!",
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn("UI_CHART_STATE_MISMATCH", _error_codes(report))

    def test_csv_hidden_value_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(Path(tmp), csv_poc=101).check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "CSV_LOG_OVERLAP_MISMATCH",
                _error_codes(report),
            )

    def test_csv_attempt_token_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                csv_attempt_token=999,
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn("CSV_TOKEN_MISMATCH", _error_codes(report))

    def test_csv_source_fingerprint_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                csv_chart_fp=9999,
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "CSV_SOURCE_FINGERPRINT_MISMATCH",
                _error_codes(report),
            )

    def test_nonzero_error_mask_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                error_mask=8,
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "CSV_ERROR_MASK_NONZERO",
                _error_codes(report),
            )

    def test_missing_or_duplicate_terminal_marker_rejected(self) -> None:
        for terminal_times in ((), (2000, 3000)):
            with self.subTest(terminal_times=terminal_times):
                with tempfile.TemporaryDirectory() as tmp:
                    report = Fixture(
                        Path(tmp),
                        terminal_times=terminal_times,
                    ).check()
                    self.assertFalse(report["accepted"])
                    self.assertIn(
                        "CSV_TERMINAL_COUNT_INVALID",
                        _error_codes(report),
                    )

    def test_session_interior_gap_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                csv_times=(1000, 3000),
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "SESSION_COVERAGE_MISMATCH",
                _error_codes(report),
            )

    def test_required_source_fingerprint_rejected_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(
                Path(tmp),
                omit_profile_fp=True,
            ).check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "SOURCE_FINGERPRINT_MISSING",
                _error_codes(report),
            )

    def test_profile_requires_complete_level_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            fixture.logs_path.write_text(
                fixture.logs_path.read_text(encoding="utf-8").replace(
                    "|vah_ticks=104",
                    "",
                ),
                encoding="utf-8",
            )
            report = fixture.check()
            self.assertFalse(report["accepted"])
            self.assertIn(
                "PROFILE_FIELD_MISSING",
                _error_codes(report),
            )

    def test_same_vintage_differing_payload_is_nondeterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = Fixture(
                root / "a",
                attempt_id="attempt-a",
                attempt_token=211,
                profile_poc=100,
            ).check()
            second = Fixture(
                root / "b",
                attempt_id="attempt-b",
                attempt_token=212,
                profile_poc=101,
            ).check()
            self.assertTrue(first["accepted"], first["errors"])
            self.assertTrue(second["accepted"], second["errors"])
            comparison = vpx_accept.compare_reports(first, second)
            self.assertFalse(comparison["accepted"])
            self.assertTrue(comparison["same_vintage"])
            self.assertIn(
                "SAME_VINTAGE_NONDETERMINISTIC",
                _error_codes(comparison),
            )

    def test_changed_vintage_is_distinct_not_nondeterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = Fixture(
                root / "a",
                attempt_id="attempt-a",
                attempt_token=211,
                profile_poc=100,
            ).check()
            second = Fixture(
                root / "b",
                attempt_id="attempt-b",
                attempt_token=212,
                profile_poc=101,
                chart_fp=1112,
                profile_fp=2223,
            ).check()
            self.assertTrue(first["accepted"], first["errors"])
            self.assertTrue(second["accepted"], second["errors"])
            comparison = vpx_accept.compare_reports(first, second)
            self.assertTrue(comparison["accepted"])
            self.assertFalse(comparison["same_vintage"])
            self.assertEqual(comparison["status"], "different_vintage")

    def test_compare_requires_distinct_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Fixture(Path(tmp)).check()
            self.assertTrue(report["accepted"], report["errors"])
            comparison = vpx_accept.compare_reports(report, report)
            self.assertFalse(comparison["accepted"])
            self.assertIn(
                "COMPARE_ATTEMPT_NOT_DISTINCT",
                _error_codes(comparison),
            )

    def test_strict_record_rejects_duplicate_key(self) -> None:
        message = (
            "VPX|schema=1|kind=RUN_BEGIN|severity=INFO|seq=1|seq=2"
            "|logical_run_id=r|attempt_id=a|attempt_token=1"
        )
        with self.assertRaises(vpx_accept.ValidationError) as caught:
            vpx_accept.parse_vpx_record(message)
        self.assertEqual(caught.exception.code, "VPX_DUPLICATE_KEY")

    def test_downloaded_log_csv_preserves_structured_ticker_value(self) -> None:
        message = _record(
            schema=1,
            kind="RUN_BEGIN",
            severity="INFO",
            seq=1,
            logical_run_id="logical-run-1",
            attempt_id="attempt-1",
            attempt_token=202,
            symbol=(
                '={"settlement-as-close":false,'
                '"symbol":"CME_MINI:ESU2026"}'
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pine_logs.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Date", "Message"])
                writer.writerow(
                    ["2026-07-24T15:55:00.000-05:00", message]
                )
            records = vpx_accept.parse_log_file(path)
        self.assertEqual(
            records[0].fields["symbol"],
            '={"settlement-as-close":false,"symbol":"CME_MINI:ESU2026"}',
        )

    def test_downloaded_log_csv_rejects_unquoted_extra_columns(self) -> None:
        message = _record(
            schema=1,
            kind="RUN_BEGIN",
            severity="INFO",
            seq=1,
            logical_run_id="logical-run-1",
            attempt_id="attempt-1",
            attempt_token=202,
            symbol='={"settlement-as-close":false',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pine_logs.csv"
            path.write_text(
                "Date,Message\n"
                f"2026-07-24T15:55:00.000-05:00,{message},"
                '"symbol":"CME_MINI:ESU2026"}\n',
                encoding="utf-8",
            )
            with self.assertRaises(vpx_accept.ValidationError) as caught:
                vpx_accept.parse_log_file(path)
        self.assertEqual(caught.exception.code, "LOG_CSV_ROW_INVALID")

    def test_check_cli_writes_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            exit_code = vpx_accept.main(
                [
                    "check",
                    "--manifest",
                    str(fixture.manifest_path),
                    "--attempt",
                    str(fixture.attempt_path),
                    "--logs",
                    str(fixture.logs_path),
                    "--chart-csv",
                    str(fixture.chart_csv_path),
                    "--ui-readback",
                    str(fixture.ui_readback_path),
                    "--output",
                    str(fixture.output_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            written = json.loads(
                fixture.output_path.read_text(encoding="utf-8")
            )
            self.assertTrue(written["accepted"])

    def test_compare_cli_accepts_two_positional_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = Fixture(
                root / "a",
                attempt_id="attempt-a",
                attempt_token=211,
            ).check()
            second = Fixture(
                root / "b",
                attempt_id="attempt-b",
                attempt_token=212,
            ).check()
            first_path = root / "a.json"
            second_path = root / "b.json"
            first_path.write_text(json.dumps(first), encoding="utf-8")
            second_path.write_text(json.dumps(second), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = vpx_accept.main(
                    ["compare", str(first_path), str(second_path)]
                )
            self.assertEqual(exit_code, 0)
            comparison = json.loads(stdout.getvalue())
            self.assertEqual(comparison["status"], "reproducible")


if __name__ == "__main__":
    unittest.main()
