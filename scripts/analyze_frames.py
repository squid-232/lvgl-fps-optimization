#!/usr/bin/env python3
"""Validate timestamp cadence only; do not infer panel semantics or visual correctness."""
import argparse
import csv
import io
import json
import math
import re
import statistics
from pathlib import Path


def parse_frames(text, fmt, run=None):
    if fmt == "csv":
        if run is not None:
            raise ValueError("--run applies only to splash logs")
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
        if not reader.fieldnames or "timestamp_us" not in reader.fieldnames:
            raise ValueError("CSV requires timestamp_us column")
        values = [row["timestamp_us"] for row in reader]
    else:
        rows = []
        for line in text.splitlines():
            if "[SPLASH_FRAME_TIMES]" not in line:
                continue
            match = re.search(r"\[SPLASH_FRAME_TIMES\] us=([0-9,]+)\s*$", line)
            if not match:
                raise ValueError("Malformed frame record")
            rows.append(match[1].split(","))
        if not rows:
            raise ValueError("No frame record")
        if run is None and len(rows) != 1:
            raise ValueError("Multiple runs: select --run explicitly (1-based)")
        index = 0 if run is None else run - 1
        if index < 0 or index >= len(rows):
            raise ValueError("Requested run does not exist")
        values = rows[index]
    result = []
    for value in values:
        value = (value or "").strip()
        if not re.fullmatch(r"[0-9]+", value):
            raise ValueError("Timestamps must be nonnegative integer microseconds")
        n = int(value)
        if n > 2**63 - 1:
            raise ValueError("Timestamp out of range")
        result.append(n)
    if len(result) < 3:
        raise ValueError("At least three frames are required")
    if any(b <= a for a, b in zip(result, result[1:])):
        raise ValueError("Non-increasing timestamps: duplicate, reset or wrap")
    return result


def analyze(times, target_fps=60.0, tolerance_percent=0.2,
            max_interval_factor=1.08, expected_span_ms=None):
    if not math.isfinite(target_fps) or target_fps <= 0:
        raise ValueError("target_fps must be finite and positive")
    if not math.isfinite(tolerance_percent) or not 0 <= tolerance_percent < 100:
        raise ValueError("tolerance_percent must be in [0,100)")
    if not math.isfinite(max_interval_factor) or max_interval_factor < 1:
        raise ValueError("max_interval_factor must be finite and >=1")
    if expected_span_ms is not None and (not math.isfinite(expected_span_ms) or expected_span_ms <= 0):
        raise ValueError("expected_span_ms must be finite and positive")
    if len(times) < 3 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("At least three strictly increasing timestamps required")
    period = 1e6 / target_fps
    intervals = [b-a for a, b in zip(times, times[1:])]
    span = times[-1]-times[0]
    fps = (len(times)-1)*1e6/span
    ordered = sorted(intervals)
    over = [i for i, dt in enumerate(intervals) if dt > period*max_interval_factor]
    coverage = None if expected_span_ms is None else span + period >= expected_span_ms*1000
    cadence = abs(fps-target_fps) <= target_fps*tolerance_percent/100 and not over
    return {
        "schema_version": 1,
        "scope": "input timestamp cadence only; panel event semantics, phase timing, visual output and lifecycle are NOT verified",
        "cadence_status": "PASS" if cadence else "FAIL",
        "coverage_status": "NOT_CHECKED" if coverage is None else "PASS" if coverage else "FAIL",
        "accepted": cadence and coverage is not False,
        "limits": {"target_fps": target_fps, "tolerance_percent": tolerance_percent,
                   "max_interval_factor": max_interval_factor, "expected_span_ms": expected_span_ms},
        "frames": len(times), "first_frame_us": times[0], "last_frame_us": times[-1],
        "span_ms": span/1000, "cadence_fps": fps,
        "interval_us": {"min": min(intervals), "median": statistics.median(intervals),
                        "p95": ordered[math.ceil(len(ordered)*0.95)-1], "max": max(intervals)},
        "over_budget_intervals": [{"after_frame": i+1, "interval_us": intervals[i]} for i in over],
        "note": "Cadence excludes initial latency and cleanup. Compute whole-window FPS separately using measured window boundaries. No slow frames were discarded."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("auto", "csv", "splash"), default="auto")
    parser.add_argument("--run", type=int)
    parser.add_argument("--target-fps", type=float, default=60)
    parser.add_argument("--tolerance-percent", type=float, default=0.2)
    parser.add_argument("--max-interval-factor", type=float, default=1.08)
    parser.add_argument("--expected-span-ms", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output and args.output.resolve() == args.input.resolve():
            raise ValueError("Output must not overwrite input log")
        fmt = ("csv" if args.input.suffix.lower() == ".csv" else "splash") if args.format == "auto" else args.format
        times = parse_frames(args.input.read_text(encoding="utf-8-sig"), fmt, args.run)
        result = analyze(times, args.target_fps, args.tolerance_percent,
                         args.max_interval_factor, args.expected_span_ms)
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded+"\n", encoding="utf-8")
        print(encoded)
        return 0 if result["accepted"] else 1
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
