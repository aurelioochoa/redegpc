#!/usr/bin/env python3
"""Summarize actual REDEGPC_FRAME_TRACE samples, with an explicit phase cutoff."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("trace", type=Path)
parser.add_argument("--after", type=float, default=0, help="Discard samples before this elapsed second")
parser.add_argument("--output", type=Path)
args = parser.parse_args()
with args.trace.open() as file:
    rows = [(float(row["elapsed_ms"]), float(row["frame_ms"])) for row in csv.DictReader(file)]
samples = [interval for elapsed, interval in rows[1:] if elapsed >= args.after * 1000]
assert samples and all(math.isfinite(x) and x > 0 for x in samples), "No valid frame intervals"
ordered = sorted(samples)


def percentile(percent):
    return ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)]


result = {"source": str(args.trace), "phase_cutoff_seconds": args.after,
          "samples": len(samples), "sampled_seconds": sum(samples) / 1000,
          "average_fps": 1000 / statistics.mean(samples),
          "frame_ms": {"mean": statistics.mean(samples), "median": statistics.median(samples),
                       "p95": percentile(95), "p99": percentile(99),
                       "min": min(samples), "max": max(samples)},
          "intervals_over_33_34ms": sum(x > 33.34 for x in samples)}
text = json.dumps(result, indent=2) + "\n"
if args.output:
    args.output.write_text(text)
print(text, end="")
