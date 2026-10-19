#!/usr/bin/env python3
"""Independently recount a completed, captured active-world qualification run."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image


def has_world_hud(image):
    image = image.convert("RGB")
    points = [(406, 33), (407, 33), (474, 33), (475, 33),
              (406, 44), (407, 44), (474, 44), (475, 44)]
    colors = [image.getpixel(point) for point in points]
    minimum = min(min(color) for color in colors)
    return (minimum >= 150
            and max(max(color) - min(color) for color in colors) <= 45
            and max(image.getpixel((409, 39))) <= minimum - 40)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--binary", type=Path,
                        default=Path(__file__).resolve().parents[1] / "target/release/redegpc")
    args = parser.parse_args()
    summary = json.loads((args.directory / "summary.json").read_text())
    if summary["passed"] is not True:
        raise SystemExit("Active-world qualification is incomplete")
    assert summary["binary_sha256"] == hashlib.sha256(args.binary.read_bytes()).hexdigest(), \
        "Evidence belongs to a different release binary"
    records = [json.loads(line) for line in
               (args.directory / "samples.jsonl").read_text().splitlines()]
    assert len(records) == summary["samples"]
    active_seconds = 0.0
    previous = None
    for record in records:
        assert record["pid"] == summary["pid"], "Process changed during the soak"
        assert isinstance(record["hud_active"], bool)
        assert all(math.isfinite(record[key]) for key in
                   ["monotonic", "elapsed_seconds", "active_seconds"])
        if previous:
            elapsed = record["monotonic"] - previous["monotonic"]
            assert elapsed > 0, "Samples are out of order"
            if previous["hud_active"] and record["hud_active"] and elapsed <= 2:
                active_seconds += elapsed
        assert abs(active_seconds - record["active_seconds"]) < 0.00001, \
            "An observation overcounts active time"
        previous = record
    assert active_seconds >= 1800, "Less than thirty active minutes"
    assert abs(active_seconds - summary["active_seconds"]) < 0.00001
    assert abs(records[-1]["elapsed_seconds"] - summary["elapsed_seconds"]) < 0.00001

    positive = negative = 0
    distinct = set()
    captures = sorted(args.directory.glob("sample-*.png"))
    assert len(captures) >= 25, "Missing periodic screenshot evidence"
    for path in captures:
        number = int(path.stem.removeprefix("sample-"))
        record = records[number]
        image = Image.open(path).convert("RGB")
        assert image.size == (480, 320)
        digest = hashlib.sha256(image.tobytes()).hexdigest()
        assert digest == record["frame_sha256"], str(path)
        is_active = has_world_hud(image)
        assert is_active == record["hud_active"], str(path)
        if is_active:
            positive += 1
            distinct.add(digest)
        else:
            negative += 1
    assert positive >= 10 and negative >= 1
    assert len(distinct) >= 5, "Active captures do not show changing frames"
    # Blank and uniformly bright windows must never count as gameplay.
    assert not has_world_hud(Image.new("RGB", (480, 320), "black"))
    assert not has_world_hud(Image.new("RGB", (480, 320), "white"))
    print(json.dumps({"active_seconds_recounted": active_seconds,
                      "samples": len(records), "positive_captures": positive,
                      "excluded_captures": negative}, indent=2))
    print("ACTIVE_WORLD_ARTIFACTS_VERIFIED")


if __name__ == "__main__":
    main()
