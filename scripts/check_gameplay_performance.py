#!/usr/bin/env python3
"""Check repeated gameplay captures, presentation pacing and guest frame rates."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

from PIL import Image
from benchmark_loading import mask
from check_loading_benchmark import read_suite


def guest_rates(run):
    with (run / "frames.csv").open() as file:
        end = float(list(csv.DictReader(file))[-1]["elapsed_ms"]) / 1000
    rates = []
    for line in (run / "timed.log").read_text().splitlines():
        match = re.match(r"([\d.]+) .*EAGLContext .* FPS: ([\d.]+)$", line)
        if match and end - 5 <= float(match[1]) <= end - 1:
            rates.append(float(match[2]))
    assert len(rates) >= 3, (run, "Insufficient guest frame observations", rates)
    return rates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--binary", type=Path, default=Path("target/release/redegpc"))
    parser.add_argument("--hud-template", type=Path, required=True)
    parser.add_argument("--slow-control", type=Path)
    args = parser.parse_args()
    hud = mask(Image.open(args.hud_template), (10, 1, 54, 62))
    assert sum(hud) > 100, "Missing gameplay reference"
    suite, _, pacing = read_suite(args.directory, hud)
    assert suite["binary_sha256"] == hashlib.sha256(args.binary.read_bytes()).hexdigest()
    rates = []
    for index, result in enumerate(suite["runs"], 1):
        assert result["menu_seconds"] < 30, "Menu startup stalled"
        assert result["normal_to_world_seconds"] < 12, "Gameplay transition stalled"
        run = args.directory / f"run-{index:02d}"
        guest = guest_rates(run)
        assert min(guest) >= 50, (run, guest)
        rates.append(guest)
    result = {"presentation": pacing, "guest_fps": rates}
    if args.slow_control:
        control = guest_rates(args.slow_control)
        assert max(control) < 30, "Control did not reproduce the guest slowdown"
        result["slow_control_guest_fps"] = control
    print(json.dumps(result, indent=2))
    print("GAMEPLAY_PERFORMANCE_VERIFIED")


if __name__ == "__main__":
    main()
