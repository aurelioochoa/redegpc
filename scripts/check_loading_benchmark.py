#!/usr/bin/env python3
"""Recount measured loading and inspect actual gameplay/frame artifacts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

from PIL import Image
from benchmark_loading import mask
from qualify_launches import similarity


def read_suite(directory, hud):
    summary = json.loads((directory / "summary.json").read_text())
    assert len(summary["runs"]) >= 2, "Need repeated real runs"
    measured = []
    pacing = []
    for index, record in enumerate(summary["runs"], 1):
        run = directory / f"run-{index:02d}"
        assert record == json.loads((run / "result.json").read_text())
        assert record["exit_code"] == 0
        assert record["menu_seconds"] < record["normal_selected_seconds"] < record["world_seconds"]
        for name in ["world.png", "after-movement.png"]:
            frame = Image.open(run / name)
            assert similarity(hud, mask(frame, (10, 1, 54, 62))) >= 0.9, (run, name)
        assert (run / "world.png").read_bytes() != (run / "after-movement.png").read_bytes()
        assert Image.open(run / "paused.png").size == (480, 320)
        samples = json.loads((run / "samples.json").read_text())
        assert all(b["seconds"] > a["seconds"] for a, b in zip(samples, samples[1:]))
        spans = []
        start = None
        for sample in samples:
            if sample["loading"] and start is None:
                start = (sample["seconds"], sample["phase"])
            elif not sample["loading"] and start is not None:
                spans.append({"phase": start[1], "start": start[0], "end": sample["seconds"],
                              "seconds": sample["seconds"] - start[0]})
                start = None
        assert spans == record["loading_spans"]
        measured.append(sum(span["seconds"] for span in spans if span["phase"] == "entering"))
        with (run / "frames.csv").open() as file:
            frames = list(csv.DictReader(file))
        end = float(frames[-1]["elapsed_ms"])
        # The runner observes six seconds of real world rendering before
        # opening pause. Exclude the final second (pause and shutdown).
        stable = [float(row["frame_ms"]) for row in frames
                  if end - 5000 <= float(row["elapsed_ms"]) <= end - 1000]
        assert len(stable) >= 100
        ordered = sorted(stable)
        median = statistics.median(stable)
        p95 = ordered[int(len(ordered) * .95)]
        assert 15.5 <= median <= 18.5 and p95 < 25, (run, median, p95)
        pacing.append({"median_ms": median, "p95_ms": p95})
    return summary, measured, pacing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("cached", type=Path)
    parser.add_argument("--hud-template", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    hud = mask(Image.open(args.hud_template), (10, 1, 54, 62))
    original, before, _ = read_suite(args.original, hud)
    cached, after, pacing = read_suite(args.cached, hud)
    assert original["binary_sha256"] == cached["binary_sha256"]
    assert original["binary_sha256"] == hashlib.sha256(Path("target/release/redegpc").read_bytes()).hexdigest()
    assert all(r["original_assets"] for r in original["runs"])
    assert all(not r["original_assets"] for r in cached["runs"])
    assert min(before) > 1, "Original loading control was not observed"
    assert max(after) < min(before) * .35, "Measured loading reduction is insufficient"
    result = {"original_loading_seconds": before, "cached_loading_seconds": after,
              "cached_gameplay_frame_ms": pacing,
              "binary_sha256": cached["binary_sha256"]}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    print("LOADING_COMPARISON_VERIFIED")


if __name__ == "__main__":
    main()
