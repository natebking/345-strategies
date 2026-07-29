#!/usr/bin/env python3
"""Deterministic Phase 0 matrix generation and offline evidence audit.

This tool never opens or controls TradingView.  ``generate`` expands a locked
session plan and a hash-consistent base logical-run manifest into 1-, 5-, 15-,
and 60-minute cells.  ``audit`` summarizes acceptance and invariance JSON that
already exists on disk and can optionally reconcile it to a generated index.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


MATRIX_VERSION = "1.0.0"
PLAN_SCHEMA = "vpx.session-plan/1"
INDEX_SCHEMA = "vpx.matrix-index/1"
AUDIT_SCHEMA = "vpx.matrix-audit/1"
MANIFEST_SCHEMA = "vpx.logical-run/1"
ACCEPTANCE_SCHEMA = "vpx.acceptance/1"
INVARIANCE_SCHEMA = "vpx.invariance/1"
DISPLAY_TIMEFRAMES = (1, 5, 15, 60)
MAX_EXACT_TOKEN = 2_147_483_647
TOKEN_FLOOR = 100_000_000
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class MatrixError(Exception):
    """A stable, machine-readable matrix-tool failure."""

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


def _fail(code: str, message: str, **details: Any) -> None:
    raise MatrixError(code, message, **details)


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        _fail(
            "CANONICAL_JSON_INVALID",
            "Value cannot be represented as canonical JSON",
            reason=str(exc),
        )
    return text.encode("ascii")


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
            "FILE_READ_ERROR",
            "Required file could not be read",
            path=str(path),
            reason=str(exc),
        )
    return digest.hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        _fail("FILE_MISSING", f"{label} is missing", path=str(path))
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


def _string(
    mapping: Mapping[str, Any],
    field: str,
    *,
    context: str,
) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        _fail(
            "FIELD_INVALID",
            f"{context}.{field} must be a non-empty string",
            context=context,
            field=field,
        )
    return value


def _integer(
    mapping: Mapping[str, Any],
    field: str,
    *,
    context: str,
    minimum: int | None = None,
) -> int:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(
            "FIELD_INVALID",
            f"{context}.{field} must be an integer",
            context=context,
            field=field,
        )
    if minimum is not None and value < minimum:
        _fail(
            "FIELD_INVALID",
            f"{context}.{field} is below its minimum",
            context=context,
            field=field,
            value=value,
            minimum=minimum,
        )
    return value


def _mapping(
    mapping: Mapping[str, Any],
    field: str,
    *,
    context: str,
) -> Mapping[str, Any]:
    value = mapping.get(field)
    if not isinstance(value, Mapping):
        _fail(
            "FIELD_INVALID",
            f"{context}.{field} must be an object",
            context=context,
            field=field,
        )
    return value


def _validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("schema") != PLAN_SCHEMA:
        _fail(
            "PLAN_SCHEMA_UNSUPPORTED",
            "Unsupported session-plan schema",
            schema=plan.get("schema"),
        )
    matrix_id = _string(plan, "matrix_id", context="plan")
    logical_run_prefix = _string(
        plan,
        "logical_run_prefix",
        context="plan",
    )
    if not SLUG_RE.fullmatch(logical_run_prefix):
        _fail(
            "PLAN_SLUG_INVALID",
            "logical_run_prefix must be a lowercase hyphenated slug",
            value=logical_run_prefix,
        )
    created_utc = _string(plan, "created_utc", context="plan")
    timeframes = plan.get("display_timeframes")
    if (
        not isinstance(timeframes, list)
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in timeframes
        )
        or len(timeframes) != len(DISPLAY_TIMEFRAMES)
        or set(timeframes) != set(DISPLAY_TIMEFRAMES)
    ):
        _fail(
            "PLAN_TIMEFRAMES_INVALID",
            "display_timeframes must contain exactly 1, 5, 15, and 60",
            expected=list(DISPLAY_TIMEFRAMES),
            actual=timeframes,
        )
    sessions_value = plan.get("sessions")
    if not isinstance(sessions_value, list) or not sessions_value:
        _fail(
            "PLAN_SESSIONS_INVALID",
            "plan.sessions must be a non-empty array",
        )

    sessions: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for index, value in enumerate(sessions_value):
        context = f"plan.sessions[{index}]"
        if not isinstance(value, Mapping):
            _fail(
                "PLAN_SESSION_INVALID",
                f"{context} must be an object",
                index=index,
            )
        session_key = _string(value, "session_key", context=context)
        if not SLUG_RE.fullmatch(session_key):
            _fail(
                "PLAN_SLUG_INVALID",
                "session_key must be a lowercase hyphenated slug",
                value=session_key,
                index=index,
            )
        if session_key in seen_keys:
            _fail(
                "PLAN_SESSION_DUPLICATE",
                "session_key appears more than once",
                session_key=session_key,
            )
        seen_keys.add(session_key)

        warmup_start_ms = _integer(
            value,
            "warmup_start_ms",
            context=context,
            minimum=0,
        )
        measurement = _mapping(
            value,
            "measurement",
            context=context,
        )
        measurement_context = f"{context}.measurement"
        measurement_session_id = _string(
            measurement,
            "session_id",
            context=measurement_context,
        )
        measurement_start_ms = _integer(
            measurement,
            "start_ms",
            context=measurement_context,
            minimum=0,
        )
        measurement_end_ms = _integer(
            measurement,
            "end_ms",
            context=measurement_context,
            minimum=0,
        )
        bar_anchor_ms = _integer(
            measurement,
            "bar_anchor_ms",
            context=measurement_context,
        )
        manual = _mapping(value, "manual_profile", context=context)
        manual_context = f"{context}.manual_profile"
        manual_start_ms = _integer(
            manual,
            "start_ms",
            context=manual_context,
            minimum=0,
        )
        manual_end_ms = _integer(
            manual,
            "end_ms",
            context=manual_context,
            minimum=0,
        )
        manual_expected_minutes = _integer(
            manual,
            "expected_minutes",
            context=manual_context,
            minimum=1,
        )
        if not (
            warmup_start_ms <= manual_start_ms < manual_end_ms
            <= measurement_start_ms < measurement_end_ms
        ):
            _fail(
                "PLAN_WINDOW_INVALID",
                (
                    "Expected warmup <= manual start < manual end <= "
                    "measurement start < measurement end"
                ),
                session_key=session_key,
            )
        sessions.append(
            {
                "session_key": session_key,
                "warmup_start_ms": warmup_start_ms,
                "measurement": {
                    "session_id": measurement_session_id,
                    "start_ms": measurement_start_ms,
                    "end_ms": measurement_end_ms,
                    "bar_anchor_ms": bar_anchor_ms,
                },
                "manual_profile": {
                    "start_ms": manual_start_ms,
                    "end_ms": manual_end_ms,
                    "expected_minutes": manual_expected_minutes,
                },
            }
        )
    return {
        "matrix_id": matrix_id,
        "logical_run_prefix": logical_run_prefix,
        "created_utc": created_utc,
        "sessions": sorted(
            sessions,
            key=lambda session: session["session_key"],
        ),
    }


def _validate_template(template: Mapping[str, Any]) -> None:
    if template.get("schema") != MANIFEST_SCHEMA:
        _fail(
            "TEMPLATE_SCHEMA_UNSUPPORTED",
            "Base template is not a logical-run manifest",
            schema=template.get("schema"),
        )
    _string(template, "experiment_id", context="template")
    pine_settings = _mapping(
        template,
        "pine_settings",
        context="template",
    )
    chart_state = _mapping(template, "chart_state", context="template")
    _mapping(template, "window", context="template")
    _mapping(template, "chart_csv", context="template")
    required_settings = {
        "manual_end_ms",
        "manual_expected_minutes",
        "manual_start_ms",
        "measurement_end_ms",
        "measurement_start_ms",
        "output_ticks",
        "value_area_percent",
    }
    missing = sorted(required_settings - set(pine_settings))
    if missing:
        _fail(
            "TEMPLATE_SETTINGS_MISSING",
            "Base template lacks required Pine settings",
            missing=missing,
        )
    if "chart_timeframe" not in chart_state:
        _fail(
            "TEMPLATE_CHART_STATE_INVALID",
            "Base template chart_state lacks chart_timeframe",
        )
    expected_pine_hash = template.get("pine_settings_hash")
    actual_pine_hash = _canonical_hash(pine_settings)
    if expected_pine_hash != actual_pine_hash:
        _fail(
            "TEMPLATE_PINE_HASH_MISMATCH",
            "Base template Pine settings hash is stale",
            expected=expected_pine_hash,
            actual=actual_pine_hash,
        )
    expected_chart_hash = template.get("chart_state_hash")
    actual_chart_hash = _canonical_hash(chart_state)
    if expected_chart_hash != actual_chart_hash:
        _fail(
            "TEMPLATE_CHART_HASH_MISMATCH",
            "Base template chart-state hash is stale",
            expected=expected_chart_hash,
            actual=actual_chart_hash,
        )


def _derive_token(*parts: str) -> int:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).digest()
    width = MAX_EXACT_TOKEN - TOKEN_FLOOR + 1
    return TOKEN_FLOOR + int.from_bytes(digest[:8], "big") % width


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace(".", "p")


def _aligned_session(
    *,
    start_ms: int,
    end_ms: int,
    anchor_ms: int,
    timeframe: int,
    session_id: str,
) -> dict[str, Any]:
    bar_ms = timeframe * 60_000
    remainder = (start_ms - anchor_ms) % bar_ms
    aligned_start = start_ms if remainder == 0 else start_ms + bar_ms - remainder
    if aligned_start >= end_ms:
        _fail(
            "SESSION_ALIGNMENT_EMPTY",
            "No display bars begin inside the measurement window",
            timeframe=timeframe,
            start_ms=start_ms,
            end_ms=end_ms,
            anchor_ms=anchor_ms,
        )
    expected_count = ((end_ms - 1 - aligned_start) // bar_ms) + 1
    return {
        "session_id": session_id,
        "start_ms": aligned_start,
        "end_ms": end_ms,
        "bar_ms": bar_ms,
        "expected_count": expected_count,
    }


def _build_manifest(
    *,
    template: Mapping[str, Any],
    matrix_id: str,
    logical_run_prefix: str,
    created_utc: str,
    session: Mapping[str, Any],
    timeframe: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = copy.deepcopy(dict(template))
    manifest.pop("example_only", None)
    manifest.pop("example_notes", None)

    settings = manifest["pine_settings"]
    measurement = session["measurement"]
    manual = session["manual_profile"]
    settings["measurement_start_ms"] = measurement["start_ms"]
    settings["measurement_end_ms"] = measurement["end_ms"]
    settings["manual_start_ms"] = manual["start_ms"]
    settings["manual_end_ms"] = manual["end_ms"]
    settings["manual_expected_minutes"] = manual["expected_minutes"]
    pine_settings_hash = _canonical_hash(settings)

    output_ticks = _format_scalar(settings["output_ticks"])
    value_area = _format_scalar(settings["value_area_percent"])
    logical_run_id = (
        f"{logical_run_prefix}-{session['session_key']}-"
        f"{timeframe}m-r{output_ticks}-va{value_area}"
    )
    logical_run_token = _derive_token(
        matrix_id,
        logical_run_id,
        "logical-run",
    )
    configuration_token = _derive_token(
        matrix_id,
        pine_settings_hash,
        "configuration",
    )

    chart_state = manifest["chart_state"]
    chart_state["chart_timeframe"] = str(timeframe)
    chart_state_hash = _canonical_hash(chart_state)
    expected_session = _aligned_session(
        start_ms=measurement["start_ms"],
        end_ms=measurement["end_ms"],
        anchor_ms=measurement["bar_anchor_ms"],
        timeframe=timeframe,
        session_id=measurement["session_id"],
    )

    manifest["logical_run_id"] = logical_run_id
    manifest["logical_run_token"] = logical_run_token
    manifest["configuration_token"] = configuration_token
    manifest["created_utc"] = created_utc
    manifest["pine_settings_hash"] = pine_settings_hash
    manifest["chart_state_hash"] = chart_state_hash
    manifest["window"] = {
        "warmup_start_ms": session["warmup_start_ms"],
        "measurement_start_ms": measurement["start_ms"],
        "measurement_end_ms": measurement["end_ms"],
        "expected_sessions": [expected_session],
    }
    manifest["matrix"] = {
        "matrix_id": matrix_id,
        "session_key": session["session_key"],
        "display_timeframe": timeframe,
        "bar_anchor_ms": measurement["bar_anchor_ms"],
    }
    cell = {
        "session_key": session["session_key"],
        "display_timeframe": timeframe,
        "logical_run_id": logical_run_id,
        "logical_run_token": logical_run_token,
        "configuration_token": configuration_token,
        "pine_settings_hash": pine_settings_hash,
        "chart_state_hash": chart_state_hash,
        "expected_session": expected_session,
    }
    return manifest, cell


def _pretty_json(value: Any) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )


def _preflight_writes(files: Mapping[Path, str]) -> None:
    for path, payload in files.items():
        if not path.exists():
            continue
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError as exc:
            _fail(
                "OUTPUT_READ_ERROR",
                "Existing output could not be read",
                path=str(path),
                reason=str(exc),
            )
        if existing != payload:
            _fail(
                "OUTPUT_CONFLICT",
                "Existing output differs from deterministic generation",
                path=str(path),
            )


def _write_files(files: Mapping[Path, str]) -> tuple[int, int]:
    created = 0
    unchanged = 0
    for path, payload in files.items():
        if path.exists():
            unchanged += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(payload)
                temporary_name = handle.name
            os.replace(temporary_name, path)
            created += 1
        except OSError as exc:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink()
                except OSError:
                    pass
            _fail(
                "OUTPUT_WRITE_ERROR",
                "Generated output could not be written",
                path=str(path),
                reason=str(exc),
            )
    return created, unchanged


def generate_matrix(
    *,
    plan_path: str | os.PathLike[str],
    template_path: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    """Generate deterministic logical-run manifests and a matrix index."""

    plan_file = Path(plan_path).resolve()
    template_file = Path(template_path).resolve()
    output_root = Path(output_dir).resolve()
    raw_plan = _load_object(plan_file, "session plan")
    plan = _validate_plan(raw_plan)
    template = _load_object(template_file, "base manifest template")
    _validate_template(template)

    cells: list[dict[str, Any]] = []
    files: dict[Path, str] = {}
    logical_tokens: dict[int, str] = {}
    logical_ids: set[str] = set()
    for session in plan["sessions"]:
        for timeframe in DISPLAY_TIMEFRAMES:
            manifest, cell = _build_manifest(
                template=template,
                matrix_id=plan["matrix_id"],
                logical_run_prefix=plan["logical_run_prefix"],
                created_utc=plan["created_utc"],
                session=session,
                timeframe=timeframe,
            )
            logical_run_id = cell["logical_run_id"]
            token = cell["logical_run_token"]
            if logical_run_id in logical_ids:
                _fail(
                    "LOGICAL_RUN_ID_COLLISION",
                    "Generated logical-run ID is not unique",
                    logical_run_id=logical_run_id,
                )
            if token in logical_tokens:
                _fail(
                    "LOGICAL_RUN_TOKEN_COLLISION",
                    "Generated logical-run token is not unique",
                    token=token,
                    first=logical_tokens[token],
                    second=logical_run_id,
                )
            logical_ids.add(logical_run_id)
            logical_tokens[token] = logical_run_id
            relative = Path(logical_run_id) / "manifest.json"
            manifest_path = output_root / relative
            payload = _pretty_json(manifest)
            files[manifest_path] = payload
            cell["manifest_relpath"] = relative.as_posix()
            cell["manifest_sha256"] = hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()
            cells.append(cell)

    index = {
        "schema": INDEX_SCHEMA,
        "generator_version": MATRIX_VERSION,
        "matrix_id": plan["matrix_id"],
        "created_utc": plan["created_utc"],
        "display_timeframes": list(DISPLAY_TIMEFRAMES),
        "session_plan_sha256": _sha256_file(plan_file),
        "base_manifest_sha256": _sha256_file(template_file),
        "cell_count": len(cells),
        "cells": cells,
    }
    index_path = output_root / "matrix-index.json"
    files[index_path] = _pretty_json(index)
    _preflight_writes(files)
    created, unchanged = _write_files(files)
    return {
        "schema": "vpx.matrix-generation/1",
        "generator_version": MATRIX_VERSION,
        "accepted": True,
        "matrix_id": plan["matrix_id"],
        "session_count": len(plan["sessions"]),
        "cell_count": len(cells),
        "created_files": created,
        "unchanged_files": unchanged,
        "output_dir": str(output_root),
        "index_path": str(index_path),
        "cells": cells,
        "errors": [],
    }


def _try_load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def _acceptance_summary(
    path: Path,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    source = value.get("source_vintage")
    return {
        "path": str(path),
        "accepted": value.get("accepted") is True,
        "logical_run_id": value.get("logical_run_id"),
        "attempt_id": value.get("attempt_id"),
        "pine_settings_hash": value.get("pine_settings_hash"),
        "chart_state_hash": value.get("chart_state_hash"),
        "source_vintage": dict(source) if isinstance(source, Mapping) else None,
        "errors": value.get("errors", []),
    }


def _invariance_summary(
    path: Path,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    mismatches = value.get("mismatches")
    errors = value.get("errors")
    return {
        "path": str(path),
        "accepted": value.get("accepted") is True,
        "status": value.get("status"),
        "input_count": value.get("input_count"),
        "mismatch_count": (
            len(mismatches) if isinstance(mismatches, list) else None
        ),
        "error_count": len(errors) if isinstance(errors, list) else None,
    }


def audit_matrix(
    *,
    root: str | os.PathLike[str],
    index_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Summarize existing acceptance and invariance reports under a root."""

    audit_root = Path(root).resolve()
    if not audit_root.is_dir():
        _fail(
            "AUDIT_ROOT_INVALID",
            "Audit root must be an existing directory",
            path=str(audit_root),
        )
    acceptances: list[dict[str, Any]] = []
    invariances: list[dict[str, Any]] = []
    scan_errors: list[dict[str, Any]] = []
    for path in sorted(audit_root.rglob("*.json")):
        value, error = _try_load_json(path)
        if error is not None:
            if (
                path.name == "acceptance.json"
                or "invariance" in path.name.lower()
            ):
                scan_errors.append(
                    {
                        "code": "AUDIT_JSON_INVALID",
                        "path": str(path),
                        "reason": error,
                    }
                )
            continue
        if not isinstance(value, Mapping):
            continue
        if value.get("schema") == ACCEPTANCE_SCHEMA:
            acceptances.append(_acceptance_summary(path, value))
        elif value.get("schema") == INVARIANCE_SCHEMA:
            invariances.append(_invariance_summary(path, value))

    accepted_runs = {
        item["logical_run_id"]
        for item in acceptances
        if item["accepted"] and isinstance(item["logical_run_id"], str)
    }
    observed_runs = {
        item["logical_run_id"]
        for item in acceptances
        if isinstance(item["logical_run_id"], str)
    }
    coverage: dict[str, Any] | None = None
    index_summary: dict[str, Any] | None = None
    if index_path is not None:
        resolved_index = Path(index_path).resolve()
        index = _load_object(resolved_index, "matrix index")
        if index.get("schema") != INDEX_SCHEMA:
            _fail(
                "INDEX_SCHEMA_UNSUPPORTED",
                "Audit index has an unsupported schema",
                path=str(resolved_index),
                schema=index.get("schema"),
            )
        raw_cells = index.get("cells")
        if not isinstance(raw_cells, list):
            _fail(
                "INDEX_CELLS_INVALID",
                "Audit index cells must be an array",
                path=str(resolved_index),
            )
        expected_runs: set[str] = set()
        for position, cell in enumerate(raw_cells):
            if not isinstance(cell, Mapping):
                _fail(
                    "INDEX_CELLS_INVALID",
                    "Audit index cell must be an object",
                    position=position,
                )
            logical_run_id = cell.get("logical_run_id")
            if not isinstance(logical_run_id, str) or not logical_run_id:
                _fail(
                    "INDEX_CELLS_INVALID",
                    "Audit index cell lacks logical_run_id",
                    position=position,
                )
            expected_runs.add(logical_run_id)
        missing = sorted(expected_runs - accepted_runs)
        rejected_only = sorted(
            logical_run_id
            for logical_run_id in expected_runs & observed_runs
            if logical_run_id not in accepted_runs
        )
        coverage = {
            "expected_logical_runs": len(expected_runs),
            "accepted_logical_runs": len(expected_runs & accepted_runs),
            "missing_or_unaccepted": missing,
            "rejected_only": rejected_only,
            "unexpected_observed": sorted(observed_runs - expected_runs),
        }
        index_summary = {
            "path": str(resolved_index),
            "matrix_id": index.get("matrix_id"),
            "cell_count": index.get("cell_count"),
        }

    accepted_count = sum(item["accepted"] for item in acceptances)
    invariant_count = sum(item["accepted"] for item in invariances)
    has_attention = (
        bool(scan_errors)
        or accepted_count != len(acceptances)
        or invariant_count != len(invariances)
        or (
            coverage is not None
            and bool(coverage["missing_or_unaccepted"])
        )
    )
    if not acceptances and not invariances:
        status = "empty"
    elif has_attention:
        status = "attention"
    else:
        status = "healthy"
    return {
        "schema": AUDIT_SCHEMA,
        "audit_version": MATRIX_VERSION,
        "status": status,
        "root": str(audit_root),
        "index": index_summary,
        "summary": {
            "acceptance_reports": len(acceptances),
            "accepted_attempts": accepted_count,
            "rejected_attempts": len(acceptances) - accepted_count,
            "observed_logical_runs": len(observed_runs),
            "accepted_logical_runs": len(accepted_runs),
            "invariance_reports": len(invariances),
            "invariant_reports": invariant_count,
            "noninvariant_reports": len(invariances) - invariant_count,
            "scan_errors": len(scan_errors),
        },
        "coverage": coverage,
        "acceptances": acceptances,
        "invariance_reports": invariances,
        "errors": scan_errors,
    }


def _write_report(report: Mapping[str, Any], output: Path | None) -> None:
    payload = _pretty_json(report)
    if output is None:
        sys.stdout.write(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary_name = handle.name
        os.replace(temporary_name, output)
    except OSError:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass
        raise


def _error_report(command: str, exc: MatrixError) -> dict[str, Any]:
    return {
        "schema": "vpx.matrix-error/1",
        "generator_version": MATRIX_VERSION,
        "accepted": False,
        "command": command,
        "errors": [exc.as_dict()],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Phase 0 timeframe matrices and audit existing evidence."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate",
        help="generate deterministic 1/5/15/60 logical-run manifests",
    )
    generate.add_argument("--plan", required=True, type=Path)
    generate.add_argument("--template", required=True, type=Path)
    generate.add_argument("--output-dir", required=True, type=Path)
    generate.add_argument(
        "--report",
        type=Path,
        help="write generation JSON here instead of stdout",
    )

    audit = subparsers.add_parser(
        "audit",
        help="summarize existing acceptance and invariance JSON",
    )
    audit.add_argument("--root", required=True, type=Path)
    audit.add_argument(
        "--index",
        type=Path,
        help="optional generated matrix index for coverage reconciliation",
    )
    audit.add_argument(
        "--output",
        type=Path,
        help="write audit JSON here instead of stdout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "generate":
            report = generate_matrix(
                plan_path=args.plan,
                template_path=args.template,
                output_dir=args.output_dir,
            )
            output = args.report
            status = 0
        else:
            report = audit_matrix(
                root=args.root,
                index_path=args.index,
            )
            output = args.output
            status = 0 if report["status"] == "healthy" else 1
    except MatrixError as exc:
        report = _error_report(args.command, exc)
        output = getattr(args, "report", None) or getattr(
            args,
            "output",
            None,
        )
        status = 1
    try:
        _write_report(report, output)
    except OSError as exc:
        sys.stderr.write(f"Could not write matrix report: {exc}\n")
        return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
