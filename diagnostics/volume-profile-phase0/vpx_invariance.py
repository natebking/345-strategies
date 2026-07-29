#!/usr/bin/env python3
"""Cross-display-timeframe invariance gate for accepted Phase 0 runs.

The Phase 0 acceptance report intentionally stays compact and therefore does
not embed PROFILE records.  This comparator accepts two or more
``acceptance.json`` paths, resolves each report's sibling manifest and Pine-log
artifact, verifies both against the hashes recorded by the acceptance gate,
and then compares only construction/projection evidence that should be
display-timeframe invariant.

Chart state hashes, display chart timeframes, chart bar counts, and chart
fingerprints are retained as context but deliberately excluded from the
invariance decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import vpx_accept


COMPARATOR_VERSION = "1.0.0"
ACCEPTANCE_SCHEMA = "vpx.acceptance/1"
REPORT_SCHEMA = "vpx.invariance/1"

PROFILE_ENVELOPE_FIELDS = frozenset(
    {
        "schema",
        "kind",
        "severity",
        "seq",
        "logical_run_id",
        "attempt_id",
        "attempt_token",
        "config_token",
    }
)

ALLOWED_DIFFERENCES = (
    "logical_run_id",
    "logical_run_token",
    "attempt_id",
    "attempt_token",
    "chart_state_hash",
    "manifest.chart_state.chart_timeframe",
    "source_vintage.chart_count",
    "source_vintage.chart_fp",
    "payload_sha256",
    "csv_rows",
    "raw_sha256",
)


class InvarianceError(Exception):
    """A stable, machine-readable comparator rejection."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass(frozen=True)
class Evidence:
    """The invariant evidence and allowed chart context for one run."""

    acceptance_path: Path
    logical_run_id: str
    attempt_id: str
    pine_settings_hash: str
    configuration_token: int
    config_sha256: str
    fp_algo: str
    profile_count: int
    profile_fp: int
    profiles_by_family: Mapping[str, tuple[Mapping[str, str], ...]]
    chart_timeframe: str | None
    chart_state_hash: str
    chart_count: int
    chart_fp: int

    def invariant_projection(self) -> dict[str, Any]:
        return {
            "pine_settings_hash": self.pine_settings_hash,
            "configuration_token": self.configuration_token,
            "config_sha256": self.config_sha256,
            "source_vintage": {
                "fp_algo": self.fp_algo,
                "profile_count": self.profile_count,
                "profile_fp": self.profile_fp,
            },
            "profiles_by_family": {
                family: [dict(profile) for profile in profiles]
                for family, profiles in sorted(
                    self.profiles_by_family.items()
                )
            },
        }

    def input_summary(self) -> dict[str, Any]:
        return {
            "acceptance_path": str(self.acceptance_path),
            "logical_run_id": self.logical_run_id,
            "attempt_id": self.attempt_id,
            "chart_context": {
                "chart_timeframe": self.chart_timeframe,
                "chart_state_hash": self.chart_state_hash,
                "chart_count": self.chart_count,
                "chart_fp": self.chart_fp,
            },
        }


def _fail(code: str, message: str, **details: Any) -> None:
    raise InvarianceError(code, message, **details)


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        _fail(
            "CANONICAL_JSON_INVALID",
            "Evidence cannot be represented as canonical JSON",
            reason=str(exc),
        )
    return encoded.encode("ascii")


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except OSError as exc:
        _fail(
            "EVIDENCE_READ_ERROR",
            "Evidence file could not be read",
            path=str(path),
            reason=str(exc),
        )
    return digest.hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        _fail(
            "FILE_MISSING",
            f"{label} file is missing",
            path=str(path),
        )
    except (OSError, json.JSONDecodeError) as exc:
        _fail(
            "JSON_INVALID",
            f"{label} is not valid readable JSON",
            path=str(path),
            reason=str(exc),
        )
    if not isinstance(value, dict):
        _fail(
            "JSON_ROOT_INVALID",
            f"{label} JSON root must be an object",
            path=str(path),
        )
    return value


def _require_string(
    mapping: Mapping[str, Any],
    field: str,
    *,
    path: Path,
) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        _fail(
            "ACCEPTANCE_FIELD_INVALID",
            f"Accepted report field {field!r} must be a non-empty string",
            path=str(path),
            field=field,
        )
    return value


def _require_int(
    mapping: Mapping[str, Any],
    field: str,
    *,
    path: Path,
) -> int:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(
            "ACCEPTANCE_FIELD_INVALID",
            f"Accepted report field {field!r} must be an integer",
            path=str(path),
            field=field,
        )
    return value


def _expected_raw_hash(
    acceptance: Mapping[str, Any],
    label: str,
    acceptance_path: Path,
) -> str:
    raw_hashes = acceptance.get("raw_sha256")
    if not isinstance(raw_hashes, Mapping):
        _fail(
            "RAW_HASHES_MISSING",
            "Accepted report lacks raw artifact hashes",
            path=str(acceptance_path),
        )
    expected = raw_hashes.get(label)
    if not isinstance(expected, str) or len(expected) != 64:
        _fail(
            "RAW_HASH_MISSING",
            "Accepted report lacks a valid raw artifact hash",
            path=str(acceptance_path),
            artifact=label,
        )
    return expected


def _resolve_hashed_artifact(
    *,
    acceptance_path: Path,
    acceptance: Mapping[str, Any],
    label: str,
    candidates: Sequence[Path],
) -> Path:
    expected = _expected_raw_hash(acceptance, label, acceptance_path)
    existing: list[Path] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        existing.append(candidate)
        if _sha256_file(candidate) == expected:
            return candidate
    if not existing:
        _fail(
            "EVIDENCE_MISSING",
            "Hashed evidence artifact could not be resolved",
            acceptance_path=str(acceptance_path),
            artifact=label,
            candidates=[str(candidate) for candidate in candidates],
        )
    _fail(
        "EVIDENCE_HASH_MISMATCH",
        "Resolved evidence artifact does not match its acceptance hash",
        acceptance_path=str(acceptance_path),
        artifact=label,
        expected_sha256=expected,
        candidates=[str(candidate) for candidate in existing],
    )


def _select_records(
    records: Sequence[vpx_accept.VpxRecord],
    acceptance: Mapping[str, Any],
    acceptance_path: Path,
) -> list[vpx_accept.VpxRecord]:
    logical_run_id = _require_string(
        acceptance,
        "logical_run_id",
        path=acceptance_path,
    )
    attempt_id = _require_string(
        acceptance,
        "attempt_id",
        path=acceptance_path,
    )
    attempt_token = _require_int(
        acceptance,
        "attempt_token",
        path=acceptance_path,
    )
    selected = [
        record
        for record in records
        if record.fields.get("logical_run_id") == logical_run_id
        and record.fields.get("attempt_id") == attempt_id
        and record.fields.get("attempt_token") == str(attempt_token)
    ]
    if not selected:
        _fail(
            "ATTEMPT_RECORDS_MISSING",
            "Pine-log evidence contains no records for the accepted attempt",
            path=str(acceptance_path),
            logical_run_id=logical_run_id,
            attempt_id=attempt_id,
            attempt_token=attempt_token,
        )
    return selected


def _extract_config(
    records: Sequence[vpx_accept.VpxRecord],
    acceptance_path: Path,
) -> tuple[dict[str, str], str]:
    config: dict[str, str] = {}
    for record in records:
        if record.kind != "CONFIG":
            continue
        key = record.fields.get("key")
        value = record.fields.get("value")
        if not key or value is None:
            _fail(
                "CONFIG_RECORD_INVALID",
                "CONFIG evidence must contain key and value fields",
                path=str(acceptance_path),
                seq=record.seq,
            )
        if key in config:
            _fail(
                "CONFIG_KEY_DUPLICATE",
                "CONFIG evidence contains a duplicate key",
                path=str(acceptance_path),
                key=key,
            )
        config[key] = value
    if not config:
        _fail(
            "CONFIG_EVIDENCE_MISSING",
            "Accepted Pine-log evidence contains no CONFIG records",
            path=str(acceptance_path),
        )
    ordered = dict(sorted(config.items()))
    return ordered, _canonical_hash(ordered)


def _extract_profiles(
    records: Sequence[vpx_accept.VpxRecord],
    acceptance_path: Path,
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for record in records:
        if record.kind != "PROFILE":
            continue
        family = record.fields.get("family")
        if not family:
            _fail(
                "PROFILE_FAMILY_MISSING",
                "PROFILE evidence lacks a family",
                path=str(acceptance_path),
                seq=record.seq,
            )
        payload = {
            key: value
            for key, value in record.fields.items()
            if key not in PROFILE_ENVELOPE_FIELDS
        }
        grouped.setdefault(family, []).append(dict(sorted(payload.items())))
    if not grouped:
        _fail(
            "PROFILE_EVIDENCE_MISSING",
            "Accepted Pine-log evidence contains no PROFILE records",
            path=str(acceptance_path),
        )
    return {
        family: tuple(
            sorted(
                profiles,
                key=lambda profile: _canonical_json_bytes(profile),
            )
        )
        for family, profiles in sorted(grouped.items())
    }


def _extract_evidence(acceptance_path: Path) -> Evidence:
    acceptance_path = acceptance_path.resolve()
    acceptance = _load_object(acceptance_path, "acceptance report")
    if acceptance.get("schema") != ACCEPTANCE_SCHEMA:
        _fail(
            "ACCEPTANCE_SCHEMA_UNSUPPORTED",
            "Input is not a supported acceptance report",
            path=str(acceptance_path),
            schema=acceptance.get("schema"),
        )
    if acceptance.get("accepted") is not True:
        _fail(
            "ACCEPTANCE_REQUIRED",
            "Every input report must be accepted before invariance comparison",
            path=str(acceptance_path),
        )

    pine_logs_path = _resolve_hashed_artifact(
        acceptance_path=acceptance_path,
        acceptance=acceptance,
        label="pine_logs",
        candidates=(
            acceptance_path.parent / "raw" / "pine_logs.csv",
            acceptance_path.parent / "raw" / "pine_logs.txt",
            acceptance_path.parent / "pine_logs.csv",
            acceptance_path.parent / "pine_logs.txt",
        ),
    )
    manifest_path = _resolve_hashed_artifact(
        acceptance_path=acceptance_path,
        acceptance=acceptance,
        label="manifest",
        candidates=(
            acceptance_path.parent / "manifest.json",
            acceptance_path.parent.parent / "manifest.json",
        ),
    )
    manifest = _load_object(manifest_path, "logical-run manifest")
    chart_state = manifest.get("chart_state")
    if not isinstance(chart_state, Mapping):
        _fail(
            "MANIFEST_CHART_STATE_INVALID",
            "Resolved manifest lacks a chart_state object",
            path=str(manifest_path),
        )
    chart_timeframe_value = chart_state.get("chart_timeframe")
    if (
        isinstance(chart_timeframe_value, bool)
        or not isinstance(chart_timeframe_value, (str, int))
        or not str(chart_timeframe_value)
    ):
        _fail(
            "MANIFEST_CHART_TIMEFRAME_INVALID",
            "Resolved manifest lacks a valid display chart timeframe",
            path=str(manifest_path),
        )
    chart_timeframe = str(chart_timeframe_value)

    try:
        all_records = vpx_accept.parse_log_file(pine_logs_path)
    except vpx_accept.ValidationError as exc:
        _fail(
            "PINE_LOG_INVALID",
            "Hashed Pine-log evidence could not be parsed",
            path=str(pine_logs_path),
            cause=exc.as_dict(),
        )
    records = _select_records(all_records, acceptance, acceptance_path)

    run_begin = [record for record in records if record.kind == "RUN_BEGIN"]
    if len(run_begin) != 1:
        _fail(
            "RUN_BEGIN_INVALID",
            "Accepted attempt must have exactly one RUN_BEGIN record",
            path=str(acceptance_path),
            actual=len(run_begin),
        )
    pine_settings_hash = _require_string(
        acceptance,
        "pine_settings_hash",
        path=acceptance_path,
    )
    if run_begin[0].fields.get("pine_settings_hash") != pine_settings_hash:
        _fail(
            "PINE_SETTINGS_HASH_MISMATCH",
            "RUN_BEGIN Pine settings hash differs from the acceptance report",
            path=str(acceptance_path),
        )
    configuration_token = _require_int(
        acceptance,
        "configuration_token",
        path=acceptance_path,
    )
    if run_begin[0].fields.get("config_token") != str(configuration_token):
        _fail(
            "CONFIGURATION_TOKEN_MISMATCH",
            "RUN_BEGIN configuration token differs from the acceptance report",
            path=str(acceptance_path),
        )

    _, config_sha256 = _extract_config(records, acceptance_path)
    profiles_by_family = _extract_profiles(records, acceptance_path)

    source_vintage = acceptance.get("source_vintage")
    if not isinstance(source_vintage, Mapping):
        _fail(
            "SOURCE_VINTAGE_MISSING",
            "Accepted report lacks source-vintage evidence",
            path=str(acceptance_path),
        )
    fp_algo = source_vintage.get("fp_algo")
    if not isinstance(fp_algo, str) or not fp_algo:
        _fail(
            "SOURCE_VINTAGE_INVALID",
            "Source fingerprint algorithm must be a non-empty string",
            path=str(acceptance_path),
            field="fp_algo",
        )
    profile_count = _require_int(
        source_vintage,
        "profile_count",
        path=acceptance_path,
    )
    profile_fp = _require_int(
        source_vintage,
        "profile_fp",
        path=acceptance_path,
    )
    chart_count = _require_int(
        source_vintage,
        "chart_count",
        path=acceptance_path,
    )
    chart_fp = _require_int(
        source_vintage,
        "chart_fp",
        path=acceptance_path,
    )

    return Evidence(
        acceptance_path=acceptance_path,
        logical_run_id=_require_string(
            acceptance,
            "logical_run_id",
            path=acceptance_path,
        ),
        attempt_id=_require_string(
            acceptance,
            "attempt_id",
            path=acceptance_path,
        ),
        pine_settings_hash=pine_settings_hash,
        configuration_token=configuration_token,
        config_sha256=config_sha256,
        fp_algo=fp_algo,
        profile_count=profile_count,
        profile_fp=profile_fp,
        profiles_by_family=profiles_by_family,
        chart_timeframe=chart_timeframe,
        chart_state_hash=_require_string(
            acceptance,
            "chart_state_hash",
            path=acceptance_path,
        ),
        chart_count=chart_count,
        chart_fp=chart_fp,
    )


def _append_differences(
    mismatches: list[dict[str, Any]],
    expected: Any,
    actual: Any,
    *,
    field: str,
    baseline_path: Path,
    compared_path: Path,
) -> None:
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        for key in sorted(set(expected) | set(actual)):
            child = f"{field}.{key}" if field else str(key)
            if key not in expected:
                mismatches.append(
                    {
                        "field": child,
                        "baseline_path": str(baseline_path),
                        "compared_path": str(compared_path),
                        "expected": None,
                        "actual": actual[key],
                        "reason": "unexpected_field",
                    }
                )
            elif key not in actual:
                mismatches.append(
                    {
                        "field": child,
                        "baseline_path": str(baseline_path),
                        "compared_path": str(compared_path),
                        "expected": expected[key],
                        "actual": None,
                        "reason": "missing_field",
                    }
                )
            else:
                _append_differences(
                    mismatches,
                    expected[key],
                    actual[key],
                    field=child,
                    baseline_path=baseline_path,
                    compared_path=compared_path,
                )
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            mismatches.append(
                {
                    "field": field,
                    "baseline_path": str(baseline_path),
                    "compared_path": str(compared_path),
                    "expected_count": len(expected),
                    "actual_count": len(actual),
                    "reason": "list_length",
                }
            )
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual)
        ):
            _append_differences(
                mismatches,
                expected_item,
                actual_item,
                field=f"{field}[{index}]",
                baseline_path=baseline_path,
                compared_path=compared_path,
            )
        return
    if expected != actual:
        mismatches.append(
            {
                "field": field,
                "baseline_path": str(baseline_path),
                "compared_path": str(compared_path),
                "expected": expected,
                "actual": actual,
                "reason": "value",
            }
        )


def _base_report(paths: Sequence[Path]) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "comparator_version": COMPARATOR_VERSION,
        "accepted": False,
        "status": "rejected",
        "input_count": len(paths),
        "inputs": [],
        "allowed_differences": list(ALLOWED_DIFFERENCES),
        "invariant_projection": None,
        "mismatches": [],
        "errors": [],
    }


def compare_acceptance_paths(
    acceptance_paths: Sequence[str | os.PathLike[str]],
) -> dict[str, Any]:
    """Compare invariant profile evidence from two or more accepted reports."""

    paths = [Path(path) for path in acceptance_paths]
    result = _base_report(paths)
    if len(paths) < 2:
        result["errors"].append(
            {
                "code": "INPUT_COUNT_INVALID",
                "message": "At least two acceptance reports are required",
                "details": {"actual": len(paths), "minimum": 2},
            }
        )
        return result

    evidence: list[Evidence] = []
    try:
        for path in paths:
            evidence.append(_extract_evidence(path))
    except InvarianceError as exc:
        result["errors"].append(exc.as_dict())
        return result

    result["inputs"] = [item.input_summary() for item in evidence]
    chart_timeframes = {item.chart_timeframe for item in evidence}
    if len(chart_timeframes) < 2:
        result["errors"].append(
            {
                "code": "DISPLAY_TIMEFRAME_VARIATION_REQUIRED",
                "message": (
                    "Cross-display-timeframe comparison requires at least "
                    "two distinct display chart timeframes"
                ),
                "details": {
                    "chart_timeframes": sorted(chart_timeframes),
                },
            }
        )
        return result

    baseline = evidence[0]
    baseline_projection = baseline.invariant_projection()
    result["invariant_projection"] = baseline_projection
    mismatches: list[dict[str, Any]] = []
    for compared in evidence[1:]:
        _append_differences(
            mismatches,
            baseline_projection,
            compared.invariant_projection(),
            field="",
            baseline_path=baseline.acceptance_path,
            compared_path=compared.acceptance_path,
        )
    result["mismatches"] = mismatches
    if mismatches:
        result["status"] = "mismatch"
        return result
    result["accepted"] = True
    result["status"] = "invariant"
    return result


def _write_report(report: Mapping[str, Any], output: Path | None) -> None:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    )
    if output is None:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        temporary.write_text(f"{payload}\n", encoding="utf-8")
        temporary.replace(output)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare display-timeframe-invariant profile evidence from two "
            "or more accepted Phase 0 runs."
        )
    )
    parser.add_argument(
        "acceptance",
        nargs="+",
        type=Path,
        help="path to an accepted acceptance.json report",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the JSON report to this path instead of stdout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = compare_acceptance_paths(args.acceptance)
    try:
        _write_report(report, args.output)
    except OSError as exc:
        sys.stderr.write(f"Could not write invariance report: {exc}\n")
        return 2
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
