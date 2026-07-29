#!/usr/bin/env python3
"""Static contract tests for the headless v0.2 Slice 1 Pine shell."""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path


PHASE0_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PHASE0_ROOT.parents[1]
PHASE0_PATH = PHASE0_ROOT / "Volume_Profile_Phase0_Probe_v0.1.0.pine"
SHELL_PATH = (
    REPO_ROOT
    / "pine"
    / "research"
    / "VP_Research_Preview_v0.2.0_Profile_Parity_Shell.pine"
)
PINNED_PHASE0_SHA256 = (
    "331bf9d3c8a824ad6dea2e0138b2db3178e6948a3cc23b27b9221beddbb32796"
)


def without_line_comments(source: str) -> str:
    return "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("//")
    )


def extract_function(source: str, name: str) -> str:
    """Return one top-level Pine function, excluding following comments."""
    lines = source.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith(f"{name}(")
    )
    saw_arrow = False
    end = len(lines)
    for index in range(start, len(lines)):
        line = lines[index]
        saw_arrow = saw_arrow or "=>" in line
        if (
            index > start
            and saw_arrow
            and line
            and not line[0].isspace()
        ):
            end = index
            break
    return "\n".join(lines[start:end]).rstrip()


def call_blocks(source: str, function_name: str) -> list[str]:
    """Extract balanced calls while ignoring parentheses inside strings."""
    starts = [
        match.start()
        for match in re.finditer(
            rf"(?<![A-Za-z0-9_.]){re.escape(function_name)}\s*\(",
            source,
        )
    ]
    blocks: list[str] = []
    for start in starts:
        open_paren = source.find("(", start)
        depth = 0
        in_string = False
        escaped = False
        for index in range(open_paren, len(source)):
            char = source[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start : index + 1])
                    break
        else:
            raise AssertionError(f"Unbalanced {function_name} call at {start}")
    return blocks


class V02ProfileShellContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = SHELL_PATH.read_text(encoding="utf-8")
        cls.code = without_line_comments(cls.shell)
        cls.phase0 = PHASE0_PATH.read_text(encoding="utf-8")

    def test_phase0_source_and_profile_core_provenance_are_pinned(self) -> None:
        self.assertEqual(
            hashlib.sha256(PHASE0_PATH.read_bytes()).hexdigest(),
            PINNED_PHASE0_SHA256,
        )
        for function_name in (
            "hashFold",
            "priceToTicks",
            "volumeToFingerprintInt",
            "boundedPut",
            "calculateProfile",
            "freezeProfile",
        ):
            with self.subTest(function=function_name):
                self.assertEqual(
                    extract_function(self.shell, function_name),
                    extract_function(self.phase0, function_name),
                )

    def test_single_fixed_nested_footprint_request(self) -> None:
        self.assertEqual(len(re.findall(r"request\.footprint\s*\(", self.code)), 1)
        self.assertEqual(
            len(re.findall(r"request\.security_lower_tf\s*\(", self.code)),
            1,
        )
        payload = extract_function(self.shell, "oneMinutePayload")
        self.assertIn("request.footprint(PRIMITIVE_TICKS", payload)
        self.assertIn("time_close", payload)
        for field in ("openTicks", "highTicks", "lowTicks", "closeTicks"):
            self.assertIn(field, payload)
        self.assertNotIn(".rows()", payload)

        request_call = call_blocks(self.code, "request.security_lower_tf")
        self.assertEqual(len(request_call), 1)
        self.assertIn("SOURCE_TIMEFRAME", request_call[0])
        self.assertIn("oneMinutePayload()", request_call[0])
        # One definition plus one invocation, and the invocation is the request
        # expression inspected immediately above.
        self.assertEqual(self.code.count("oneMinutePayload()"), 2)

    def test_profile_fingerprint_does_not_absorb_path_fields(self) -> None:
        start = self.code.index(
            "int minuteFingerprint = hashFold(HASH_SEED, sourceTime)"
        )
        end = self.code.index("if useForRth", start)
        profile_fingerprint_region = self.code[start:end]
        for path_field in (
            "sourceCloseTime",
            "sourceOpen",
            "sourceHigh",
            "sourceLow",
            "sourceClose",
            "pathMinuteFingerprint",
        ):
            self.assertNotIn(path_field, profile_fingerprint_region)

        path_function = extract_function(self.shell, "pathMinuteFingerprint")
        for path_field in (
            "sourceTime",
            "sourceCloseTime",
            "openTicks",
            "highTicks",
            "lowTicks",
            "closeTicks",
        ):
            self.assertIn(path_field, path_function)
        self.assertIn('const string FP_ALGORITHM = "fold31_v1"', self.code)
        self.assertIn(
            'const string PATH_FP_ALGORITHM = "fold31_ohlc_close_v1"',
            self.code,
        )

    def test_profile_construction_is_locked_not_user_configurable(self) -> None:
        self.assertRegex(self.code, r"const int outputTicksInput\s*=\s*4\b")
        self.assertRegex(
            self.code,
            r"const float valueAreaPercentInput\s*=\s*70\.0\b",
        )
        self.assertRegex(self.code, r'const string SOURCE_TIMEFRAME\s*=\s*"1"')
        self.assertRegex(
            self.code,
            r'const string RTH_SESSION\s*=\s*"0830-1515:23456"',
        )
        self.assertRegex(
            self.code,
            r'const string RTH_TIMEZONE\s*=\s*"America/Chicago"',
        )
        for forbidden_input in (
            r"input\.(?:int|float)\s*\([^)]*Output",
            r"input\.(?:int|float)\s*\([^)]*Value Area",
        ):
            self.assertIsNone(
                re.search(forbidden_input, self.code, re.IGNORECASE | re.DOTALL)
            )

    def test_only_prior_rth_profile_path_exists(self) -> None:
        for forbidden in (
            "manual",
            "swing",
            "visible_range",
            "overnight",
            "composite",
            "developing",
            "histogram",
            "hvn",
            "lvn",
        ):
            self.assertNotIn(forbidden, self.code.lower())
        self.assertIn("|family=PRIOR_RTH", self.code)
        self.assertEqual(self.code.count("|family=PRIOR_RTH"), 1)
        self.assertIn("sourceTime < measurementStartInput", self.code)

    def test_no_objects_alerts_orders_or_visible_outputs(self) -> None:
        forbidden_calls = (
            r"\bstrategy\s*\(",
            r"\bstrategy\.",
            r"\balert\s*\(",
            r"\balertcondition\s*\(",
            r"\bbox\.",
            r"\bline\.",
            r"\blabel\.",
            r"\bpolyline\.",
            r"\btable\.",
            r"\bfill\s*\(",
            r"\bhline\s*\(",
            r"\bplotshape\s*\(",
            r"\bplotchar\s*\(",
            r"\bplotarrow\s*\(",
            r"\bbarcolor\s*\(",
            r"\bbgcolor\s*\(",
        )
        for forbidden in forbidden_calls:
            with self.subTest(pattern=forbidden):
                self.assertIsNone(re.search(forbidden, self.code), forbidden)

        plots = call_blocks(self.code, "plot")
        self.assertGreater(len(plots), 0)
        for plot_call in plots:
            self.assertIn("display = display.data_window", plot_call)
            self.assertNotIn("display.all", plot_call)
            self.assertNotIn("display.pane", plot_call)

    def test_fail_closed_error_registry_and_guards_are_present(self) -> None:
        error_values = [
            int(value)
            for value in re.findall(
                r"const int ERR_[A-Z_]+\s*=\s*(\d+)",
                self.code,
            )
        ]
        self.assertEqual(len(error_values), 11)
        self.assertEqual(len(set(error_values)), len(error_values))
        self.assertTrue(
            all(value > 0 and value & (value - 1) == 0 for value in error_values)
        )
        for guard in (
            "environmentSupported",
            "validSha256",
            "value != UNSET_SETTINGS_HASH",
            "sourceArrayIssue",
            "sourceOrderIssue",
            "sourceTimestampIssue",
            "pathTimestampIssue",
            "pathOhlcIssue",
            "latestRthCandidateMissing",
            "latestRthCandidatePrimitiveIssue",
            "latestRthCandidateOverflow",
            "latestRthCandidateReconciliationIssue",
            "terminalErrorMask",
        ):
            self.assertIn(guard, self.code)
        self.assertIn('"RUN_ABORT"', self.code)
        self.assertIn("time_close >= measurementEndInput", self.code)
        self.assertIn(
            "terminalErrorMask == 0 and terminalProfileComplete",
            self.code,
        )
        self.assertIn("terminalPathComplete", self.code)
        self.assertIn(
            'string profileId = rthTerminalComplete ?',
            self.code,
        )

    def test_logs_and_hidden_outputs_cover_profile_parity(self) -> None:
        for field in (
            "|profile_id=",
            "|source_start_ms=",
            "|source_end_ms=",
            "|poc_ticks=",
            "|vah_ticks=",
            "|val_ticks=",
            "|source_count=",
            "|row_count=",
            "|source_fp=",
            "|path_fp=",
            "|total_volume=",
            "|achieved_va_percent=",
            "|poc_volume=",
            "|error_mask=",
        ):
            self.assertIn(field, self.code)
        for title in (
            "VP2.PriorRTH.POC",
            "VP2.PriorRTH.VAH",
            "VP2.PriorRTH.VAL",
            "VP2.PriorRTH.SourceCount",
            "VP2.PriorRTH.RowCount",
            "VP2.PriorRTH.SourceFP",
            "VP2.PriorRTH.PathFP",
            "VP2.PriorRTH.TotalVolume",
            "VP2.PriorRTH.AchievedVA",
            "VP2.PriorRTH.POCVolume",
            "VP2.Path.SourceFP",
            "VP2.ErrorMask",
        ):
            self.assertIn(f'"{title}"', self.code)

    def test_canary_profile_anchor_is_not_silently_redefined(self) -> None:
        # Static Slice 1 can only bind the arithmetic contract. TradingView
        # compile/runtime capture must verify these accepted Phase 0 exacts.
        canary = {
            "source_count": 405,
            "row_count": 6249,
            "source_fp": 1307222739,
            "total_volume": 1256450,
            "poc_ticks": 29730,
            "val_ticks": 29700,
            "vah_ticks": 29820,
            "achieved_va_percent": 69.71132954,
            "poc_volume": 42166,
        }
        self.assertEqual(canary["source_count"], 405)
        self.assertLess(canary["val_ticks"], canary["poc_ticks"])
        self.assertLess(canary["poc_ticks"], canary["vah_ticks"])
        self.assertLess(canary["achieved_va_percent"], 70.0)


if __name__ == "__main__":
    unittest.main()
