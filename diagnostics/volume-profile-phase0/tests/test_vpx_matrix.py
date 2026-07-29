#!/usr/bin/env python3
"""Tests for deterministic Phase 0 matrix generation and offline audit."""

from __future__ import annotations

import contextlib
import copy
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
import vpx_matrix  # noqa: E402


EXAMPLE_TEMPLATE = MODULE_DIR / "examples" / "manifest.phase0.json"
EXAMPLE_PLAN = MODULE_DIR / "examples" / "session-plan.phase0.json"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _acceptance(logical_run_id: str, *, accepted: bool = True) -> dict:
    return {
        "schema": "vpx.acceptance/1",
        "accepted": accepted,
        "logical_run_id": logical_run_id,
        "attempt_id": f"attempt-{logical_run_id}",
        "pine_settings_hash": "a" * 64,
        "chart_state_hash": "b" * 64,
        "source_vintage": {
            "fp_algo": "fold31_v1",
            "chart_count": 1,
            "chart_fp": 2,
            "profile_count": 810,
            "profile_fp": 3,
        },
        "errors": [] if accepted else [{"code": "SYNTHETIC"}],
    }


class MatrixGenerationTests(unittest.TestCase):
    def test_generation_emits_four_valid_hash_consistent_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "generated"
            report = vpx_matrix.generate_matrix(
                plan_path=EXAMPLE_PLAN,
                template_path=EXAMPLE_TEMPLATE,
                output_dir=output_dir,
            )

            self.assertTrue(report["accepted"])
            self.assertEqual(report["cell_count"], 4)
            self.assertEqual(report["created_files"], 5)
            self.assertEqual(
                [cell["display_timeframe"] for cell in report["cells"]],
                [1, 5, 15, 60],
            )
            expected_counts = {1: 405, 5: 81, 15: 27, 60: 7}
            for cell in report["cells"]:
                timeframe = cell["display_timeframe"]
                manifest_path = output_dir / cell["manifest_relpath"]
                manifest = json.loads(manifest_path.read_text("utf-8"))
                validated = vpx_accept._validate_manifest(manifest)
                self.assertEqual(
                    manifest["chart_state"]["chart_timeframe"],
                    str(timeframe),
                )
                self.assertEqual(
                    manifest["window"]["expected_sessions"][0][
                        "expected_count"
                    ],
                    expected_counts[timeframe],
                )
                self.assertEqual(
                    manifest["pine_settings_hash"],
                    vpx_accept.canonical_hash(manifest["pine_settings"]),
                )
                self.assertEqual(
                    manifest["chart_state_hash"],
                    vpx_accept.canonical_hash(manifest["chart_state"]),
                )
                self.assertEqual(
                    validated["logical_run_id"],
                    cell["logical_run_id"],
                )
                self.assertNotIn("example_only", manifest)

            hourly = report["cells"][-1]["expected_session"]
            self.assertEqual(hourly["start_ms"], 1784901600000)
            self.assertEqual(hourly["end_ms"], 1784924100000)

    def test_generation_is_idempotent_and_refuses_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "generated"
            first = vpx_matrix.generate_matrix(
                plan_path=EXAMPLE_PLAN,
                template_path=EXAMPLE_TEMPLATE,
                output_dir=output_dir,
            )
            second = vpx_matrix.generate_matrix(
                plan_path=EXAMPLE_PLAN,
                template_path=EXAMPLE_TEMPLATE,
                output_dir=output_dir,
            )
            self.assertEqual(first["cells"], second["cells"])
            self.assertEqual(second["created_files"], 0)
            self.assertEqual(second["unchanged_files"], 5)

            manifest_path = output_dir / first["cells"][0][
                "manifest_relpath"
            ]
            manifest_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(vpx_matrix.MatrixError) as raised:
                vpx_matrix.generate_matrix(
                    plan_path=EXAMPLE_PLAN,
                    template_path=EXAMPLE_TEMPLATE,
                    output_dir=output_dir,
                )
            self.assertEqual(raised.exception.code, "OUTPUT_CONFLICT")

    def test_plan_must_contain_the_locked_timeframe_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = json.loads(EXAMPLE_PLAN.read_text("utf-8"))
            plan["display_timeframes"] = [1, 5, 15]
            plan_path = Path(tmp) / "plan.json"
            _write_json(plan_path, plan)

            with self.assertRaises(vpx_matrix.MatrixError) as raised:
                vpx_matrix.generate_matrix(
                    plan_path=plan_path,
                    template_path=EXAMPLE_TEMPLATE,
                    output_dir=Path(tmp) / "generated",
                )
            self.assertEqual(
                raised.exception.code,
                "PLAN_TIMEFRAMES_INVALID",
            )

    def test_session_input_order_does_not_change_generated_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = json.loads(EXAMPLE_PLAN.read_text("utf-8"))
            second_session = copy.deepcopy(plan["sessions"][0])
            second_session["session_key"] = "esu2026-20260725"
            second_session["measurement"]["session_id"] = (
                "ESU2026-RTH-2026-07-25"
            )
            offset = 86_400_000
            second_session["warmup_start_ms"] += offset
            for key in ("start_ms", "end_ms"):
                second_session["measurement"][key] += offset
                second_session["manual_profile"][key] += offset
            plan["sessions"].append(second_session)

            first_plan = Path(tmp) / "first-plan.json"
            second_plan = Path(tmp) / "second-plan.json"
            _write_json(first_plan, plan)
            plan["sessions"].reverse()
            _write_json(second_plan, plan)
            first_output = Path(tmp) / "first"
            second_output = Path(tmp) / "second"
            first = vpx_matrix.generate_matrix(
                plan_path=first_plan,
                template_path=EXAMPLE_TEMPLATE,
                output_dir=first_output,
            )
            second = vpx_matrix.generate_matrix(
                plan_path=second_plan,
                template_path=EXAMPLE_TEMPLATE,
                output_dir=second_output,
            )

            first_cells = [
                {
                    key: value
                    for key, value in cell.items()
                    if key != "manifest_sha256"
                }
                for cell in first["cells"]
            ]
            second_cells = [
                {
                    key: value
                    for key, value in cell.items()
                    if key != "manifest_sha256"
                }
                for cell in second["cells"]
            ]
            self.assertEqual(first_cells, second_cells)


class MatrixAuditTests(unittest.TestCase):
    def _generated_index(self, root: Path) -> tuple[Path, list[str]]:
        report = vpx_matrix.generate_matrix(
            plan_path=EXAMPLE_PLAN,
            template_path=EXAMPLE_TEMPLATE,
            output_dir=root / "planned",
        )
        return Path(report["index_path"]), [
            cell["logical_run_id"] for cell in report["cells"]
        ]

    def test_audit_reconciles_acceptances_and_invariance_to_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_path, logical_run_ids = self._generated_index(root)
            evidence_root = root / "evidence"
            for logical_run_id in logical_run_ids:
                _write_json(
                    evidence_root
                    / logical_run_id
                    / "attempt-1"
                    / "acceptance.json",
                    _acceptance(logical_run_id),
                )
            _write_json(
                evidence_root / "display-timeframe-invariance.json",
                {
                    "schema": "vpx.invariance/1",
                    "accepted": True,
                    "status": "invariant",
                    "input_count": 4,
                    "mismatches": [],
                    "errors": [],
                },
            )

            report = vpx_matrix.audit_matrix(
                root=evidence_root,
                index_path=index_path,
            )

            self.assertEqual(report["status"], "healthy")
            self.assertEqual(report["summary"]["accepted_attempts"], 4)
            self.assertEqual(report["summary"]["invariant_reports"], 1)
            self.assertEqual(
                report["coverage"]["accepted_logical_runs"],
                4,
            )
            self.assertEqual(
                report["coverage"]["missing_or_unaccepted"],
                [],
            )

    def test_audit_marks_rejections_and_missing_cells_for_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_path, logical_run_ids = self._generated_index(root)
            evidence_root = root / "evidence"
            _write_json(
                evidence_root
                / logical_run_ids[0]
                / "attempt-1"
                / "acceptance.json",
                _acceptance(logical_run_ids[0], accepted=False),
            )

            report = vpx_matrix.audit_matrix(
                root=evidence_root,
                index_path=index_path,
            )

            self.assertEqual(report["status"], "attention")
            self.assertEqual(report["summary"]["rejected_attempts"], 1)
            self.assertEqual(
                len(report["coverage"]["missing_or_unaccepted"]),
                4,
            )
            self.assertEqual(
                report["coverage"]["rejected_only"],
                [logical_run_ids[0]],
            )

    def test_cli_status_tracks_healthy_and_empty_audits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty = root / "empty"
            empty.mkdir()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = vpx_matrix.main(
                    ["audit", "--root", str(empty)]
                )
            self.assertEqual(status, 1)
            self.assertEqual(
                json.loads(stdout.getvalue())["status"],
                "empty",
            )

            evidence = root / "evidence"
            _write_json(
                evidence / "run" / "attempt" / "acceptance.json",
                _acceptance("run"),
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = vpx_matrix.main(
                    ["audit", "--root", str(evidence)]
                )
            self.assertEqual(status, 0)
            self.assertEqual(
                json.loads(stdout.getvalue())["status"],
                "healthy",
            )


if __name__ == "__main__":
    unittest.main()
