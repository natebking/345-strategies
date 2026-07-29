#!/usr/bin/env python3
"""Static cross-channel contract tests for the Phase 0 Pine probe."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PINE_PATH = ROOT / "Volume_Profile_Phase0_Probe_v0.1.0.pine"
MANIFEST_PATH = ROOT / "examples" / "manifest.phase0.json"
UI_PATH = ROOT / "examples" / "ui_readback.phase0.json"


class PineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pine = PINE_PATH.read_text(encoding="utf-8")
        cls.code = "\n".join(
            line
            for line in cls.pine.splitlines()
            if not line.lstrip().startswith("//")
        )
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.ui = json.loads(UI_PATH.read_text(encoding="utf-8"))

    def test_single_footprint_context_and_no_chart_clutter(self) -> None:
        self.assertEqual(
            len(re.findall(r"request\.footprint\(", self.code)),
            1,
        )
        self.assertEqual(
            len(re.findall(r"request\.security_lower_tf\(", self.code)),
            1,
        )
        for forbidden in (
            r"\bstrategy\s*\(",
            r"\balert\s*\(",
            r"\bline\.new\s*\(",
            r"\bbox\.new\s*\(",
            r"\blabel\.new\s*\(",
            r"\btable\.new\s*\(",
        ):
            self.assertIsNone(re.search(forbidden, self.code), forbidden)
        plot_calls = re.findall(r"^plot\([^\n]+$", self.pine, re.MULTILINE)
        self.assertEqual(len(plot_calls), 24)
        self.assertTrue(
            all("display = display.data_window" in call for call in plot_calls)
        )

    def test_config_records_match_manifest_in_lexical_order(self) -> None:
        config_keys = re.findall(
            r'"CONFIG", "\|key=([A-Za-z0-9_]+)\|value=',
            self.pine,
        )
        expected = sorted(self.manifest["pine_settings"])
        self.assertEqual(config_keys, expected)

    def test_manifest_columns_are_backed_by_data_window_plots(self) -> None:
        plot_titles = set(
            re.findall(
                r'^plot\([^\n]*, "([^"]+)"[^\n]*display = display\.data_window\)',
                self.pine,
                re.MULTILINE,
            )
        )
        csv_contract = self.manifest["chart_csv"]
        required = set(csv_contract["identity_columns"].values())
        required.update(csv_contract["value_columns"])
        self.assertTrue(required.issubset(plot_titles))

    def test_example_hashes_match_source_and_chart_state(self) -> None:
        source_hash = hashlib.sha256(PINE_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            source_hash,
            self.manifest["code"]["source_sha256"],
        )
        canonical_chart = json.dumps(
            self.manifest["chart_state"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        chart_hash = hashlib.sha256(canonical_chart).hexdigest()
        self.assertEqual(chart_hash, self.manifest["chart_state_hash"])
        self.assertEqual(self.ui["chart_state"], self.manifest["chart_state"])
        self.assertEqual(self.ui["chart_state_hash"], chart_hash)


if __name__ == "__main__":
    unittest.main()
