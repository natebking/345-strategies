#!/usr/bin/env python3
"""Stdlib-only acceptance gate for Volume Profile Phase 0 TradingView exports.

The checker deliberately treats browser output as untrusted input.  It accepts
two Pine-log containers:

* TradingView's downloaded CSV form with leading ``Date,Message`` columns.
* Plain text containing one VPX record per line (a non-VPX prefix is allowed).

The public Python interface is ``check_artifacts()`` and ``compare_reports()``.
The command-line interface is documented by ``python3 vpx_accept.py --help``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


CHECKER_VERSION = "1.0.0"
MAX_EXACT_TOKEN = 2_147_483_647
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
INTEGER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
ALLOWED_SEVERITIES = frozenset({"INFO", "WARN", "ERROR"})
ENTITY_ID_FIELDS = {
    "PROFILE": "profile_id",
    "ZONE": "zone_id",
    "EVENT": "event_id",
}
PAYLOAD_KINDS = frozenset(ENTITY_ID_FIELDS)
IDENTITY_FIELDS = (
    "logical_run_id",
    "attempt_id",
    "attempt_token",
)


class ValidationError(Exception):
    """A stable, machine-readable artifact rejection."""

    def __init__(
        self,
        code: str,
        message: str,
        **details: Any,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            out["details"] = self.details
        return out


@dataclass(frozen=True)
class VpxRecord:
    """One parsed VPX message."""

    fields: Mapping[str, str]
    source_row: int
    raw_message: str
    pane_time: str | None = None

    @property
    def kind(self) -> str:
        return self.fields["kind"]

    @property
    def severity(self) -> str:
        return self.fields["severity"]

    @property
    def seq(self) -> int:
        return int(self.fields["seq"])


@dataclass(frozen=True)
class LogResult:
    records: tuple[VpxRecord, ...]
    header: VpxRecord
    terminal: VpxRecord
    config: Mapping[str, Any]
    source_vintage: Mapping[str, Any]
    payload_sha256: str
    record_counts: Mapping[str, int]


@dataclass(frozen=True)
class CsvRow:
    time_ms: int
    raw: Mapping[str, str]
    numeric: Mapping[str, Decimal | None]
    source_row: int


@dataclass(frozen=True)
class CsvResult:
    rows: tuple[CsvRow, ...]
    expected_times: frozenset[int]


def _fail(code: str, message: str, **details: Any) -> None:
    raise ValidationError(code, message, **details)


def canonical_json_bytes(value: Any) -> bytes:
    """Return the sole canonical JSON encoding used by the harness."""

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


def canonical_hash(value: Any) -> str:
    """SHA-256 of canonical_json_bytes(value)."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except FileNotFoundError:
        _fail("FILE_MISSING", "Required input file is missing", path=str(path))
    except OSError as exc:
        _fail(
            "FILE_READ_ERROR",
            "Required input file could not be read",
            path=str(path),
            reason=str(exc),
        )
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        _fail("FILE_MISSING", f"{label} file is missing", path=str(path))
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


def _required(mapping: Mapping[str, Any], key: str, code: str) -> Any:
    if key not in mapping:
        _fail(code, f"Required field {key!r} is missing", field=key)
    return mapping[key]


def _require_nonempty_string(value: Any, field: str, code: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(code, f"{field} must be a non-empty string", field=field)
    return value


def _parse_int(
    value: Any,
    field: str,
    code: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool):
        _fail(code, f"{field} must be an integer", field=field, value=value)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and INTEGER_RE.fullmatch(value):
        parsed = int(value)
    else:
        _fail(code, f"{field} must be an integer", field=field, value=value)
    if minimum is not None and parsed < minimum:
        _fail(
            code,
            f"{field} is below its minimum",
            field=field,
            value=parsed,
            minimum=minimum,
        )
    if maximum is not None and parsed > maximum:
        _fail(
            code,
            f"{field} exceeds its maximum",
            field=field,
            value=parsed,
            maximum=maximum,
        )
    return parsed


def _parse_exact_token(value: Any, field: str, code: str) -> int:
    return _parse_int(
        value,
        field,
        code,
        minimum=0,
        maximum=MAX_EXACT_TOKEN,
    )


def _validate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    schema = _required(manifest, "schema", "MANIFEST_SCHEMA_MISSING")
    if schema != "vpx.logical-run/1":
        _fail(
            "MANIFEST_SCHEMA_UNSUPPORTED",
            "Unsupported logical-run manifest schema",
            schema=schema,
        )

    experiment_id = _require_nonempty_string(
        _required(manifest, "experiment_id", "MANIFEST_ID_MISSING"),
        "experiment_id",
        "MANIFEST_ID_INVALID",
    )
    logical_run_id = _require_nonempty_string(
        _required(manifest, "logical_run_id", "MANIFEST_ID_MISSING"),
        "logical_run_id",
        "MANIFEST_ID_INVALID",
    )
    logical_run_token = _parse_exact_token(
        _required(manifest, "logical_run_token", "MANIFEST_TOKEN_MISSING"),
        "logical_run_token",
        "MANIFEST_TOKEN_INVALID",
    )
    configuration_token = _parse_exact_token(
        _required(manifest, "configuration_token", "MANIFEST_TOKEN_MISSING"),
        "configuration_token",
        "MANIFEST_TOKEN_INVALID",
    )

    pine_settings = _required(
        manifest,
        "pine_settings",
        "PINE_SETTINGS_MISSING",
    )
    if not isinstance(pine_settings, dict):
        _fail("PINE_SETTINGS_INVALID", "pine_settings must be an object")
    for key, value in pine_settings.items():
        if not isinstance(key, str) or not key:
            _fail(
                "PINE_SETTINGS_INVALID",
                "Every Pine setting key must be a non-empty string",
            )
        if isinstance(value, (dict, list)) or value is None:
            _fail(
                "PINE_SETTINGS_INVALID",
                "Phase 0 Pine settings must be scalar JSON values",
                key=key,
            )

    declared_pine_hash = _require_nonempty_string(
        _required(
            manifest,
            "pine_settings_hash",
            "PINE_SETTINGS_HASH_MISSING",
        ),
        "pine_settings_hash",
        "PINE_SETTINGS_HASH_INVALID",
    )
    actual_pine_hash = canonical_hash(pine_settings)
    if declared_pine_hash != actual_pine_hash:
        _fail(
            "MANIFEST_PINE_SETTINGS_HASH_MISMATCH",
            "Manifest Pine-settings hash does not match its Pine settings",
            declared=declared_pine_hash,
            actual=actual_pine_hash,
        )

    chart_state = _required(manifest, "chart_state", "CHART_STATE_MISSING")
    if not isinstance(chart_state, dict):
        _fail("CHART_STATE_INVALID", "chart_state must be an object")
    declared_chart_hash = _require_nonempty_string(
        _required(
            manifest,
            "chart_state_hash",
            "CHART_STATE_HASH_MISSING",
        ),
        "chart_state_hash",
        "CHART_STATE_HASH_INVALID",
    )
    actual_chart_hash = canonical_hash(chart_state)
    if declared_chart_hash != actual_chart_hash:
        _fail(
            "MANIFEST_CHART_STATE_HASH_MISMATCH",
            "Manifest chart-state hash does not match its chart state",
            declared=declared_chart_hash,
            actual=actual_chart_hash,
        )

    window = _required(manifest, "window", "WINDOW_MISSING")
    if not isinstance(window, dict):
        _fail("WINDOW_INVALID", "window must be an object")
    warmup_start_ms = _parse_int(
        _required(window, "warmup_start_ms", "WINDOW_FIELD_MISSING"),
        "warmup_start_ms",
        "WINDOW_FIELD_INVALID",
    )
    measurement_start_ms = _parse_int(
        _required(window, "measurement_start_ms", "WINDOW_FIELD_MISSING"),
        "measurement_start_ms",
        "WINDOW_FIELD_INVALID",
    )
    measurement_end_ms = _parse_int(
        _required(window, "measurement_end_ms", "WINDOW_FIELD_MISSING"),
        "measurement_end_ms",
        "WINDOW_FIELD_INVALID",
    )
    if not warmup_start_ms <= measurement_start_ms < measurement_end_ms:
        _fail(
            "WINDOW_ORDER_INVALID",
            "Window must satisfy warmup_start <= measurement_start < measurement_end",
        )
    sessions = _required(window, "expected_sessions", "SESSION_SPEC_MISSING")
    if not isinstance(sessions, list) or not sessions:
        _fail(
            "SESSION_SPEC_INVALID",
            "window.expected_sessions must be a non-empty array",
        )

    chart_csv = _required(manifest, "chart_csv", "CSV_SCHEMA_MISSING")
    if not isinstance(chart_csv, dict):
        _fail("CSV_SCHEMA_INVALID", "chart_csv must be an object")

    return {
        "experiment_id": experiment_id,
        "logical_run_id": logical_run_id,
        "logical_run_token": logical_run_token,
        "configuration_token": configuration_token,
        "pine_settings": pine_settings,
        "pine_settings_hash": actual_pine_hash,
        "chart_state": chart_state,
        "chart_state_hash": actual_chart_hash,
        "window": window,
        "chart_csv": chart_csv,
    }


def _validate_attempt(
    attempt: Mapping[str, Any],
    manifest_info: Mapping[str, Any],
) -> dict[str, Any]:
    schema = _required(attempt, "schema", "ATTEMPT_SCHEMA_MISSING")
    if schema != "vpx.attempt/1":
        _fail(
            "ATTEMPT_SCHEMA_UNSUPPORTED",
            "Unsupported attempt envelope schema",
            schema=schema,
        )
    experiment_id = _require_nonempty_string(
        _required(attempt, "experiment_id", "ATTEMPT_ID_MISSING"),
        "experiment_id",
        "ATTEMPT_ID_INVALID",
    )
    logical_run_id = _require_nonempty_string(
        _required(attempt, "logical_run_id", "ATTEMPT_ID_MISSING"),
        "logical_run_id",
        "ATTEMPT_ID_INVALID",
    )
    attempt_id = _require_nonempty_string(
        _required(attempt, "attempt_id", "ATTEMPT_ID_MISSING"),
        "attempt_id",
        "ATTEMPT_ID_INVALID",
    )
    attempt_token = _parse_exact_token(
        _required(attempt, "attempt_token", "ATTEMPT_TOKEN_MISSING"),
        "attempt_token",
        "ATTEMPT_TOKEN_INVALID",
    )
    if experiment_id != manifest_info["experiment_id"]:
        _fail(
            "ATTEMPT_EXPERIMENT_ID_MISMATCH",
            "Attempt experiment_id does not match manifest",
            expected=manifest_info["experiment_id"],
            actual=experiment_id,
        )
    if logical_run_id != manifest_info["logical_run_id"]:
        _fail(
            "ATTEMPT_LOGICAL_RUN_ID_MISMATCH",
            "Attempt logical_run_id does not match manifest",
            expected=manifest_info["logical_run_id"],
            actual=logical_run_id,
        )
    return {
        "experiment_id": experiment_id,
        "logical_run_id": logical_run_id,
        "attempt_id": attempt_id,
        "attempt_token": attempt_token,
    }


def _validate_ui_readback(
    ui: Mapping[str, Any],
    manifest_info: Mapping[str, Any],
    attempt_info: Mapping[str, Any],
) -> None:
    schema = _required(ui, "schema", "UI_SCHEMA_MISSING")
    if schema != "vpx.ui-readback/1":
        _fail(
            "UI_SCHEMA_UNSUPPORTED",
            "Unsupported UI read-back schema",
            schema=schema,
        )
    expected_identity = {
        "logical_run_id": manifest_info["logical_run_id"],
        "attempt_id": attempt_info["attempt_id"],
        "attempt_token": attempt_info["attempt_token"],
    }
    for key, expected in expected_identity.items():
        actual = _required(ui, key, "UI_IDENTITY_MISSING")
        if key == "attempt_token":
            actual = _parse_exact_token(
                actual,
                key,
                "UI_IDENTITY_INVALID",
            )
        if actual != expected:
            _fail(
                "UI_IDENTITY_MISMATCH",
                "UI read-back identity does not match attempt",
                field=key,
                expected=expected,
                actual=actual,
            )
    chart_state = _required(ui, "chart_state", "UI_CHART_STATE_MISSING")
    if not isinstance(chart_state, dict):
        _fail("UI_CHART_STATE_INVALID", "UI chart_state must be an object")
    declared_hash = _require_nonempty_string(
        _required(ui, "chart_state_hash", "UI_CHART_STATE_HASH_MISSING"),
        "chart_state_hash",
        "UI_CHART_STATE_HASH_INVALID",
    )
    actual_hash = canonical_hash(chart_state)
    if declared_hash != actual_hash:
        _fail(
            "UI_SELF_HASH_MISMATCH",
            "UI read-back chart-state hash does not match its chart state",
            declared=declared_hash,
            actual=actual_hash,
        )
    if actual_hash != manifest_info["chart_state_hash"]:
        _fail(
            "UI_CHART_STATE_MISMATCH",
            "UI read-back chart state does not match the manifest",
            expected_hash=manifest_info["chart_state_hash"],
            actual_hash=actual_hash,
        )


def _iter_log_messages(path: Path) -> Iterator[tuple[int, str | None, str]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        _fail("FILE_MISSING", "Pine Logs file is missing", path=str(path))
    except (OSError, UnicodeError) as exc:
        _fail(
            "LOG_READ_ERROR",
            "Pine Logs file is not readable UTF-8 text",
            path=str(path),
            reason=str(exc),
        )

    lines = text.splitlines()
    if not lines:
        _fail("LOG_EMPTY", "Pine Logs file is empty", path=str(path))

    first_row = next(csv.reader([lines[0]]), [])
    if len(first_row) >= 2 and first_row[:2] == ["Date", "Message"]:
        reader = csv.reader(text.splitlines())
        header = next(reader)
        if header != ["Date", "Message"]:
            _fail(
                "LOG_CSV_HEADER_INVALID",
                "TradingView log CSV must contain exactly Date,Message columns",
                header=header,
            )
        for row_number, row in enumerate(reader, start=2):
            if len(row) != 2:
                _fail(
                    "LOG_CSV_ROW_INVALID",
                    "TradingView log CSV row must contain exactly two columns",
                    row=row_number,
                    columns=len(row),
                )
            yield row_number, row[0], row[1]
        return

    for row_number, line in enumerate(lines, start=1):
        marker = line.find("VPX|")
        if marker >= 0:
            yield row_number, None, line[marker:]


def parse_vpx_record(
    message: str,
    *,
    source_row: int = 0,
    pane_time: str | None = None,
) -> VpxRecord:
    """Parse one strict ``VPX|key=value`` record."""

    if not message.startswith("VPX|"):
        _fail(
            "VPX_PREFIX_INVALID",
            "VPX record does not begin with VPX|",
            row=source_row,
        )
    if "\n" in message or "\r" in message:
        _fail(
            "VPX_MULTILINE_RECORD",
            "VPX machine records must occupy one line",
            row=source_row,
        )
    try:
        message.encode("ascii")
    except UnicodeEncodeError:
        _fail(
            "VPX_NON_ASCII",
            "VPX machine records must contain ASCII only",
            row=source_row,
        )

    fields: dict[str, str] = {}
    parts = message.split("|")
    if parts[0] != "VPX":
        _fail("VPX_PREFIX_INVALID", "Malformed VPX prefix", row=source_row)
    for part in parts[1:]:
        if not part or "=" not in part:
            _fail(
                "VPX_FIELD_INVALID",
                "Every VPX field must be a non-empty key=value pair",
                row=source_row,
                field=part,
            )
        key, value = part.split("=", 1)
        if not KEY_RE.fullmatch(key):
            _fail(
                "VPX_KEY_INVALID",
                "VPX field key is invalid",
                row=source_row,
                key=key,
            )
        if key in fields:
            _fail(
                "VPX_DUPLICATE_KEY",
                "VPX record contains a duplicate key",
                row=source_row,
                key=key,
            )
        if value == "":
            _fail(
                "VPX_VALUE_EMPTY",
                "VPX field value cannot be empty",
                row=source_row,
                key=key,
            )
        fields[key] = value

    for key in ("schema", "kind", "severity", "seq", *IDENTITY_FIELDS):
        if key not in fields:
            _fail(
                "VPX_REQUIRED_FIELD_MISSING",
                "VPX record is missing a required field",
                row=source_row,
                field=key,
            )
    if fields["schema"] != "1":
        _fail(
            "VPX_SCHEMA_UNSUPPORTED",
            "Unsupported VPX record schema",
            row=source_row,
            schema=fields["schema"],
        )
    if not KEY_RE.fullmatch(fields["kind"]):
        _fail(
            "VPX_KIND_INVALID",
            "VPX kind must use identifier characters",
            row=source_row,
            kind=fields["kind"],
        )
    if fields["severity"] not in ALLOWED_SEVERITIES:
        _fail(
            "VPX_SEVERITY_INVALID",
            "VPX severity must be INFO, WARN, or ERROR",
            row=source_row,
            severity=fields["severity"],
        )
    _parse_int(
        fields["seq"],
        "seq",
        "VPX_SEQ_INVALID",
        minimum=1,
    )
    _require_nonempty_string(
        fields["logical_run_id"],
        "logical_run_id",
        "VPX_IDENTITY_INVALID",
    )
    _require_nonempty_string(
        fields["attempt_id"],
        "attempt_id",
        "VPX_IDENTITY_INVALID",
    )
    _parse_exact_token(
        fields["attempt_token"],
        "attempt_token",
        "VPX_IDENTITY_INVALID",
    )
    return VpxRecord(
        fields=fields,
        source_row=source_row,
        raw_message=message,
        pane_time=pane_time,
    )


def parse_log_file(path: Path) -> tuple[VpxRecord, ...]:
    records: list[VpxRecord] = []
    for row, pane_time, message in _iter_log_messages(path):
        if not message.startswith("VPX|"):
            continue
        records.append(
            parse_vpx_record(
                message,
                source_row=row,
                pane_time=pane_time,
            )
        )
    if not records:
        _fail("LOG_NO_VPX_RECORDS", "Pine Logs contain no VPX records")
    return tuple(records)


def _select_attempt_records(
    records: Sequence[VpxRecord],
    logical_run_id: str,
    attempt_id: str,
    attempt_token: int,
) -> tuple[VpxRecord, ...]:
    exact = tuple(
        record
        for record in records
        if record.fields["logical_run_id"] == logical_run_id
        and record.fields["attempt_id"] == attempt_id
        and _parse_exact_token(
            record.fields["attempt_token"],
            "attempt_token",
            "VPX_IDENTITY_INVALID",
        )
        == attempt_token
    )
    if exact:
        return exact

    same_run_and_attempt = [
        record
        for record in records
        if record.fields["logical_run_id"] == logical_run_id
        and record.fields["attempt_id"] == attempt_id
    ]
    if same_run_and_attempt:
        seen = sorted({record.fields["attempt_token"] for record in same_run_and_attempt})
        _fail(
            "ATTEMPT_TOKEN_MISMATCH",
            "Logs contain the target IDs under a different attempt token",
            expected=attempt_token,
            seen=seen,
        )
    same_run = [
        record
        for record in records
        if record.fields["logical_run_id"] == logical_run_id
    ]
    if same_run:
        seen = sorted({record.fields["attempt_id"] for record in same_run})
        _fail(
            "ATTEMPT_ID_MISMATCH",
            "Logs contain the logical run under a different attempt ID",
            expected=attempt_id,
            seen=seen,
        )
    seen_runs = sorted({record.fields["logical_run_id"] for record in records})
    _fail(
        "LOGICAL_RUN_ID_MISMATCH",
        "Logs do not contain the target logical run",
        expected=logical_run_id,
        seen=seen_runs,
    )


def _coerce_config_value(raw: str, expected: Any, key: str) -> Any:
    if isinstance(expected, bool):
        if raw == "true":
            return True
        if raw == "false":
            return False
        _fail(
            "CONFIG_VALUE_INVALID",
            "Boolean CONFIG values must be true or false",
            key=key,
            value=raw,
        )
    if isinstance(expected, int) and not isinstance(expected, bool):
        return _parse_int(raw, key, "CONFIG_VALUE_INVALID")
    if isinstance(expected, float):
        try:
            value = float(raw)
        except ValueError:
            _fail(
                "CONFIG_VALUE_INVALID",
                "Floating CONFIG value is invalid",
                key=key,
                value=raw,
            )
        if not math.isfinite(value):
            _fail(
                "CONFIG_VALUE_INVALID",
                "Floating CONFIG value must be finite",
                key=key,
                value=raw,
            )
        return value
    if isinstance(expected, str):
        return raw
    _fail(
        "PINE_SETTINGS_INVALID",
        "Unsupported Pine setting type",
        key=key,
        type=type(expected).__name__,
    )


def _canonical_payload_digest(records: Sequence[VpxRecord]) -> str:
    payload: list[dict[str, str]] = []
    omitted = {
        "schema",
        "severity",
        "seq",
        "attempt_id",
        "attempt_token",
    }
    for record in records:
        if record.kind not in PAYLOAD_KINDS:
            continue
        payload.append(
            {
                key: value
                for key, value in record.fields.items()
                if key not in omitted
            }
        )
    return canonical_hash(payload)


def _parse_terminal_count(
    terminal: VpxRecord,
    field: str,
) -> int:
    if field not in terminal.fields:
        _fail(
            "TRAILER_FIELD_MISSING",
            "RUN_END is missing a required count",
            field=field,
        )
    return _parse_int(
        terminal.fields[field],
        field,
        "TRAILER_FIELD_INVALID",
        minimum=0,
    )


def _validate_log(
    all_records: Sequence[VpxRecord],
    manifest_info: Mapping[str, Any],
    attempt_info: Mapping[str, Any],
) -> LogResult:
    records = _select_attempt_records(
        all_records,
        manifest_info["logical_run_id"],
        attempt_info["attempt_id"],
        attempt_info["attempt_token"],
    )
    observed_seq = [record.seq for record in records]
    expected_seq = list(range(1, len(records) + 1))
    if observed_seq != expected_seq:
        _fail(
            "LOG_SEQUENCE_NOT_CONTIGUOUS",
            "Target attempt sequence must be exactly 1..N in capture order",
            expected=expected_seq,
            observed=observed_seq,
        )

    headers = [record for record in records if record.kind == "RUN_BEGIN"]
    terminals = [
        record
        for record in records
        if record.kind in {"RUN_END", "RUN_ABORT"}
    ]
    if len(headers) != 1:
        _fail(
            "RUN_BEGIN_COUNT_INVALID",
            "Target attempt must contain exactly one RUN_BEGIN",
            count=len(headers),
        )
    if len(terminals) != 1:
        _fail(
            "RUN_TERMINAL_COUNT_INVALID",
            "Target attempt must contain exactly one RUN_END or RUN_ABORT",
            count=len(terminals),
        )
    header = headers[0]
    terminal = terminals[0]
    if header.seq != 1:
        _fail(
            "RUN_BEGIN_POSITION_INVALID",
            "RUN_BEGIN must be sequence 1",
            seq=header.seq,
        )
    if terminal.seq != len(records):
        _fail(
            "RUN_TERMINAL_POSITION_INVALID",
            "Terminal record must be the final target-attempt record",
            terminal_seq=terminal.seq,
            final_seq=len(records),
        )
    if terminal.kind == "RUN_ABORT":
        code = terminal.fields.get("code")
        if not code:
            _fail(
                "RUN_ABORT_CODE_MISSING",
                "RUN_ABORT must include a non-empty code",
                seq=terminal.seq,
            )
        _fail(
            "RUN_ABORT",
            "Pine explicitly aborted the attempt",
            abort_code=code,
            seq=terminal.seq,
        )

    required_header = {
        "logical_run_token": manifest_info["logical_run_token"],
        "config_token": manifest_info["configuration_token"],
    }
    for field, expected in required_header.items():
        if field not in header.fields:
            _fail(
                "RUN_BEGIN_FIELD_MISSING",
                "RUN_BEGIN is missing a required identity token",
                field=field,
            )
        actual = _parse_exact_token(
            header.fields[field],
            field,
            "RUN_BEGIN_FIELD_INVALID",
        )
        if actual != expected:
            _fail(
                "RUN_BEGIN_TOKEN_MISMATCH",
                "RUN_BEGIN identity token does not match manifest",
                field=field,
                expected=expected,
                actual=actual,
            )
    header_hash = header.fields.get("pine_settings_hash")
    if header_hash is None:
        _fail(
            "RUN_BEGIN_FIELD_MISSING",
            "RUN_BEGIN is missing pine_settings_hash",
            field="pine_settings_hash",
        )
    if header_hash != manifest_info["pine_settings_hash"]:
        _fail(
            "RUN_BEGIN_PINE_HASH_MISMATCH",
            "RUN_BEGIN Pine-settings hash does not match manifest",
            expected=manifest_info["pine_settings_hash"],
            actual=header_hash,
        )

    config_records = [record for record in records if record.kind == "CONFIG"]
    config_keys: list[str] = []
    actual_config: dict[str, Any] = {}
    for record in config_records:
        key = record.fields.get("key")
        if key is None or "value" not in record.fields:
            _fail(
                "CONFIG_FIELD_MISSING",
                "CONFIG record must include key and value",
                seq=record.seq,
            )
        if key in actual_config:
            _fail(
                "CONFIG_DUPLICATE_KEY",
                "CONFIG contains a duplicate key",
                key=key,
            )
        if key not in manifest_info["pine_settings"]:
            _fail(
                "CONFIG_UNKNOWN_KEY",
                "CONFIG contains a key absent from manifest Pine settings",
                key=key,
            )
        config_keys.append(key)
        actual_config[key] = _coerce_config_value(
            record.fields["value"],
            manifest_info["pine_settings"][key],
            key,
        )
    expected_keys = sorted(manifest_info["pine_settings"])
    if config_keys != expected_keys:
        _fail(
            "CONFIG_KEY_ORDER_MISMATCH",
            "CONFIG keys must exactly match manifest keys in canonical order",
            expected=expected_keys,
            observed=config_keys,
        )
    if actual_config != manifest_info["pine_settings"]:
        _fail(
            "PINE_SETTINGS_MISMATCH",
            "Effective Pine CONFIG values do not match manifest settings",
            expected=manifest_info["pine_settings"],
            actual=actual_config,
        )
    actual_config_hash = canonical_hash(actual_config)
    if actual_config_hash != manifest_info["pine_settings_hash"]:
        _fail(
            "PINE_SETTINGS_HASH_MISMATCH",
            "Effective Pine CONFIG hash does not match manifest",
            expected=manifest_info["pine_settings_hash"],
            actual=actual_config_hash,
        )

    for record in records:
        if record.kind != "PROFILE":
            continue
        required_profile_fields = (
            "family",
            "effective_start_ms",
            "effective_end_ms",
            "poc_ticks",
            "vah_ticks",
            "val_ticks",
        )
        missing_profile_fields = [
            field
            for field in required_profile_fields
            if not record.fields.get(field)
        ]
        if missing_profile_fields:
            _fail(
                "PROFILE_FIELD_MISSING",
                "PROFILE record is missing required fields",
                seq=record.seq,
                missing=missing_profile_fields,
            )
        effective_start = _parse_int(
            record.fields["effective_start_ms"],
            "effective_start_ms",
            "PROFILE_FIELD_INVALID",
        )
        effective_end = _parse_int(
            record.fields["effective_end_ms"],
            "effective_end_ms",
            "PROFILE_FIELD_INVALID",
        )
        if effective_start >= effective_end:
            _fail(
                "PROFILE_INTERVAL_INVALID",
                "PROFILE effective interval must be half-open and non-empty",
                seq=record.seq,
                effective_start_ms=effective_start,
                effective_end_ms=effective_end,
            )
        for field in ("poc_ticks", "vah_ticks", "val_ticks"):
            _parse_int(
                record.fields[field],
                field,
                "PROFILE_FIELD_INVALID",
            )

    seen_entities: set[tuple[str, str]] = set()
    for record in records:
        id_field = ENTITY_ID_FIELDS.get(record.kind)
        if id_field is None:
            continue
        entity_id = record.fields.get(id_field)
        if not entity_id:
            _fail(
                "ENTITY_ID_MISSING",
                "Entity record is missing its deterministic ID",
                kind=record.kind,
                field=id_field,
                seq=record.seq,
            )
        key = (record.kind, entity_id)
        if key in seen_entities:
            _fail(
                "DUPLICATE_ENTITY_ID",
                "Entity ID appears more than once in an attempt",
                kind=record.kind,
                entity_id=entity_id,
            )
        seen_entities.add(key)

    actual_counts = {
        "profiles": sum(record.kind == "PROFILE" for record in records),
        "events": sum(record.kind == "EVENT" for record in records),
        "warnings": sum(record.severity == "WARN" for record in records),
        "errors": sum(record.severity == "ERROR" for record in records),
    }
    for field, actual in actual_counts.items():
        declared = _parse_terminal_count(terminal, field)
        if declared != actual:
            _fail(
                "TRAILER_COUNT_MISMATCH",
                "RUN_END count does not match parsed records",
                field=field,
                declared=declared,
                actual=actual,
            )
    if actual_counts["errors"]:
        _fail(
            "RUN_ERROR_RECORD",
            "Successful terminal block contains ERROR records",
            errors=actual_counts["errors"],
        )
    overflow = _parse_terminal_count(terminal, "overflow")
    if overflow != 0:
        _fail(
            "LOG_OVERFLOW",
            "RUN_END reports log overflow",
            overflow=overflow,
        )

    fp_algo = terminal.fields.get("fp_algo")
    chart_fp_raw = terminal.fields.get("chart_fp")
    profile_fp_raw = terminal.fields.get("profile_fp")
    if not fp_algo or not chart_fp_raw or not profile_fp_raw:
        _fail(
            "SOURCE_FINGERPRINT_MISSING",
            "RUN_END must contain fp_algo, chart_fp, and profile_fp",
        )
    chart_fp = _parse_exact_token(
        chart_fp_raw,
        "chart_fp",
        "SOURCE_FINGERPRINT_INVALID",
    )
    profile_fp = _parse_exact_token(
        profile_fp_raw,
        "profile_fp",
        "SOURCE_FINGERPRINT_INVALID",
    )
    chart_count = _parse_terminal_count(terminal, "chart_count")
    profile_count = _parse_terminal_count(terminal, "profile_count")
    if chart_count <= 0:
        _fail(
            "SOURCE_FINGERPRINT_COUNT_INVALID",
            "chart_count must be positive",
            chart_count=chart_count,
        )
    if profile_count <= 0:
        _fail(
            "SOURCE_FINGERPRINT_COUNT_INVALID",
            "profile_count must be positive",
            profile_count=profile_count,
        )
    source_vintage = {
        "fp_algo": fp_algo,
        "chart_count": chart_count,
        "chart_fp": chart_fp,
        "profile_count": profile_count,
        "profile_fp": profile_fp,
    }
    return LogResult(
        records=tuple(records),
        header=header,
        terminal=terminal,
        config=actual_config,
        source_vintage=source_vintage,
        payload_sha256=_canonical_payload_digest(records),
        record_counts=actual_counts,
    )


def _parse_decimal(
    raw: str,
    *,
    field: str,
    row: int,
    code: str = "CSV_NUMERIC_INVALID",
) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        _fail(
            code,
            "CSV numeric value is invalid",
            field=field,
            row=row,
            value=raw,
        )
    if not value.is_finite():
        _fail(
            code,
            "CSV numeric value must be finite",
            field=field,
            row=row,
            value=raw,
        )
    return value


def _parse_csv_time(
    raw: str,
    time_format: str,
    row: int,
    field: str,
) -> int:
    if time_format == "unix_ms":
        return _parse_int(raw, field, "CSV_TIME_INVALID")
    if time_format == "iso8601":
        candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            _fail(
                "CSV_TIME_INVALID",
                "CSV ISO-8601 timestamp is invalid",
                row=row,
                value=raw,
            )
        if parsed.tzinfo is None:
            _fail(
                "CSV_TIME_INVALID",
                "CSV ISO-8601 timestamp must include an offset",
                row=row,
                value=raw,
            )
        return int(parsed.astimezone(timezone.utc).timestamp() * 1000)
    _fail(
        "CSV_TIME_FORMAT_UNSUPPORTED",
        "chart_csv.time_format must be unix_ms or iso8601",
        time_format=time_format,
    )


def _validate_session_spec(
    sessions: Any,
) -> tuple[list[dict[str, Any]], frozenset[int]]:
    if not isinstance(sessions, list) or not sessions:
        _fail(
            "SESSION_SPEC_INVALID",
            "expected_sessions must be a non-empty array",
        )
    normalized: list[dict[str, Any]] = []
    all_times: set[int] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            _fail(
                "SESSION_SPEC_INVALID",
                "Each expected session must be an object",
                index=index,
            )
        session_id = _require_nonempty_string(
            _required(session, "session_id", "SESSION_FIELD_MISSING"),
            "session_id",
            "SESSION_FIELD_INVALID",
        )
        start_ms = _parse_int(
            _required(session, "start_ms", "SESSION_FIELD_MISSING"),
            "start_ms",
            "SESSION_FIELD_INVALID",
        )
        end_ms = _parse_int(
            _required(session, "end_ms", "SESSION_FIELD_MISSING"),
            "end_ms",
            "SESSION_FIELD_INVALID",
        )
        bar_ms = _parse_int(
            _required(session, "bar_ms", "SESSION_FIELD_MISSING"),
            "bar_ms",
            "SESSION_FIELD_INVALID",
            minimum=1,
        )
        expected_count = _parse_int(
            _required(
                session,
                "expected_count",
                "SESSION_FIELD_MISSING",
            ),
            "expected_count",
            "SESSION_FIELD_INVALID",
            minimum=1,
        )
        if start_ms >= end_ms:
            _fail(
                "SESSION_RANGE_INVALID",
                "Session start_ms must precede end_ms",
                session_id=session_id,
            )
        expected_times = list(range(start_ms, end_ms, bar_ms))
        if len(expected_times) != expected_count:
            _fail(
                "SESSION_EXPECTED_COUNT_INVALID",
                "Session expected_count disagrees with start/end/cadence",
                session_id=session_id,
                declared=expected_count,
                derived=len(expected_times),
            )
        overlap = all_times.intersection(expected_times)
        if overlap:
            _fail(
                "SESSION_OVERLAP_INVALID",
                "Expected sessions contain overlapping timestamps",
                session_id=session_id,
                overlap=sorted(overlap),
            )
        all_times.update(expected_times)
        normalized.append(
            {
                "session_id": session_id,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "bar_ms": bar_ms,
                "expected_count": expected_count,
                "expected_times": tuple(expected_times),
            }
        )
    return normalized, frozenset(all_times)


def _validate_csv_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    time_column = _require_nonempty_string(
        _required(schema, "time_column", "CSV_SCHEMA_FIELD_MISSING"),
        "time_column",
        "CSV_SCHEMA_FIELD_INVALID",
    )
    time_format = _require_nonempty_string(
        _required(schema, "time_format", "CSV_SCHEMA_FIELD_MISSING"),
        "time_format",
        "CSV_SCHEMA_FIELD_INVALID",
    )
    if time_format not in {"unix_ms", "iso8601"}:
        _fail(
            "CSV_TIME_FORMAT_UNSUPPORTED",
            "chart_csv.time_format must be unix_ms or iso8601",
            time_format=time_format,
        )
    identity_columns = _required(
        schema,
        "identity_columns",
        "CSV_SCHEMA_FIELD_MISSING",
    )
    if not isinstance(identity_columns, dict):
        _fail(
            "CSV_SCHEMA_FIELD_INVALID",
            "identity_columns must be an object",
        )
    expected_identity_names = {
        "logical_run_token",
        "attempt_token",
        "configuration_token",
    }
    if set(identity_columns) != expected_identity_names:
        _fail(
            "CSV_IDENTITY_SCHEMA_INVALID",
            "identity_columns must map exactly the three token fields",
            expected=sorted(expected_identity_names),
            actual=sorted(identity_columns),
        )
    for key, value in identity_columns.items():
        _require_nonempty_string(
            value,
            f"identity_columns.{key}",
            "CSV_IDENTITY_SCHEMA_INVALID",
        )

    value_columns = _required(
        schema,
        "value_columns",
        "CSV_SCHEMA_FIELD_MISSING",
    )
    if not isinstance(value_columns, dict) or not value_columns:
        _fail(
            "CSV_VALUE_SCHEMA_INVALID",
            "value_columns must be a non-empty object",
        )
    for column, spec in value_columns.items():
        _require_nonempty_string(
            column,
            "value_columns key",
            "CSV_VALUE_SCHEMA_INVALID",
        )
        if not isinstance(spec, dict):
            _fail(
                "CSV_VALUE_SCHEMA_INVALID",
                "Each value-column specification must be an object",
                column=column,
            )
        if not isinstance(spec.get("nullable"), bool):
            _fail(
                "CSV_VALUE_SCHEMA_INVALID",
                "Each value column must declare boolean nullable",
                column=column,
            )
        if not isinstance(spec.get("integral"), bool):
            _fail(
                "CSV_VALUE_SCHEMA_INVALID",
                "Each value column must declare boolean integral",
                column=column,
            )

    overlap_groups = _required(
        schema,
        "overlap_groups",
        "CSV_SCHEMA_FIELD_MISSING",
    )
    if not isinstance(overlap_groups, list) or not overlap_groups:
        _fail(
            "CSV_OVERLAP_SCHEMA_INVALID",
            "overlap_groups must be a non-empty array",
        )
    source_columns = _required(
        schema,
        "source_columns",
        "CSV_SCHEMA_FIELD_MISSING",
    )
    expected_source_names = {
        "chart_count",
        "chart_fp",
        "profile_count",
        "profile_fp",
        "error_mask",
    }
    if not isinstance(source_columns, dict) or set(source_columns) != expected_source_names:
        _fail(
            "CSV_SOURCE_SCHEMA_INVALID",
            "source_columns must map the four source fields and error_mask",
            expected=sorted(expected_source_names),
            actual=(
                sorted(source_columns)
                if isinstance(source_columns, dict)
                else None
            ),
        )
    for field, column in source_columns.items():
        if not isinstance(column, str) or not column:
            _fail(
                "CSV_SOURCE_SCHEMA_INVALID",
                "Every source-column name must be a non-empty string",
                field=field,
            )
        spec = value_columns.get(column)
        expected_nullable = field != "error_mask"
        if not isinstance(spec, dict) or (
            spec.get("nullable") is not expected_nullable
            or spec.get("integral") is not True
        ):
            _fail(
                "CSV_SOURCE_SCHEMA_INVALID",
                "Source fingerprints must be nullable integral columns; error_mask must be required integral",
                field=field,
                column=column,
            )
    terminal_column = _require_nonempty_string(
        _required(
            schema,
            "terminal_column",
            "CSV_SCHEMA_FIELD_MISSING",
        ),
        "terminal_column",
        "CSV_TERMINAL_SCHEMA_INVALID",
    )
    terminal_spec = value_columns.get(terminal_column)
    if (
        not isinstance(terminal_spec, dict)
        or terminal_spec.get("nullable") is not False
        or terminal_spec.get("integral") is not True
    ):
        _fail(
            "CSV_TERMINAL_SCHEMA_INVALID",
            "terminal_column must be a required integral value column",
            column=terminal_column,
        )
    return {
        "time_column": time_column,
        "time_format": time_format,
        "identity_columns": identity_columns,
        "value_columns": value_columns,
        "overlap_groups": overlap_groups,
        "source_columns": source_columns,
        "terminal_column": terminal_column,
        "na_values": set(schema.get("na_values", ["", "NaN"])),
    }


def _validate_overlap(
    csv_rows: Sequence[CsvRow],
    records: Sequence[VpxRecord],
    groups: Sequence[Any],
    value_columns: Mapping[str, Any],
) -> None:
    covered: dict[tuple[int, str], int] = {}
    overlap_columns: set[str] = set()

    for group_index, group in enumerate(groups):
        if not isinstance(group, dict):
            _fail(
                "CSV_OVERLAP_SCHEMA_INVALID",
                "Each overlap group must be an object",
                index=group_index,
            )
        kind = _require_nonempty_string(
            _required(
                group,
                "record_kind",
                "CSV_OVERLAP_SCHEMA_INVALID",
            ),
            "record_kind",
            "CSV_OVERLAP_SCHEMA_INVALID",
        )
        match = group.get("match", {})
        if not isinstance(match, dict):
            _fail(
                "CSV_OVERLAP_SCHEMA_INVALID",
                "Overlap match must be an object",
                index=group_index,
            )
        start_field = _require_nonempty_string(
            _required(
                group,
                "start_field",
                "CSV_OVERLAP_SCHEMA_INVALID",
            ),
            "start_field",
            "CSV_OVERLAP_SCHEMA_INVALID",
        )
        end_field = _require_nonempty_string(
            _required(
                group,
                "end_field",
                "CSV_OVERLAP_SCHEMA_INVALID",
            ),
            "end_field",
            "CSV_OVERLAP_SCHEMA_INVALID",
        )
        fields = _required(
            group,
            "fields",
            "CSV_OVERLAP_SCHEMA_INVALID",
        )
        if not isinstance(fields, dict) or not fields:
            _fail(
                "CSV_OVERLAP_SCHEMA_INVALID",
                "Overlap fields must be a non-empty object",
                index=group_index,
            )
        for record_field, column in fields.items():
            if column not in value_columns:
                _fail(
                    "CSV_OVERLAP_SCHEMA_INVALID",
                    "Overlap column is absent from value_columns",
                    column=column,
                )
            overlap_columns.add(column)

        matching_records = [
            record
            for record in records
            if record.kind == kind
            and all(record.fields.get(key) == str(value) for key, value in match.items())
        ]
        if not matching_records:
            _fail(
                "CSV_OVERLAP_RECORD_MISSING",
                "No Pine record matches an overlap group",
                kind=kind,
                match=match,
            )
        for record in matching_records:
            if start_field not in record.fields or end_field not in record.fields:
                _fail(
                    "CSV_OVERLAP_RECORD_INVALID",
                    "Overlap record lacks effective interval fields",
                    seq=record.seq,
                    start_field=start_field,
                    end_field=end_field,
                )
            start_ms = _parse_int(
                record.fields[start_field],
                start_field,
                "CSV_OVERLAP_RECORD_INVALID",
            )
            end_ms = _parse_int(
                record.fields[end_field],
                end_field,
                "CSV_OVERLAP_RECORD_INVALID",
            )
            if start_ms >= end_ms:
                _fail(
                    "CSV_OVERLAP_RECORD_INVALID",
                    "Overlap record effective interval is invalid",
                    seq=record.seq,
                )
            applicable_rows = [
                row
                for row in csv_rows
                if start_ms <= row.time_ms < end_ms
            ]
            if not applicable_rows:
                _fail(
                    "CSV_OVERLAP_INTERVAL_EMPTY",
                    "Overlap record covers no chart CSV rows",
                    seq=record.seq,
                )
            for record_field, column in fields.items():
                if record_field not in record.fields:
                    _fail(
                        "CSV_OVERLAP_RECORD_INVALID",
                        "Overlap record lacks a mapped value",
                        seq=record.seq,
                        field=record_field,
                    )
                expected = _parse_decimal(
                    record.fields[record_field],
                    field=record_field,
                    row=record.source_row,
                    code="CSV_OVERLAP_RECORD_INVALID",
                )
                for row in applicable_rows:
                    cell = (row.time_ms, column)
                    if cell in covered:
                        _fail(
                            "CSV_OVERLAP_MULTIPLE_RECORDS",
                            "More than one record governs a CSV overlap cell",
                            time_ms=row.time_ms,
                            column=column,
                            first_seq=covered[cell],
                            second_seq=record.seq,
                        )
                    covered[cell] = record.seq
                    actual = row.numeric[column]
                    if actual is None:
                        _fail(
                            "CSV_LOG_OVERLAP_MISMATCH",
                            "CSV overlap value is missing while log has a value",
                            time_ms=row.time_ms,
                            column=column,
                            expected=str(expected),
                            actual=None,
                        )
                    if actual != expected:
                        _fail(
                            "CSV_LOG_OVERLAP_MISMATCH",
                            "CSV value disagrees with the governing Pine record",
                            time_ms=row.time_ms,
                            column=column,
                            expected=str(expected),
                            actual=str(actual),
                        )

    for row in csv_rows:
        for column in overlap_columns:
            if row.numeric[column] is not None and (row.time_ms, column) not in covered:
                _fail(
                    "CSV_UNMATCHED_OVERLAP_VALUE",
                    "CSV contains an overlap value with no governing Pine record",
                    time_ms=row.time_ms,
                    column=column,
                )


def _validate_chart_csv(
    path: Path,
    manifest_info: Mapping[str, Any],
    attempt_info: Mapping[str, Any],
    log_result: LogResult,
) -> CsvResult:
    schema = _validate_csv_schema(manifest_info["chart_csv"])
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError:
        _fail("FILE_MISSING", "Chart-data CSV is missing", path=str(path))
    except OSError as exc:
        _fail(
            "CSV_READ_ERROR",
            "Chart-data CSV could not be opened",
            path=str(path),
            reason=str(exc),
        )

    with handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            _fail("CSV_HEADER_MISSING", "Chart-data CSV has no header")
        if len(fieldnames) != len(set(fieldnames)):
            _fail(
                "CSV_DUPLICATE_COLUMN",
                "Chart-data CSV header contains duplicate columns",
                columns=fieldnames,
            )
        required_columns = {
            schema["time_column"],
            *schema["identity_columns"].values(),
            *schema["value_columns"].keys(),
        }
        missing = sorted(required_columns.difference(fieldnames))
        if missing:
            _fail(
                "CSV_REQUIRED_COLUMN_MISSING",
                "Chart-data CSV is missing required hidden-plot columns",
                missing=missing,
            )

        expected_tokens = {
            "logical_run_token": manifest_info["logical_run_token"],
            "attempt_token": attempt_info["attempt_token"],
            "configuration_token": manifest_info["configuration_token"],
        }
        rows: list[CsvRow] = []
        seen_times: set[int] = set()
        previous_time: int | None = None
        for row_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                _fail(
                    "CSV_ROW_WIDTH_INVALID",
                    "Chart-data CSV row has more fields than its header",
                    row=row_number,
                )
            if any(value is None for value in raw_row.values()):
                _fail(
                    "CSV_ROW_WIDTH_INVALID",
                    "Chart-data CSV row has fewer fields than its header",
                    row=row_number,
                )
            time_raw = raw_row[schema["time_column"]]
            time_ms = _parse_csv_time(
                time_raw,
                schema["time_format"],
                row_number,
                schema["time_column"],
            )
            if time_ms in seen_times:
                _fail(
                    "CSV_DUPLICATE_TIMESTAMP",
                    "Chart-data CSV contains a duplicate timestamp",
                    row=row_number,
                    time_ms=time_ms,
                )
            if previous_time is not None and time_ms <= previous_time:
                _fail(
                    "CSV_TIMESTAMP_ORDER_INVALID",
                    "Chart-data CSV timestamps must be strictly ascending",
                    row=row_number,
                    previous=previous_time,
                    current=time_ms,
                )
            seen_times.add(time_ms)
            previous_time = time_ms

            for token_name, column in schema["identity_columns"].items():
                value = _parse_exact_token(
                    raw_row[column],
                    column,
                    "CSV_TOKEN_INVALID",
                )
                expected = expected_tokens[token_name]
                if value != expected:
                    _fail(
                        "CSV_TOKEN_MISMATCH",
                        "Chart-data CSV identity token does not match attempt",
                        row=row_number,
                        token=token_name,
                        expected=expected,
                        actual=value,
                    )

            numeric: dict[str, Decimal | None] = {}
            for column, spec in schema["value_columns"].items():
                raw = raw_row[column]
                if raw in schema["na_values"]:
                    if not spec["nullable"]:
                        _fail(
                            "CSV_REQUIRED_VALUE_MISSING",
                            "Required hidden-plot value is missing",
                            row=row_number,
                            column=column,
                        )
                    numeric[column] = None
                    continue
                value = _parse_decimal(
                    raw,
                    field=column,
                    row=row_number,
                )
                if spec["integral"] and value != value.to_integral_value():
                    _fail(
                        "CSV_INTEGRAL_VALUE_INVALID",
                        "Hidden-plot value must be integral",
                        row=row_number,
                        column=column,
                        value=raw,
                    )
                numeric[column] = value
            rows.append(
                CsvRow(
                    time_ms=time_ms,
                    raw=raw_row,
                    numeric=numeric,
                    source_row=row_number,
                )
            )

    if not rows:
        _fail("CSV_NO_DATA", "Chart-data CSV contains no data rows")

    sessions, expected_times = _validate_session_spec(
        manifest_info["window"]["expected_sessions"]
    )
    actual_times = {row.time_ms for row in rows}
    for session in sessions:
        expected = list(session["expected_times"])
        actual = [
            row.time_ms
            for row in rows
            if session["start_ms"] <= row.time_ms < session["end_ms"]
        ]
        if actual != expected:
            missing = sorted(set(expected).difference(actual))
            extra = sorted(set(actual).difference(expected))
            _fail(
                "SESSION_COVERAGE_MISMATCH",
                "Chart-data CSV does not contain the exact expected session cadence",
                session_id=session["session_id"],
                missing=missing,
                extra=extra,
                expected_count=len(expected),
                actual_count=len(actual),
            )
    missing_overall = sorted(expected_times.difference(actual_times))
    if missing_overall:
        _fail(
            "CSV_INTERIOR_GAP",
            "Chart-data CSV is missing expected interior timestamps",
            missing=missing_overall,
        )
    if log_result.source_vintage["chart_count"] != len(expected_times):
        _fail(
            "CHART_SOURCE_COUNT_MISMATCH",
            "RUN_END chart_count does not match expected covered chart bars",
            declared=log_result.source_vintage["chart_count"],
            actual=len(expected_times),
        )

    rows_by_time = {row.time_ms: row for row in rows}
    terminal_rows: list[CsvRow] = []
    for row in rows:
        marker = row.numeric[schema["terminal_column"]]
        if marker not in {Decimal(0), Decimal(1)}:
            _fail(
                "CSV_TERMINAL_MARKER_INVALID",
                "Terminal marker must be exactly 0 or 1",
                time_ms=row.time_ms,
                actual=None if marker is None else str(marker),
            )
        if marker == 1:
            terminal_rows.append(row)
    if len(terminal_rows) != 1:
        _fail(
            "CSV_TERMINAL_COUNT_INVALID",
            "Chart-data CSV must contain exactly one terminal marker",
            count=len(terminal_rows),
            times=[row.time_ms for row in terminal_rows],
        )
    terminal_row = terminal_rows[0]

    for field in (
        "chart_count",
        "chart_fp",
        "profile_count",
        "profile_fp",
    ):
        expected = log_result.source_vintage[field]
        column = schema["source_columns"][field]
        actual = terminal_row.numeric[column]
        if actual is None or actual != Decimal(expected):
            _fail(
                "CSV_SOURCE_FINGERPRINT_MISMATCH",
                "Terminal CSV source count/fingerprint disagrees with RUN_END",
                time_ms=terminal_row.time_ms,
                field=field,
                expected=expected,
                actual=None if actual is None else str(actual),
            )

    measurement_start = _parse_int(
        manifest_info["window"]["measurement_start_ms"],
        "measurement_start_ms",
        "WINDOW_FIELD_INVALID",
    )
    measurement_end = _parse_int(
        manifest_info["window"]["measurement_end_ms"],
        "measurement_end_ms",
        "WINDOW_FIELD_INVALID",
    )
    error_rows = [
        row
        for row in rows
        if measurement_start <= row.time_ms < measurement_end
    ]
    if terminal_row not in error_rows:
        error_rows.append(terminal_row)
    error_column = schema["source_columns"]["error_mask"]
    for row in error_rows:
        error_mask = row.numeric[error_column]
        if error_mask is None or error_mask != 0:
            _fail(
                "CSV_ERROR_MASK_NONZERO",
                "Applicable chart-data row has a run-invalidating error mask",
                time_ms=row.time_ms,
                actual=None if error_mask is None else str(error_mask),
            )

    _validate_overlap(
        rows,
        log_result.records,
        schema["overlap_groups"],
        schema["value_columns"],
    )
    return CsvResult(rows=tuple(rows), expected_times=expected_times)


def _base_acceptance_report() -> dict[str, Any]:
    return {
        "schema": "vpx.acceptance/1",
        "checker_version": CHECKER_VERSION,
        "accepted": False,
        "logical_run_id": None,
        "logical_run_token": None,
        "attempt_id": None,
        "attempt_token": None,
        "configuration_token": None,
        "pine_settings_hash": None,
        "chart_state_hash": None,
        "source_vintage": None,
        "payload_sha256": None,
        "record_counts": None,
        "csv_rows": None,
        "raw_sha256": {},
        "checks": [],
        "errors": [],
    }


def check_artifacts(
    *,
    manifest_path: str | os.PathLike[str],
    attempt_path: str | os.PathLike[str],
    logs_path: str | os.PathLike[str],
    chart_csv_path: str | os.PathLike[str],
    ui_readback_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Validate one immutable logical-run attempt.

    The function never raises ``ValidationError``. Artifact failures are
    returned in the deterministic acceptance report's ``errors`` array.
    """

    paths = {
        "manifest": Path(manifest_path),
        "attempt": Path(attempt_path),
        "pine_logs": Path(logs_path),
        "chart_data": Path(chart_csv_path),
        "ui_readback": Path(ui_readback_path),
    }
    report = _base_acceptance_report()
    try:
        # Hash every input before parsing it.
        report["raw_sha256"] = {
            label: sha256_file(path)
            for label, path in paths.items()
        }
        report["checks"].append("RAW_INPUTS_HASHED")

        manifest = _load_json(paths["manifest"], "manifest")
        manifest_info = _validate_manifest(manifest)
        report.update(
            {
                "logical_run_id": manifest_info["logical_run_id"],
                "logical_run_token": manifest_info["logical_run_token"],
                "configuration_token": manifest_info["configuration_token"],
                "pine_settings_hash": manifest_info["pine_settings_hash"],
                "chart_state_hash": manifest_info["chart_state_hash"],
            }
        )
        report["checks"].append("MANIFEST_VALID")

        attempt = _load_json(paths["attempt"], "attempt")
        attempt_info = _validate_attempt(attempt, manifest_info)
        report.update(
            {
                "attempt_id": attempt_info["attempt_id"],
                "attempt_token": attempt_info["attempt_token"],
            }
        )
        report["checks"].append("ATTEMPT_IDENTITY_VALID")

        ui = _load_json(paths["ui_readback"], "UI read-back")
        _validate_ui_readback(ui, manifest_info, attempt_info)
        report["checks"].append("UI_READBACK_VALID")

        all_records = parse_log_file(paths["pine_logs"])
        log_result = _validate_log(
            all_records,
            manifest_info,
            attempt_info,
        )
        report["source_vintage"] = dict(log_result.source_vintage)
        report["payload_sha256"] = log_result.payload_sha256
        report["record_counts"] = dict(log_result.record_counts)
        report["checks"].extend(
            [
                "LOG_IDENTITY_AND_SEQUENCE_VALID",
                "PINE_CONFIG_VALID",
                "SOURCE_FINGERPRINTS_PRESENT",
            ]
        )

        csv_result = _validate_chart_csv(
            paths["chart_data"],
            manifest_info,
            attempt_info,
            log_result,
        )
        report["csv_rows"] = len(csv_result.rows)
        report["checks"].extend(
            [
                "CSV_IDENTITY_AND_VALUES_VALID",
                "SESSION_COVERAGE_VALID",
                "LOG_CSV_OVERLAP_VALID",
            ]
        )
        report["accepted"] = True
    except ValidationError as exc:
        report["errors"].append(exc.as_dict())
    return report


def compare_reports(
    report_a: Mapping[str, Any],
    report_b: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare two accepted attempts of the same logical run."""

    result: dict[str, Any] = {
        "schema": "vpx.comparison/1",
        "checker_version": CHECKER_VERSION,
        "accepted": False,
        "status": "rejected",
        "same_vintage": None,
        "logical_run_id": None,
        "attempts": [
            report_a.get("attempt_id"),
            report_b.get("attempt_id"),
        ],
        "errors": [],
    }
    for label, report in (("A", report_a), ("B", report_b)):
        if report.get("schema") != "vpx.acceptance/1":
            result["errors"].append(
                {
                    "code": "COMPARE_SCHEMA_INVALID",
                    "message": f"Acceptance report {label} has an unsupported schema",
                }
            )
            return result
        if report.get("accepted") is not True:
            result["errors"].append(
                {
                    "code": "COMPARE_INPUT_NOT_ACCEPTED",
                    "message": f"Acceptance report {label} is not accepted",
                }
            )
            return result

    logical_run_a = report_a.get("logical_run_id")
    logical_run_b = report_b.get("logical_run_id")
    if logical_run_a != logical_run_b:
        result["errors"].append(
            {
                "code": "COMPARE_LOGICAL_RUN_MISMATCH",
                "message": "Attempts belong to different logical runs",
                "details": {
                    "logical_run_a": logical_run_a,
                    "logical_run_b": logical_run_b,
                },
            }
        )
        return result
    result["logical_run_id"] = logical_run_a

    if (
        report_a.get("attempt_id") == report_b.get("attempt_id")
        or report_a.get("attempt_token") == report_b.get("attempt_token")
    ):
        result["errors"].append(
            {
                "code": "COMPARE_ATTEMPT_NOT_DISTINCT",
                "message": "Reproducibility comparison requires two distinct attempts",
            }
        )
        return result

    specification_fields = (
        "logical_run_token",
        "configuration_token",
        "pine_settings_hash",
        "chart_state_hash",
    )
    mismatched_specification = {
        field: {
            "a": report_a.get(field),
            "b": report_b.get(field),
        }
        for field in specification_fields
        if report_a.get(field) != report_b.get(field)
    }
    if mismatched_specification:
        result["errors"].append(
            {
                "code": "COMPARE_SPECIFICATION_MISMATCH",
                "message": "Attempts have the same logical-run ID but different specifications",
                "details": mismatched_specification,
            }
        )
        return result

    vintage_a = report_a.get("source_vintage")
    vintage_b = report_b.get("source_vintage")
    if not isinstance(vintage_a, dict) or not isinstance(vintage_b, dict):
        result["errors"].append(
            {
                "code": "COMPARE_VINTAGE_MISSING",
                "message": "Accepted report lacks a source-vintage tuple",
            }
        )
        return result

    if vintage_a != vintage_b:
        result.update(
            {
                "accepted": True,
                "status": "different_vintage",
                "same_vintage": False,
                "vintage_a": vintage_a,
                "vintage_b": vintage_b,
            }
        )
        return result

    result["same_vintage"] = True
    payload_a = report_a.get("payload_sha256")
    payload_b = report_b.get("payload_sha256")
    if not payload_a or not payload_b:
        result["errors"].append(
            {
                "code": "COMPARE_PAYLOAD_DIGEST_MISSING",
                "message": "Accepted report lacks a canonical payload digest",
            }
        )
        return result
    if payload_a != payload_b:
        result["errors"].append(
            {
                "code": "SAME_VINTAGE_NONDETERMINISTIC",
                "message": "Same-vintage attempts produced different canonical payloads",
                "details": {
                    "payload_a": payload_a,
                    "payload_b": payload_b,
                },
            }
        )
        return result
    result.update(
        {
            "accepted": True,
            "status": "reproducible",
        }
    )
    return result


def _load_acceptance(path: Path) -> dict[str, Any]:
    return _load_json(path, "acceptance report")


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        sort_keys=True,
        indent=2,
        ensure_ascii=True,
        allow_nan=False,
    )
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
    except FileExistsError:
        _fail(
            "OUTPUT_EXISTS",
            "Refusing to overwrite an existing output artifact",
            path=str(path),
        )
    except OSError as exc:
        _fail(
            "OUTPUT_WRITE_ERROR",
            "Could not write output artifact",
            path=str(path),
            reason=str(exc),
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or compare Volume Profile Phase 0 artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="validate one TradingView attempt",
    )
    check.add_argument("--manifest", required=True, type=Path)
    check.add_argument("--attempt", required=True, type=Path)
    check.add_argument("--logs", required=True, type=Path)
    check.add_argument("--chart-csv", required=True, type=Path)
    check.add_argument("--ui-readback", required=True, type=Path)
    check.add_argument("--output", required=True, type=Path)

    compare = subparsers.add_parser(
        "compare",
        help="compare two accepted attempt reports",
    )
    compare.add_argument("acceptance_a", type=Path)
    compare.add_argument("acceptance_b", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "check":
        report = check_artifacts(
            manifest_path=args.manifest,
            attempt_path=args.attempt,
            logs_path=args.logs,
            chart_csv_path=args.chart_csv,
            ui_readback_path=args.ui_readback,
        )
        try:
            _write_json_exclusive(args.output, report)
        except ValidationError as exc:
            print(
                json.dumps(
                    {
                        "schema": "vpx.acceptance/1",
                        "accepted": False,
                        "errors": [exc.as_dict()],
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 2
        print(
            json.dumps(
                {
                    "accepted": report["accepted"],
                    "output": str(args.output),
                    "errors": report["errors"],
                },
                sort_keys=True,
            )
        )
        return 0 if report["accepted"] else 1

    try:
        report_a = _load_acceptance(args.acceptance_a)
        report_b = _load_acceptance(args.acceptance_b)
        comparison = compare_reports(report_a, report_b)
    except ValidationError as exc:
        comparison = {
            "schema": "vpx.comparison/1",
            "checker_version": CHECKER_VERSION,
            "accepted": False,
            "status": "rejected",
            "same_vintage": None,
            "errors": [exc.as_dict()],
        }
    print(json.dumps(comparison, sort_keys=True, indent=2))
    return 0 if comparison["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
