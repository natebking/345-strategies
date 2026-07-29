#!/usr/bin/env python3
"""Fail-closed first-touch behavior evaluator for accepted VPX Phase 0 runs.

The evaluator is deliberately downstream of ``vpx_accept.py``.  It re-runs
that gate against the immutable sibling evidence, verifies that the supplied
chart-data CSV is the exact file hashed by the acceptance report, and then
measures the next one-minute RTH path around PRIOR_RTH POC, VAH, and VAL.

This module describes observed behavior.  It does not make a predictive claim,
select thresholds from the sample, or create TradingView/chart objects.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import vpx_accept


EVALUATOR_VERSION = "1.0.0"
REPORT_SCHEMA = "vpx.behavior/1"
ACCEPTANCE_SCHEMA = "vpx.acceptance/1"
MINUTE_MS = 60_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LEVEL_ORDER = ("POC", "VAH", "VAL")
DEFAULT_HORIZONS_MINUTES = (5, 15, 30, 60)
DEFAULT_REACTION_THRESHOLD_TICKS = 8
DEFAULT_BREAK_DISTANCE_TICKS = 4
DEFAULT_BREAK_CONSECUTIVE_CLOSES = 2


class BehaviorError(Exception):
    """A stable, machine-readable behavior-evidence rejection."""

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
class Bar:
    """One validated one-minute OHLC observation in integer tick units."""

    time_ms: int
    open_ticks: int
    high_ticks: int
    low_ticks: int
    close_ticks: int
    source_row: int


@dataclass(frozen=True)
class LevelZone:
    """A closed price interval used for deterministic touch tests."""

    level_type: str
    reference_ticks: int
    low_ticks: int
    high_ticks: int


@dataclass(frozen=True)
class Evidence:
    acceptance_path: Path
    chart_csv_path: Path
    manifest_path: Path
    logs_path: Path
    acceptance: Mapping[str, Any]
    manifest: Mapping[str, Any]
    profile: Mapping[str, str]
    session: Mapping[str, Any]
    output_ticks: int
    minimum_tick: Decimal
    bars: tuple[Bar, ...]


def _fail(code: str, message: str, **details: Any) -> None:
    raise BehaviorError(code, message, **details)


def _load_object(path: Path, label: str) -> dict[str, Any]:
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except FileNotFoundError:
        _fail("FILE_MISSING", "Required evidence file is missing", path=str(path))
    except OSError as exc:
        _fail(
            "FILE_READ_ERROR",
            "Required evidence file could not be read",
            path=str(path),
            reason=str(exc),
        )
    return digest.hexdigest()


def _expected_hash(
    acceptance: Mapping[str, Any],
    acceptance_path: Path,
    label: str,
) -> str:
    hashes = acceptance.get("raw_sha256")
    if not isinstance(hashes, Mapping):
        _fail(
            "RAW_HASHES_MISSING",
            "Acceptance report lacks raw artifact hashes",
            path=str(acceptance_path),
        )
    expected = hashes.get(label)
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        _fail(
            "RAW_HASH_INVALID",
            "Acceptance report lacks a valid raw artifact hash",
            path=str(acceptance_path),
            artifact=label,
        )
    return expected


def _resolve_hashed_artifact(
    *,
    acceptance: Mapping[str, Any],
    acceptance_path: Path,
    label: str,
    candidates: Sequence[Path],
) -> Path:
    expected = _expected_hash(acceptance, acceptance_path, label)
    existing: list[Path] = []
    for candidate in candidates:
        candidate = candidate.resolve()
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
            candidates=[str(path) for path in candidates],
        )
    _fail(
        "EVIDENCE_HASH_MISMATCH",
        "Evidence artifact does not match its accepted hash",
        acceptance_path=str(acceptance_path),
        artifact=label,
        expected_sha256=expected,
        candidates=[str(path) for path in existing],
    )


def _as_int(
    value: Any,
    field: str,
    code: str,
    *,
    minimum: int | None = None,
) -> int:
    if isinstance(value, bool):
        _fail(code, f"{field} must be an integer", field=field, value=value)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
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
    return parsed


def _as_decimal(value: Any, field: str, code: str) -> Decimal:
    if isinstance(value, bool):
        _fail(code, f"{field} must be numeric", field=field, value=value)
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        _fail(code, f"{field} must be numeric", field=field, value=value)
    if not parsed.is_finite():
        _fail(code, f"{field} must be finite", field=field, value=value)
    return parsed


def _parse_iso8601_ms(value: str, *, row: int, column: str) -> int:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        _fail(
            "OHLC_TIME_INVALID",
            "Chart timestamp is not valid ISO-8601",
            row=row,
            column=column,
            value=value,
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(
            "OHLC_TIME_INVALID",
            "ISO-8601 chart timestamp must include an offset",
            row=row,
            column=column,
            value=value,
        )
    utc_value = parsed.astimezone(timezone.utc)
    if utc_value.microsecond % 1000:
        _fail(
            "OHLC_TIME_INVALID",
            "Chart timestamp must have whole-millisecond precision",
            row=row,
            column=column,
            value=value,
        )
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = utc_value - epoch
    return (
        delta.days * 86_400_000
        + delta.seconds * 1000
        + delta.microseconds // 1000
    )


def _parse_time(
    value: str,
    time_format: str,
    *,
    row: int,
    column: str,
) -> int:
    if time_format == "unix_ms":
        return _as_int(value, column, "OHLC_TIME_INVALID")
    if time_format == "iso8601":
        return _parse_iso8601_ms(value, row=row, column=column)
    _fail(
        "OHLC_TIME_FORMAT_UNSUPPORTED",
        "Behavior evaluator supports unix_ms and iso8601 chart times",
        time_format=time_format,
    )


def _price_to_ticks(
    value: str,
    minimum_tick: Decimal,
    *,
    row: int,
    column: str,
) -> int:
    if value == "":
        _fail(
            "OHLC_VALUE_MISSING",
            "Measurement-window OHLC value is missing",
            row=row,
            column=column,
        )
    price = _as_decimal(value, column, "OHLC_VALUE_INVALID")
    quotient = price / minimum_tick
    integral = quotient.to_integral_value()
    if quotient != integral:
        _fail(
            "OHLC_TICK_ALIGNMENT_INVALID",
            "OHLC price is not aligned to the manifest minimum tick",
            row=row,
            column=column,
            value=value,
            minimum_tick=str(minimum_tick),
        )
    return int(integral)


def _read_session_bars(
    chart_csv_path: Path,
    manifest: Mapping[str, Any],
    session: Mapping[str, Any],
    minimum_tick: Decimal,
    price_columns: Mapping[str, str],
) -> tuple[Bar, ...]:
    chart_csv = manifest.get("chart_csv")
    if not isinstance(chart_csv, Mapping):
        _fail(
            "MANIFEST_CHART_CSV_INVALID",
            "Manifest lacks a chart_csv object",
        )
    time_column = chart_csv.get("time_column")
    time_format = chart_csv.get("time_format")
    if not isinstance(time_column, str) or not time_column:
        _fail(
            "MANIFEST_CHART_CSV_INVALID",
            "Manifest chart_csv lacks a time_column",
        )
    if not isinstance(time_format, str) or not time_format:
        _fail(
            "MANIFEST_CHART_CSV_INVALID",
            "Manifest chart_csv lacks a time_format",
        )

    start_ms = _as_int(
        session.get("start_ms"),
        "session.start_ms",
        "SESSION_INVALID",
    )
    end_ms = _as_int(
        session.get("end_ms"),
        "session.end_ms",
        "SESSION_INVALID",
    )
    expected_count = _as_int(
        session.get("expected_count"),
        "session.expected_count",
        "SESSION_INVALID",
        minimum=1,
    )
    expected_times = tuple(range(start_ms, end_ms, MINUTE_MS))
    if len(expected_times) != expected_count:
        _fail(
            "SESSION_INVALID",
            "Expected one-minute session count disagrees with its interval",
            start_ms=start_ms,
            end_ms=end_ms,
            expected_count=expected_count,
            interval_count=len(expected_times),
        )

    required_columns = {time_column, *price_columns.values()}
    rows_by_time: dict[int, Bar] = {}
    seen_times: set[int] = set()
    previous_time: int | None = None
    try:
        handle = chart_csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        _fail(
            "OHLC_CSV_READ_ERROR",
            "Chart-data CSV could not be opened for OHLC evaluation",
            path=str(chart_csv_path),
            reason=str(exc),
        )
    with handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            _fail("OHLC_HEADER_MISSING", "Chart-data CSV has no header")
        if len(fieldnames) != len(set(fieldnames)):
            _fail(
                "OHLC_DUPLICATE_COLUMN",
                "Chart-data CSV header contains duplicate columns",
                columns=fieldnames,
            )
        missing = sorted(required_columns.difference(fieldnames))
        if missing:
            _fail(
                "OHLC_COLUMN_MISSING",
                "Chart-data CSV lacks required OHLC columns",
                missing=missing,
            )
        for row_number, raw in enumerate(reader, start=2):
            if None in raw or any(value is None for value in raw.values()):
                _fail(
                    "OHLC_ROW_WIDTH_INVALID",
                    "Chart-data CSV row width disagrees with its header",
                    row=row_number,
                )
            time_ms = _parse_time(
                raw[time_column],
                time_format,
                row=row_number,
                column=time_column,
            )
            if time_ms in seen_times:
                _fail(
                    "OHLC_DUPLICATE_TIMESTAMP",
                    "Chart-data CSV contains a duplicate timestamp",
                    row=row_number,
                    time_ms=time_ms,
                )
            if previous_time is not None and time_ms <= previous_time:
                _fail(
                    "OHLC_TIMESTAMP_ORDER_INVALID",
                    "Chart-data CSV timestamps must be strictly ascending",
                    row=row_number,
                    previous_time_ms=previous_time,
                    time_ms=time_ms,
                )
            seen_times.add(time_ms)
            previous_time = time_ms
            if time_ms < start_ms or time_ms >= end_ms:
                continue
            values = {
                field: _price_to_ticks(
                    raw[column],
                    minimum_tick,
                    row=row_number,
                    column=column,
                )
                for field, column in price_columns.items()
            }
            if values["high"] < max(
                values["open"],
                values["low"],
                values["close"],
            ) or values["low"] > min(
                values["open"],
                values["high"],
                values["close"],
            ):
                _fail(
                    "OHLC_ENVELOPE_INVALID",
                    "OHLC high/low does not contain open and close",
                    row=row_number,
                    time_ms=time_ms,
                    values=values,
                )
            rows_by_time[time_ms] = Bar(
                time_ms=time_ms,
                open_ticks=values["open"],
                high_ticks=values["high"],
                low_ticks=values["low"],
                close_ticks=values["close"],
                source_row=row_number,
            )

    missing_times = [time_ms for time_ms in expected_times if time_ms not in rows_by_time]
    extra_times = sorted(set(rows_by_time).difference(expected_times))
    if missing_times or extra_times:
        _fail(
            "OHLC_SESSION_COVERAGE_INVALID",
            "One-minute OHLC path does not exactly cover the expected RTH session",
            missing_times_ms=missing_times,
            extra_times_ms=extra_times,
        )
    return tuple(rows_by_time[time_ms] for time_ms in expected_times)


def _select_attempt_records(
    records: Sequence[vpx_accept.VpxRecord],
    acceptance: Mapping[str, Any],
) -> list[vpx_accept.VpxRecord]:
    logical_run_id = acceptance.get("logical_run_id")
    attempt_id = acceptance.get("attempt_id")
    attempt_token = acceptance.get("attempt_token")
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
            "Accepted Pine Logs contain no records for the accepted attempt",
            logical_run_id=logical_run_id,
            attempt_id=attempt_id,
            attempt_token=attempt_token,
        )
    return selected


def _extract_profile(
    records: Sequence[vpx_accept.VpxRecord],
) -> Mapping[str, str]:
    profiles = [
        record.fields
        for record in records
        if record.kind == "PROFILE"
        and record.fields.get("family") == "PRIOR_RTH"
    ]
    if len(profiles) != 1:
        _fail(
            "PRIOR_RTH_PROFILE_COUNT_INVALID",
            "Exactly one accepted PRIOR_RTH profile is required",
            count=len(profiles),
        )
    profile = profiles[0]
    if profile.get("complete") != "1":
        _fail(
            "PRIOR_RTH_PROFILE_INCOMPLETE",
            "PRIOR_RTH profile must explicitly report complete=1",
            complete=profile.get("complete"),
        )
    for field in (
        "profile_id",
        "effective_start_ms",
        "effective_end_ms",
        "source_start_ms",
        "source_end_ms",
        "poc_ticks",
        "vah_ticks",
        "val_ticks",
    ):
        if not profile.get(field):
            _fail(
                "PRIOR_RTH_PROFILE_FIELD_MISSING",
                "PRIOR_RTH profile lacks required behavior evidence",
                field=field,
            )
    return profile


def _load_evidence(
    acceptance_path: Path,
    chart_csv_path: Path,
    price_columns: Mapping[str, str],
) -> Evidence:
    acceptance_path = acceptance_path.resolve()
    chart_csv_path = chart_csv_path.resolve()
    acceptance = _load_object(acceptance_path, "acceptance report")
    if acceptance.get("schema") != ACCEPTANCE_SCHEMA:
        _fail(
            "ACCEPTANCE_SCHEMA_UNSUPPORTED",
            "Input is not a supported Phase 0 acceptance report",
            schema=acceptance.get("schema"),
        )
    if acceptance.get("accepted") is not True:
        _fail(
            "ACCEPTANCE_REQUIRED",
            "Behavior evaluation requires an accepted input report",
            path=str(acceptance_path),
        )

    chart_csv = _resolve_hashed_artifact(
        acceptance=acceptance,
        acceptance_path=acceptance_path,
        label="chart_data",
        candidates=(chart_csv_path,),
    )
    manifest_path = _resolve_hashed_artifact(
        acceptance=acceptance,
        acceptance_path=acceptance_path,
        label="manifest",
        candidates=(
            acceptance_path.parent / "manifest.json",
            acceptance_path.parent.parent / "manifest.json",
        ),
    )
    attempt_path = _resolve_hashed_artifact(
        acceptance=acceptance,
        acceptance_path=acceptance_path,
        label="attempt",
        candidates=(acceptance_path.parent / "attempt.json",),
    )
    logs_path = _resolve_hashed_artifact(
        acceptance=acceptance,
        acceptance_path=acceptance_path,
        label="pine_logs",
        candidates=(
            acceptance_path.parent / "raw" / "pine_logs.csv",
            acceptance_path.parent / "raw" / "pine_logs.txt",
            acceptance_path.parent / "pine_logs.csv",
            acceptance_path.parent / "pine_logs.txt",
        ),
    )
    ui_path = _resolve_hashed_artifact(
        acceptance=acceptance,
        acceptance_path=acceptance_path,
        label="ui_readback",
        candidates=(
            acceptance_path.parent / "ui_readback.json",
            acceptance_path.parent / "raw" / "ui_readback.json",
        ),
    )

    recomputed = vpx_accept.check_artifacts(
        manifest_path=manifest_path,
        attempt_path=attempt_path,
        logs_path=logs_path,
        chart_csv_path=chart_csv,
        ui_readback_path=ui_path,
    )
    if recomputed.get("accepted") is not True:
        _fail(
            "ACCEPTANCE_REVALIDATION_FAILED",
            "Current acceptance gate rejects the resolved evidence",
            errors=recomputed.get("errors"),
        )
    if recomputed != acceptance:
        _fail(
            "ACCEPTANCE_REPORT_TAMPERED",
            "Stored acceptance report differs from a fresh deterministic check",
            stored_report_sha256=vpx_accept.canonical_hash(acceptance),
            recomputed_report_sha256=vpx_accept.canonical_hash(recomputed),
        )

    manifest = _load_object(manifest_path, "logical-run manifest")
    chart_state = manifest.get("chart_state")
    if not isinstance(chart_state, Mapping):
        _fail(
            "MANIFEST_CHART_STATE_INVALID",
            "Manifest lacks a chart_state object",
        )
    if str(chart_state.get("chart_timeframe")) != "1":
        _fail(
            "ONE_MINUTE_CHART_REQUIRED",
            "First-touch evaluation requires accepted one-minute chart data",
            chart_timeframe=chart_state.get("chart_timeframe"),
        )
    if str(chart_state.get("calculation_timeframe")) != "1":
        _fail(
            "ONE_MINUTE_SOURCE_REQUIRED",
            "First-touch evaluation requires a one-minute calculation source",
            calculation_timeframe=chart_state.get("calculation_timeframe"),
        )

    market = manifest.get("market")
    if not isinstance(market, Mapping):
        _fail("MANIFEST_MARKET_INVALID", "Manifest lacks a market object")
    minimum_tick = _as_decimal(
        market.get("minimum_tick"),
        "market.minimum_tick",
        "MANIFEST_MINIMUM_TICK_INVALID",
    )
    if minimum_tick <= 0:
        _fail(
            "MANIFEST_MINIMUM_TICK_INVALID",
            "Manifest minimum tick must be positive",
            minimum_tick=str(minimum_tick),
        )

    pine_settings = manifest.get("pine_settings")
    if not isinstance(pine_settings, Mapping):
        _fail(
            "MANIFEST_PINE_SETTINGS_INVALID",
            "Manifest lacks pine_settings",
        )
    output_ticks = _as_int(
        pine_settings.get("output_ticks"),
        "pine_settings.output_ticks",
        "OUTPUT_TICKS_INVALID",
        minimum=1,
    )

    window = manifest.get("window")
    if not isinstance(window, Mapping):
        _fail("MANIFEST_WINDOW_INVALID", "Manifest lacks a window object")
    sessions = window.get("expected_sessions")
    if not isinstance(sessions, list) or len(sessions) != 1:
        _fail(
            "SESSION_COUNT_INVALID",
            "Behavior evaluation requires exactly one expected RTH session",
            count=len(sessions) if isinstance(sessions, list) else None,
        )
    session = sessions[0]
    if not isinstance(session, Mapping):
        _fail("SESSION_INVALID", "Expected RTH session must be an object")
    bar_ms = _as_int(
        session.get("bar_ms"),
        "session.bar_ms",
        "SESSION_INVALID",
        minimum=1,
    )
    if bar_ms != MINUTE_MS:
        _fail(
            "ONE_MINUTE_SESSION_REQUIRED",
            "Behavior evaluation requires one-minute RTH bars",
            bar_ms=bar_ms,
        )

    try:
        records = vpx_accept.parse_log_file(logs_path)
    except vpx_accept.ValidationError as exc:
        _fail(
            "PINE_LOG_INVALID",
            "Accepted Pine Logs could not be parsed",
            error=exc.as_dict(),
        )
    profile = _extract_profile(_select_attempt_records(records, acceptance))
    session_start = _as_int(
        session.get("start_ms"),
        "session.start_ms",
        "SESSION_INVALID",
    )
    session_end = _as_int(
        session.get("end_ms"),
        "session.end_ms",
        "SESSION_INVALID",
    )
    effective_start = _as_int(
        profile.get("effective_start_ms"),
        "profile.effective_start_ms",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    effective_end = _as_int(
        profile.get("effective_end_ms"),
        "profile.effective_end_ms",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    source_start = _as_int(
        profile.get("source_start_ms"),
        "profile.source_start_ms",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    source_end = _as_int(
        profile.get("source_end_ms"),
        "profile.source_end_ms",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    if source_start >= source_end or source_end > effective_start:
        _fail(
            "PRIOR_RTH_SOURCE_INTERVAL_INVALID",
            "PRIOR_RTH source must be complete before its effective session",
            source_interval=[source_start, source_end],
            effective_start_ms=effective_start,
        )
    if (effective_start, effective_end) != (session_start, session_end):
        _fail(
            "PROFILE_SESSION_MISMATCH",
            "PRIOR_RTH effective interval does not equal the next RTH path",
            profile_interval=[effective_start, effective_end],
            session_interval=[session_start, session_end],
        )

    bars = _read_session_bars(
        chart_csv,
        manifest,
        session,
        minimum_tick,
        price_columns,
    )
    return Evidence(
        acceptance_path=acceptance_path,
        chart_csv_path=chart_csv,
        manifest_path=manifest_path,
        logs_path=logs_path,
        acceptance=acceptance,
        manifest=manifest,
        profile=profile,
        session=session,
        output_ticks=output_ticks,
        minimum_tick=minimum_tick,
        bars=bars,
    )


def _utc_text(time_ms: int | None) -> str | None:
    if time_ms is None:
        return None
    return (
        datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _zones(profile: Mapping[str, str], output_ticks: int) -> tuple[LevelZone, ...]:
    poc = _as_int(
        profile["poc_ticks"],
        "profile.poc_ticks",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    vah = _as_int(
        profile["vah_ticks"],
        "profile.vah_ticks",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    val = _as_int(
        profile["val_ticks"],
        "profile.val_ticks",
        "PRIOR_RTH_PROFILE_INVALID",
    )
    if not val <= poc <= vah:
        _fail(
            "PRIOR_RTH_LEVEL_ORDER_INVALID",
            "PRIOR_RTH levels must satisfy VAL <= POC <= VAH",
            val_ticks=val,
            poc_ticks=poc,
            vah_ticks=vah,
        )
    poc_low = poc - output_ticks // 2
    return (
        LevelZone("POC", poc, poc_low, poc_low + output_ticks),
        LevelZone("VAH", vah, vah - output_ticks, vah),
        LevelZone("VAL", val, val, val + output_ticks),
    )


def _side(price_ticks: int, zone: LevelZone) -> str:
    if price_ticks < zone.low_ticks:
        return "below"
    if price_ticks > zone.high_ticks:
        return "above"
    return "inside"


def _entry(
    bars: Sequence[Bar],
    touch_index: int,
    zone: LevelZone,
) -> tuple[str, str, int]:
    bar = bars[touch_index]
    open_side = _side(bar.open_ticks, zone)
    if touch_index == 0:
        if open_side == "above":
            return "from_above", "session_open", bar.open_ticks
        if open_side == "below":
            return "from_below", "session_open", bar.open_ticks
        return "opened_inside", "session_open", bar.open_ticks

    prior_close = bars[touch_index - 1].close_ticks
    prior_side = _side(prior_close, zone)
    if (
        {prior_side, open_side} == {"above", "below"}
        and prior_side != open_side
    ):
        return "gap_through_unobserved", "prior_close_to_bar_open", prior_close
    if open_side == "above":
        return "from_above", "touch_bar_open", bar.open_ticks
    if open_side == "below":
        return "from_below", "touch_bar_open", bar.open_ticks
    if prior_side == "above":
        return "from_above", "gap_into_zone_from_prior_close", prior_close
    if prior_side == "below":
        return "from_below", "gap_into_zone_from_prior_close", prior_close
    return "opened_inside", "prior_close_and_bar_open_inside", prior_close


def _first_true_time(
    bars: Sequence[Bar],
    predicate: Any,
) -> int | None:
    for bar in bars:
        if predicate(bar):
            return bar.time_ms
    return None


def _close_run_metrics(
    bars: Sequence[Bar],
    predicate: Any,
    required: int,
) -> dict[str, Any]:
    total = 0
    longest = 0
    run = 0
    first_bar_ms: int | None = None
    confirmation_bar_ms: int | None = None
    for bar in bars:
        if predicate(bar):
            total += 1
            run += 1
            longest = max(longest, run)
            if first_bar_ms is None:
                first_bar_ms = bar.time_ms
            if run >= required and confirmation_bar_ms is None:
                confirmation_bar_ms = bar.time_ms
        else:
            run = 0
    return {
        "count": total,
        "max_consecutive": longest,
        "first_bar_start_ms": first_bar_ms,
        "first_bar_start_utc": _utc_text(first_bar_ms),
        "confirmation_bar_start_ms": confirmation_bar_ms,
        "confirmation_bar_start_utc": _utc_text(confirmation_bar_ms),
        "confirmation_close_ms": (
            confirmation_bar_ms + MINUTE_MS
            if confirmation_bar_ms is not None
            else None
        ),
        "confirmation_close_utc": (
            _utc_text(confirmation_bar_ms + MINUTE_MS)
            if confirmation_bar_ms is not None
            else None
        ),
    }


def _horizon_metrics(
    *,
    bars: Sequence[Bar],
    touch_index: int,
    zone: LevelZone,
    direction: str,
    horizon_minutes: int,
    reaction_threshold_ticks: int,
    break_distance_ticks: int,
    break_consecutive_closes: int,
    session_end_ms: int,
) -> dict[str, Any]:
    touch_bar = bars[touch_index]
    target_end_ms = touch_bar.time_ms + horizon_minutes * MINUTE_MS
    window = [
        bar
        for bar in bars[touch_index:]
        if bar.time_ms < target_end_ms
    ]
    post_touch = window[1:]
    right_censored = target_end_ms > session_end_ms
    result: dict[str, Any] = {
        "horizon_minutes": horizon_minutes,
        "target_end_ms": target_end_ms,
        "target_end_utc": _utc_text(target_end_ms),
        "observed_bars_including_touch_bar": len(window),
        "post_touch_bars": len(post_touch),
        "touch_bar_excluded_from_mfe_mae": True,
        "right_censored": right_censored,
        "censoring_reason": "session_end" if right_censored else None,
        "penetration_ticks": None,
        "far_edge_breach_ticks": None,
        "mfe_ticks": None,
        "mae_ticks": None,
        "closes_beyond_zone": None,
        "closes_beyond_break_threshold": None,
        "reaction_threshold_reached": None,
        "reaction_bar_start_ms": None,
        "reaction_bar_start_utc": None,
        "acceptance_state": "not_evaluable",
        "break_state": "not_evaluable",
        "outcome_state": "direction_unavailable",
    }
    if direction not in {"from_above", "from_below"}:
        return result

    if direction == "from_above":
        minimum_low = min(bar.low_ticks for bar in window)
        penetration = max(0, zone.high_ticks - minimum_low)
        far_edge_breach = max(0, zone.low_ticks - minimum_low)
        mfe = (
            max(0, max(bar.high_ticks for bar in post_touch) - zone.high_ticks)
            if post_touch
            else None
        )
        mae = (
            max(0, zone.high_ticks - min(bar.low_ticks for bar in post_touch))
            if post_touch
            else None
        )
        beyond_zone = lambda bar: bar.close_ticks < zone.low_ticks
        beyond_break = (
            lambda bar: bar.close_ticks
            <= zone.low_ticks - break_distance_ticks
        )
        reaction = (
            lambda bar: bar.high_ticks
            >= zone.high_ticks + reaction_threshold_ticks
        )
    else:
        maximum_high = max(bar.high_ticks for bar in window)
        penetration = max(0, maximum_high - zone.low_ticks)
        far_edge_breach = max(0, maximum_high - zone.high_ticks)
        mfe = (
            max(0, zone.low_ticks - min(bar.low_ticks for bar in post_touch))
            if post_touch
            else None
        )
        mae = (
            max(0, max(bar.high_ticks for bar in post_touch) - zone.low_ticks)
            if post_touch
            else None
        )
        beyond_zone = lambda bar: bar.close_ticks > zone.high_ticks
        beyond_break = (
            lambda bar: bar.close_ticks
            >= zone.high_ticks + break_distance_ticks
        )
        reaction = (
            lambda bar: bar.low_ticks
            <= zone.low_ticks - reaction_threshold_ticks
        )

    zone_close_metrics = _close_run_metrics(
        window,
        beyond_zone,
        break_consecutive_closes,
    )
    break_close_metrics = _close_run_metrics(
        window,
        beyond_break,
        break_consecutive_closes,
    )
    reaction_time = _first_true_time(post_touch, reaction)
    confirmation_time = break_close_metrics["confirmation_bar_start_ms"]
    if reaction_time is None and confirmation_time is None:
        outcome = "unresolved"
    elif reaction_time is None:
        outcome = "break_first"
    elif confirmation_time is None:
        outcome = "reaction_first"
    elif reaction_time < confirmation_time:
        outcome = "reaction_first"
    elif confirmation_time < reaction_time:
        outcome = "break_first"
    else:
        outcome = "ambiguous_same_bar"

    result.update(
        {
            "penetration_ticks": penetration,
            "far_edge_breach_ticks": far_edge_breach,
            "mfe_ticks": mfe,
            "mae_ticks": mae,
            "closes_beyond_zone": zone_close_metrics,
            "closes_beyond_break_threshold": break_close_metrics,
            "reaction_threshold_reached": reaction_time is not None,
            "reaction_bar_start_ms": reaction_time,
            "reaction_bar_start_utc": _utc_text(reaction_time),
            "acceptance_state": (
                "accepted_beyond"
                if confirmation_time is not None
                else "not_accepted_beyond"
            ),
            "break_state": (
                "confirmed"
                if confirmation_time is not None
                else "not_confirmed"
            ),
            "outcome_state": outcome,
        }
    )
    return result


def _evaluate_level(
    *,
    zone: LevelZone,
    bars: Sequence[Bar],
    horizons_minutes: Sequence[int],
    reaction_threshold_ticks: int,
    break_distance_ticks: int,
    break_consecutive_closes: int,
    session_end_ms: int,
) -> dict[str, Any]:
    touch_index: int | None = None
    for index, bar in enumerate(bars):
        if bar.high_ticks >= zone.low_ticks and bar.low_ticks <= zone.high_ticks:
            touch_index = index
            break

    result: dict[str, Any] = {
        "level_type": zone.level_type,
        "reference_ticks": zone.reference_ticks,
        "zone_low_ticks": zone.low_ticks,
        "zone_high_ticks": zone.high_ticks,
        "touch": {
            "status": "not_touched",
            "bar_index": None,
            "bar_start_ms": None,
            "bar_start_utc": None,
            "minutes_from_session_open": None,
            "entry_direction": None,
            "entry_basis": None,
            "entry_reference_ticks": None,
            "touch_bar_open_ticks": None,
            "touch_bar_high_ticks": None,
            "touch_bar_low_ticks": None,
            "touch_bar_close_ticks": None,
        },
        "horizons": [],
        "touch_search_censoring": {
            "right_censored": True,
            "reason": "no_touch_before_session_end",
            "session_end_ms": session_end_ms,
            "session_end_utc": _utc_text(session_end_ms),
        },
    }
    if touch_index is None:
        return result

    touch_bar = bars[touch_index]
    direction, basis, reference = _entry(bars, touch_index, zone)
    result["touch"] = {
        "status": "touched",
        "bar_index": touch_index,
        "bar_start_ms": touch_bar.time_ms,
        "bar_start_utc": _utc_text(touch_bar.time_ms),
        "minutes_from_session_open": touch_index,
        "entry_direction": direction,
        "entry_basis": basis,
        "entry_reference_ticks": reference,
        "touch_bar_open_ticks": touch_bar.open_ticks,
        "touch_bar_high_ticks": touch_bar.high_ticks,
        "touch_bar_low_ticks": touch_bar.low_ticks,
        "touch_bar_close_ticks": touch_bar.close_ticks,
    }
    result["touch_search_censoring"] = {
        "right_censored": False,
        "reason": None,
        "session_end_ms": session_end_ms,
        "session_end_utc": _utc_text(session_end_ms),
    }
    result["horizons"] = [
        _horizon_metrics(
            bars=bars,
            touch_index=touch_index,
            zone=zone,
            direction=direction,
            horizon_minutes=horizon,
            reaction_threshold_ticks=reaction_threshold_ticks,
            break_distance_ticks=break_distance_ticks,
            break_consecutive_closes=break_consecutive_closes,
            session_end_ms=session_end_ms,
        )
        for horizon in horizons_minutes
    ]
    return result


def _validate_policy(
    horizons_minutes: Sequence[int],
    reaction_threshold_ticks: int,
    break_distance_ticks: int,
    break_consecutive_closes: int,
) -> tuple[int, ...]:
    if not horizons_minutes:
        _fail(
            "POLICY_HORIZONS_INVALID",
            "At least one behavior horizon is required",
        )
    horizons: list[int] = []
    for value in horizons_minutes:
        parsed = _as_int(
            value,
            "horizon_minutes",
            "POLICY_HORIZONS_INVALID",
            minimum=1,
        )
        if parsed > 1440:
            _fail(
                "POLICY_HORIZONS_INVALID",
                "Behavior horizon may not exceed 1440 minutes",
                value=parsed,
            )
        horizons.append(parsed)
    if tuple(sorted(set(horizons))) != tuple(horizons):
        _fail(
            "POLICY_HORIZONS_INVALID",
            "Behavior horizons must be unique and strictly ascending",
            horizons=horizons,
        )
    _as_int(
        reaction_threshold_ticks,
        "reaction_threshold_ticks",
        "POLICY_THRESHOLD_INVALID",
        minimum=1,
    )
    _as_int(
        break_distance_ticks,
        "break_distance_ticks",
        "POLICY_THRESHOLD_INVALID",
        minimum=0,
    )
    _as_int(
        break_consecutive_closes,
        "break_consecutive_closes",
        "POLICY_THRESHOLD_INVALID",
        minimum=1,
    )
    return tuple(horizons)


def _base_report() -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "evaluator_version": EVALUATOR_VERSION,
        "accepted": False,
        "status": "rejected",
        "input": None,
        "policy": None,
        "session": None,
        "profile": None,
        "levels": [],
        "errors": [],
        "interpretation": (
            "Descriptive first-touch measurements only; no predictive or "
            "trading-performance claim."
        ),
    }


def evaluate_behavior(
    *,
    acceptance_path: str | os.PathLike[str],
    chart_csv_path: str | os.PathLike[str],
    horizons_minutes: Sequence[int] = DEFAULT_HORIZONS_MINUTES,
    reaction_threshold_ticks: int = DEFAULT_REACTION_THRESHOLD_TICKS,
    break_distance_ticks: int = DEFAULT_BREAK_DISTANCE_TICKS,
    break_consecutive_closes: int = DEFAULT_BREAK_CONSECUTIVE_CLOSES,
    open_column: str = "open",
    high_column: str = "high",
    low_column: str = "low",
    close_column: str = "close",
) -> dict[str, Any]:
    """Evaluate accepted PRIOR_RTH levels against the next one-minute RTH."""

    report = _base_report()
    try:
        horizons = _validate_policy(
            horizons_minutes,
            reaction_threshold_ticks,
            break_distance_ticks,
            break_consecutive_closes,
        )
        price_columns = {
            "open": open_column,
            "high": high_column,
            "low": low_column,
            "close": close_column,
        }
        if any(not isinstance(value, str) or not value for value in price_columns.values()):
            _fail(
                "POLICY_PRICE_COLUMNS_INVALID",
                "OHLC column names must be non-empty strings",
                columns=price_columns,
            )
        if len(set(price_columns.values())) != 4:
            _fail(
                "POLICY_PRICE_COLUMNS_INVALID",
                "OHLC column names must be distinct",
                columns=price_columns,
            )

        evidence = _load_evidence(
            Path(acceptance_path),
            Path(chart_csv_path),
            price_columns,
        )
        session_start = _as_int(
            evidence.session.get("start_ms"),
            "session.start_ms",
            "SESSION_INVALID",
        )
        session_end = _as_int(
            evidence.session.get("end_ms"),
            "session.end_ms",
            "SESSION_INVALID",
        )
        zones = _zones(evidence.profile, evidence.output_ticks)
        report.update(
            {
                "accepted": True,
                "status": "evaluated",
                "input": {
                    "acceptance_path": str(evidence.acceptance_path),
                    "acceptance_sha256": _sha256_file(evidence.acceptance_path),
                    "chart_csv_path": str(evidence.chart_csv_path),
                    "chart_csv_sha256": _sha256_file(evidence.chart_csv_path),
                    "manifest_path": str(evidence.manifest_path),
                    "manifest_sha256": _sha256_file(evidence.manifest_path),
                    "pine_logs_path": str(evidence.logs_path),
                    "pine_logs_sha256": _sha256_file(evidence.logs_path),
                    "logical_run_id": evidence.acceptance["logical_run_id"],
                    "attempt_id": evidence.acceptance["attempt_id"],
                    "attempt_token": evidence.acceptance["attempt_token"],
                },
                "policy": {
                    "source_resolution_minutes": 1,
                    "horizons_minutes": list(horizons),
                    "reaction_threshold_ticks": reaction_threshold_ticks,
                    "break_distance_ticks": break_distance_ticks,
                    "break_consecutive_closes": break_consecutive_closes,
                    "zone_policy": "profile_row_inward_closed_v1",
                    "touch_policy": "inclusive_ohlc_overlap_v1",
                    "entry_policy": "bar_open_with_gap_guard_v1",
                    "excursion_policy": (
                        "directional_from_entry_edge_excluding_touch_bar_v1"
                    ),
                    "threshold_order_policy": "first_bar_then_same_bar_ambiguous_v1",
                    "price_columns": price_columns,
                    "thresholds_preregistered_not_sample_optimized": True,
                },
                "session": {
                    "session_id": evidence.session.get("session_id"),
                    "start_ms": session_start,
                    "start_utc": _utc_text(session_start),
                    "end_ms": session_end,
                    "end_utc": _utc_text(session_end),
                    "expected_bars": evidence.session.get("expected_count"),
                    "observed_bars": len(evidence.bars),
                    "complete": True,
                    "minimum_tick": str(evidence.minimum_tick),
                },
                "profile": {
                    "profile_id": evidence.profile["profile_id"],
                    "family": "PRIOR_RTH",
                    "source_start_ms": _as_int(
                        evidence.profile["source_start_ms"],
                        "profile.source_start_ms",
                        "PRIOR_RTH_PROFILE_INVALID",
                    ),
                    "source_end_ms": _as_int(
                        evidence.profile["source_end_ms"],
                        "profile.source_end_ms",
                        "PRIOR_RTH_PROFILE_INVALID",
                    ),
                    "effective_start_ms": session_start,
                    "effective_end_ms": session_end,
                    "output_ticks": evidence.output_ticks,
                    "poc_ticks": _as_int(
                        evidence.profile["poc_ticks"],
                        "profile.poc_ticks",
                        "PRIOR_RTH_PROFILE_INVALID",
                    ),
                    "vah_ticks": _as_int(
                        evidence.profile["vah_ticks"],
                        "profile.vah_ticks",
                        "PRIOR_RTH_PROFILE_INVALID",
                    ),
                    "val_ticks": _as_int(
                        evidence.profile["val_ticks"],
                        "profile.val_ticks",
                        "PRIOR_RTH_PROFILE_INVALID",
                    ),
                },
                "levels": [
                    _evaluate_level(
                        zone=zone,
                        bars=evidence.bars,
                        horizons_minutes=horizons,
                        reaction_threshold_ticks=reaction_threshold_ticks,
                        break_distance_ticks=break_distance_ticks,
                        break_consecutive_closes=break_consecutive_closes,
                        session_end_ms=session_end,
                    )
                    for zone in zones
                ],
            }
        )
    except (BehaviorError, vpx_accept.ValidationError) as exc:
        if isinstance(exc, BehaviorError):
            report["errors"].append(exc.as_dict())
        else:
            report["errors"].append(
                {
                    "code": "ACCEPTANCE_GATE_ERROR",
                    "message": "Underlying acceptance gate raised an error",
                    "details": {"error": exc.as_dict()},
                }
            )
    return report


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item) for item in value.split(",") if item != "")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "horizons must be comma-separated integers"
        ) from exc
    if not parsed:
        raise argparse.ArgumentTypeError("at least one horizon is required")
    return parsed


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
            "Measure descriptive first-touch behavior for accepted Phase 0 "
            "PRIOR_RTH POC/VAH/VAL evidence."
        )
    )
    parser.add_argument(
        "--acceptance",
        required=True,
        type=Path,
        help="path to one accepted acceptance.json",
    )
    parser.add_argument(
        "--chart-csv",
        required=True,
        type=Path,
        help="exact chart_data.csv hashed by that acceptance report",
    )
    parser.add_argument(
        "--horizons-minutes",
        type=_parse_horizons,
        default=DEFAULT_HORIZONS_MINUTES,
        help="comma-separated fixed horizons (default: 5,15,30,60)",
    )
    parser.add_argument(
        "--reaction-threshold-ticks",
        type=int,
        default=DEFAULT_REACTION_THRESHOLD_TICKS,
        help="fixed reaction threshold in ticks (default: 8)",
    )
    parser.add_argument(
        "--break-distance-ticks",
        type=int,
        default=DEFAULT_BREAK_DISTANCE_TICKS,
        help="fixed distance beyond the far zone edge (default: 4)",
    )
    parser.add_argument(
        "--break-consecutive-closes",
        type=int,
        default=DEFAULT_BREAK_CONSECUTIVE_CLOSES,
        help="fixed consecutive-close confirmation count (default: 2)",
    )
    parser.add_argument("--open-column", default="open")
    parser.add_argument("--high-column", default="high")
    parser.add_argument("--low-column", default="low")
    parser.add_argument("--close-column", default="close")
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON report here instead of stdout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = evaluate_behavior(
        acceptance_path=args.acceptance,
        chart_csv_path=args.chart_csv,
        horizons_minutes=args.horizons_minutes,
        reaction_threshold_ticks=args.reaction_threshold_ticks,
        break_distance_ticks=args.break_distance_ticks,
        break_consecutive_closes=args.break_consecutive_closes,
        open_column=args.open_column,
        high_column=args.high_column,
        low_column=args.low_column,
        close_column=args.close_column,
    )
    try:
        _write_report(report, args.output)
    except OSError as exc:
        sys.stderr.write(f"Could not write behavior report: {exc}\n")
        return 2
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
