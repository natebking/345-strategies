#!/usr/bin/env python3
"""Focused tests for the cross-display-timeframe invariance gate."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import vpx_invariance  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(**fields: object) -> str:
    ordered = ["schema", "kind", "severity", "seq"]
    parts = ["VPX"]
    for key in ordered:
        parts.append(f"{key}={fields.pop(key)}")
    parts.extend(f"{key}={value}" for key, value in fields.items())
    return "|".join(parts)


class AcceptedCell:
    def __init__(
        self,
        root: Path,
        name: str,
        *,
        timeframe: str,
        chart_count: int,
        chart_fp: int,
        poc_ticks: int = 29730,
        configuration_token: int = 704700001,
        accepted: bool = True,
        config_value_area_percent: int = 70,
    ) -> None:
        self.logical_run_id = f"run-{name}"
        self.attempt_id = f"attempt-{name}"
        self.attempt_token = 700000000 + chart_count
        self.attempt_dir = root / name / self.attempt_id
        self.raw_dir = self.attempt_dir / "raw"
        self.raw_dir.mkdir(parents=True)
        self.acceptance_path = self.attempt_dir / "acceptance.json"
        self.manifest_path = self.attempt_dir.parent / "manifest.json"
        self.logs_path = self.raw_dir / "pine_logs.csv"
        self.pine_settings_hash = "a" * 64

        manifest = {
            "schema": "vpx.logical-run/1",
            "chart_state": {
                "chart_timeframe": timeframe,
                "calculation_timeframe": "1",
            },
        }
        self.manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        identity = {
            "logical_run_id": self.logical_run_id,
            "attempt_id": self.attempt_id,
            "attempt_token": self.attempt_token,
            "config_token": configuration_token,
        }
        records = [
            _record(
                schema=1,
                kind="RUN_BEGIN",
                severity="INFO",
                seq=1,
                **identity,
                pine_settings_hash=self.pine_settings_hash,
            ),
            _record(
                schema=1,
                kind="CONFIG",
                severity="INFO",
                seq=2,
                **identity,
                key="row_ticks",
                value=4,
            ),
            _record(
                schema=1,
                kind="CONFIG",
                severity="INFO",
                seq=3,
                **identity,
                key="value_area_percent",
                value=config_value_area_percent,
            ),
            _record(
                schema=1,
                kind="PROFILE",
                severity="INFO",
                seq=4,
                **identity,
                profile_id="RTH:20260723:B4",
                family="PRIOR_RTH",
                source_start_ms=1000,
                source_end_ms=2000,
                effective_start_ms=3000,
                effective_end_ms=4000,
                poc_ticks=poc_ticks,
                vah_ticks=29820,
                val_ticks=29700,
                source_count=405,
                source_fp=1307222739,
                row_count=6249,
                total_volume=1256450,
                achieved_va_percent="69.71132954",
                poc_volume=42166,
            ),
            _record(
                schema=1,
                kind="RUN_END",
                severity="INFO",
                seq=5,
                **identity,
                profiles=1,
                events=0,
                warnings=0,
                errors=0,
                overflow=0,
                fp_algo="fold31_v1",
                chart_count=chart_count,
                chart_fp=chart_fp,
                profile_count=810,
                profile_fp=1442736476,
            ),
        ]
        with self.logs_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Message"])
            for record in records:
                writer.writerow(["2026-07-24T15:00:00-05:00", record])

        acceptance_report = {
            "schema": "vpx.acceptance/1",
            "checker_version": "1.0.0",
            "accepted": accepted,
            "logical_run_id": self.logical_run_id,
            "logical_run_token": 123,
            "attempt_id": self.attempt_id,
            "attempt_token": self.attempt_token,
            "configuration_token": configuration_token,
            "pine_settings_hash": self.pine_settings_hash,
            "chart_state_hash": hashlib.sha256(
                timeframe.encode("ascii")
            ).hexdigest(),
            "source_vintage": {
                "fp_algo": "fold31_v1",
                "chart_count": chart_count,
                "chart_fp": chart_fp,
                "profile_count": 810,
                "profile_fp": 1442736476,
            },
            "payload_sha256": hashlib.sha256(
                name.encode("ascii")
            ).hexdigest(),
            "csv_rows": chart_count,
            "raw_sha256": {
                "manifest": _sha256(self.manifest_path),
                "pine_logs": _sha256(self.logs_path),
            },
            "errors": [] if accepted else [{"code": "SYNTHETIC"}],
        }
        self.acceptance_path.write_text(
            json.dumps(acceptance_report),
            encoding="utf-8",
        )


class InvarianceTests(unittest.TestCase):
    def test_chart_context_differences_are_explicitly_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "one-minute",
                timeframe="1",
                chart_count=405,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "hourly",
                timeframe="60",
                chart_count=7,
                chart_fp=999,
            )

            report = vpx_invariance.compare_acceptance_paths(
                [first.acceptance_path, second.acceptance_path]
            )

            self.assertTrue(report["accepted"], report)
            self.assertEqual(report["status"], "invariant")
            self.assertEqual(report["mismatches"], [])
            self.assertIn("chart_state_hash", report["allowed_differences"])
            self.assertIn(
                "source_vintage.chart_fp",
                report["allowed_differences"],
            )
            self.assertEqual(
                [
                    item["chart_context"]["chart_timeframe"]
                    for item in report["inputs"]
                ],
                ["1", "60"],
            )

    def test_profile_field_mismatch_is_rejected_with_precise_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "five-minute",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "fifteen-minute",
                timeframe="15",
                chart_count=27,
                chart_fp=222,
                poc_ticks=29731,
            )

            report = vpx_invariance.compare_acceptance_paths(
                [first.acceptance_path, second.acceptance_path]
            )

            self.assertFalse(report["accepted"])
            self.assertEqual(report["status"], "mismatch")
            fields = {
                mismatch["field"] for mismatch in report["mismatches"]
            }
            self.assertIn(
                "profiles_by_family.PRIOR_RTH[0].poc_ticks",
                fields,
            )

    def test_config_payload_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "five-minute",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "fifteen-minute",
                timeframe="15",
                chart_count=27,
                chart_fp=222,
                config_value_area_percent=68,
            )

            report = vpx_invariance.compare_acceptance_paths(
                [first.acceptance_path, second.acceptance_path]
            )

            self.assertFalse(report["accepted"])
            self.assertEqual(report["status"], "mismatch")
            self.assertIn(
                "config_sha256",
                {
                    mismatch["field"]
                    for mismatch in report["mismatches"]
                },
            )

    def test_unaccepted_input_is_rejected_before_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "accepted",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "rejected",
                timeframe="15",
                chart_count=27,
                chart_fp=222,
                accepted=False,
            )

            report = vpx_invariance.compare_acceptance_paths(
                [first.acceptance_path, second.acceptance_path]
            )

            self.assertFalse(report["accepted"])
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(
                report["errors"][0]["code"],
                "ACCEPTANCE_REQUIRED",
            )

    def test_distinct_display_timeframes_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "first",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "second",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )

            report = vpx_invariance.compare_acceptance_paths(
                [first.acceptance_path, second.acceptance_path]
            )

            self.assertFalse(report["accepted"])
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(
                report["errors"][0]["code"],
                "DISPLAY_TIMEFRAME_VARIATION_REQUIRED",
            )

    def test_tampered_log_is_rejected_by_acceptance_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "first",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "second",
                timeframe="15",
                chart_count=27,
                chart_fp=222,
            )
            second.logs_path.write_text("tampered\n", encoding="utf-8")

            report = vpx_invariance.compare_acceptance_paths(
                [first.acceptance_path, second.acceptance_path]
            )

            self.assertFalse(report["accepted"])
            self.assertEqual(
                report["errors"][0]["code"],
                "EVIDENCE_HASH_MISMATCH",
            )

    def test_cli_exit_status_tracks_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = AcceptedCell(
                Path(tmp),
                "first",
                timeframe="5",
                chart_count=81,
                chart_fp=111,
            )
            second = AcceptedCell(
                Path(tmp),
                "second",
                timeframe="15",
                chart_count=27,
                chart_fp=222,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = vpx_invariance.main(
                    [
                        str(first.acceptance_path),
                        str(second.acceptance_path),
                    ]
                )

            self.assertEqual(status, 0)
            self.assertTrue(json.loads(output.getvalue())["accepted"])

            mismatch = AcceptedCell(
                Path(tmp),
                "mismatch",
                timeframe="60",
                chart_count=7,
                chart_fp=333,
                poc_ticks=1,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = vpx_invariance.main(
                    [
                        str(first.acceptance_path),
                        str(mismatch.acceptance_path),
                    ]
                )
            self.assertEqual(status, 1)
            self.assertFalse(json.loads(output.getvalue())["accepted"])


if __name__ == "__main__":
    unittest.main()
