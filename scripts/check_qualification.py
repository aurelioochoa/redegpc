#!/usr/bin/env python3
"""Independently inspect a completed cold-launch artifact set."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

from PIL import Image
from qualify_launches import menu_mask, similarity

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
parser.add_argument("--count", type=int, default=20)
parser.add_argument("--template", type=Path, default=ROOT / "target/qualification/main-menu-template.png")
parser.add_argument("--binary", type=Path, default=ROOT / "target/release/redegpc")
args = parser.parse_args()
data = json.loads((args.directory / "launches.json").read_text())
assert data["binary_sha256"] == hashlib.sha256(args.binary.read_bytes()).hexdigest(), "Binary changed since qualification"
assert data["template_sha256"] == hashlib.sha256(args.template.read_bytes()).hexdigest(), "Template identity differs"
records = data["launches"]
assert len(records) == args.count, f"Expected {args.count} real launches, found {len(records)}"
assert [record["number"] for record in records] == list(range(1, args.count + 1))
template = menu_mask(Image.open(args.template))
assert sum(template) > 100
# Positive and negative controls exercise the same image oracle.
assert similarity(template, template) == 1
for negative in ["negative-loading.png", "negative-inventory.png"]:
    assert similarity(template, menu_mask(Image.open(ROOT / "target/qualification" / negative))) < 0.85
for record in records:
    number = record["number"]
    assert record["menu_reached"] is True and type(record["exit_code"]) is int and record["exit_code"] == 0
    assert 0 < record["loading_seconds"] < 90
    frame = Image.open(args.directory / f"menu-{number:02d}.png")
    assert frame.size == (480, 320)
    assert similarity(template, menu_mask(frame)) >= 0.85
    log = (args.directory / f"launch-{number:02d}.log").read_text()
    for required in ["- Version: 1.03.00", "- Identifier: jp.co.capcom.residentevil.en",
                     "CPU emulation begins now.", "User requested quit, exiting.", "done join"]:
        assert required in log, (number, required)
    assert "panicked at" not in log and "program has deadlocked" not in log, number
times = [record["loading_seconds"] for record in records]
print(json.dumps({"launches_verified": len(records), "loading_seconds": {
    "min": min(times), "median": statistics.median(times), "max": max(times)}}, indent=2))
print("COLD_LAUNCH_ARTIFACTS_VERIFIED")
