#!/usr/bin/env python3
"""Measure real loading screens and reach gameplay in an isolated X11 session.

Uses a disposable data directory supplied with --data; do not point it at live
saves. Templates are reviewed local captures, never game assets distributed here.
Run once with --original and again without it using the same binary/display.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from PIL import Image
from qualify_launches import Display, menu_mask, similarity


class Input:
    def __init__(self, display):
        self.display = display
        self.x = display.x
        self.d = display.display
        self.t = C.CDLL("libXtst.so.6")
        self.x.XSetInputFocus.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_ulong]
        self.x.XRaiseWindow.argtypes = [C.c_void_p, C.c_ulong]
        self.x.XTranslateCoordinates.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong,
            C.c_int, C.c_int, C.POINTER(C.c_int), C.POINTER(C.c_int), C.POINTER(C.c_ulong)]
        self.x.XStringToKeysym.argtypes = [C.c_char_p]
        self.x.XStringToKeysym.restype = C.c_ulong
        self.x.XKeysymToKeycode.argtypes = [C.c_void_p, C.c_ulong]
        self.x.XKeysymToKeycode.restype = C.c_uint
        self.x.XFlush.argtypes = [C.c_void_p]
        self.t.XTestFakeMotionEvent.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_ulong]
        self.t.XTestFakeButtonEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
        self.t.XTestFakeKeyEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]

    def click(self, px, py):
        window = self.display.windows()[-1]
        x, y, child = C.c_int(), C.c_int(), C.c_ulong()
        self.x.XRaiseWindow(self.d, window)
        self.x.XSetInputFocus(self.d, window, 1, 0)
        self.x.XTranslateCoordinates(self.d, window, self.display.root, px, py,
                                    C.byref(x), C.byref(y), C.byref(child))
        self.t.XTestFakeMotionEvent(self.d, -1, x.value, y.value, 0)
        self.t.XTestFakeButtonEvent(self.d, 1, True, 0)
        self.x.XFlush(self.d)
        time.sleep(0.07)
        self.t.XTestFakeButtonEvent(self.d, 1, False, 0)
        self.x.XFlush(self.d)

    def key(self, name, down):
        code = self.x.XKeysymToKeycode(self.d, self.x.XStringToKeysym(name.encode()))
        self.t.XTestFakeKeyEvent(self.d, code, down, 0)
        self.x.XFlush(self.d)


def mask(image, box, threshold=110):
    return [min(p) > threshold and max(p) - min(p) < 25
            for p in image.convert("RGB").crop(box).get_flattened_data()]


def benchmark(args, directory, environment):
    directory.mkdir(exist_ok=False)
    menu = menu_mask(Image.open(args.menu_template))
    hud = mask(Image.open(args.hud_template), (10, 1, 54, 62))
    loading = mask(Image.open(args.loading_template), (350, 278, 480, 317), 45)
    assert sum(hud) > 100 and sum(loading) > 100
    # A real cinematic frame was a false positive for the older corner-only
    # HUD detector. Require the complete phone icon, and reject this control.
    negative = Image.open(args.negative_template)
    assert similarity(hud, mask(negative, (10, 1, 54, 62))) < 0.8
    assert similarity(hud, mask(Image.open(args.menu_template), (10, 1, 54, 62))) < 0.8
    assert similarity(loading, mask(Image.open(args.hud_template), (350, 278, 480, 317), 45)) < 0.8
    environment = dict(environment, REDEGPC_FRAME_TRACE=str(directory / "frames.csv"))
    display = Display()
    assert not display.windows(), "Existing game on the benchmark display"
    inputs = Input(display)
    started = time.monotonic()
    process = subprocess.Popen([str(args.binary.resolve()), "run", "--windowed", "--fps"],
        cwd="/tmp", env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1)
    result = {"original_assets": args.original, "loading_spans": []}
    samples = []
    movie_finished = []

    def logs():
        with (directory / "timed.log").open("w") as log:
            for line in process.stdout:
                if "Movie playback finished:" in line:
                    movie_finished.append(time.monotonic() - started)
                log.write(f"{time.monotonic() - started:.6f} {line}")
                log.flush()

    reader = threading.Thread(target=logs)
    reader.start()
    phase = "startup"
    next_skip = 3.0
    clicked = None
    skip_count = 0
    loading_start = None
    last_saved = -1
    black_start = None
    try:
        while process.poll() is None and time.monotonic() - started < args.timeout:
            frame = display.capture()
            now = time.monotonic() - started
            if frame is None:
                time.sleep(0.01)
                continue
            is_loading = similarity(loading, mask(frame, (350, 278, 480, 317), 45)) >= 0.8
            if phase == "entering" and movie_finished and now >= movie_finished[-1]:
                pixels = list(frame.crop((80, 70, 400, 260)).get_flattened_data())
                black = sum(max(pixel) > 25 for pixel in pixels) < len(pixels) * 0.05
                if black and black_start is None:
                    black_start = now
                elif not black and black_start is not None and "movie_to_scene_seconds" not in result:
                    result["post_movie_black_seconds"] = now - black_start
                    result["movie_to_scene_seconds"] = now - movie_finished[-1]
                    frame.save(directory / "first-native-scene.png")
            is_world = similarity(hud, mask(frame, (10, 1, 54, 62))) >= 0.9
            samples.append({"seconds": now, "loading": is_loading,
                            "world": is_world, "phase": phase})
            if is_loading and loading_start is None:
                loading_start = (now, phase)
            if not is_loading and loading_start is not None:
                start, start_phase = loading_start
                result["loading_spans"].append({"phase": start_phase, "start": start,
                    "end": now, "seconds": now - start})
                loading_start = None
            if int(now * 5) != last_saved:
                frame.save(directory / f"frame-{int(now * 5):04d}.png")
                last_saved = int(now * 5)
            if phase == "startup" and similarity(menu, menu_mask(frame)) >= 0.85:
                result["menu_seconds"] = now
                frame.save(directory / "menu.png")
                time.sleep(0.2)
                inputs.click(240, 138)
                time.sleep(0.6)
                display.capture().save(directory / "difficulty.png")
                inputs.click(240, 204)
                clicked = time.monotonic() - started
                result["normal_selected_seconds"] = clicked
                phase = "entering"
                next_skip = clicked + 0.5
            elif phase == "entering" and is_world:
                result["world_seconds"] = now
                result["normal_to_world_seconds"] = now - clicked
                frame.save(directory / "world.png")
                inputs.key("w", True)
                time.sleep(0.4)
                inputs.key("w", False)
                time.sleep(6)
                display.capture().save(directory / "after-movement.png")
                inputs.key("Escape", True)
                time.sleep(0.08)
                inputs.key("Escape", False)
                time.sleep(0.5)
                display.capture().save(directory / "paused.png")
                break
            elif now >= next_skip:
                # Normal touch skips startup logos/camera, the video and native
                # cinematics. Never alter guest clocks or speed up simulation.
                if phase == "entering":
                    inputs.click(435, 45) if skip_count % 2 == 0 else inputs.click(25, 298)
                    skip_count += 1
                else:
                    inputs.click(240, 160)
                next_skip = now + 0.5
            time.sleep(0.01)
    finally:
        display.request_game_close()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        reader.join(timeout=2)
        display.close()
        result["exit_code"] = process.returncode
        (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        (directory / "samples.json").write_text(json.dumps(samples) + "\n")
    assert "world_seconds" in result, f"Did not reach gameplay: {result}"
    assert result["exit_code"] == 0, result
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path("target/release/redegpc"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--menu-template", type=Path, required=True)
    parser.add_argument("--hud-template", type=Path, required=True)
    parser.add_argument("--loading-template", type=Path, required=True)
    parser.add_argument("--negative-template", type=Path, required=True)
    parser.add_argument("--original", action="store_true")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--xvfb", type=Path)
    parser.add_argument("--display", default=":96")
    args = parser.parse_args()
    assert args.count > 0
    args.output = args.output.resolve()
    args.output.mkdir(exist_ok=False)
    # Exercise the runtime's swap policy under the user's normal driver
    # settings. Forcing vblank_mode=0 here hid desktop synchronization issues.
    environment = dict(os.environ, SDL_VIDEODRIVER="x11",
        XDG_DATA_HOME=str(args.data.resolve().parent),
        XDG_CONFIG_HOME=str(args.output / "config"),
        XDG_STATE_HOME=str(args.output / "state"))
    environment.pop("REDEGPC_TRACE", None)
    environment.pop("REDEGPC_ORIGINAL_ASSETS", None)
    if args.original:
        environment["REDEGPC_ORIGINAL_ASSETS"] = "1"
    binary_hash = hashlib.sha256(args.binary.read_bytes()).hexdigest()
    server = None
    try:
        if args.xvfb:
            os.environ["DISPLAY"] = args.display
            environment["DISPLAY"] = args.display
            with (args.output / "xvfb.log").open("w") as log:
                server = subprocess.Popen([str(args.xvfb), args.display, "-screen", "0",
                    "800x600x24", "-nolisten", "tcp"], stdout=log, stderr=subprocess.STDOUT)
            time.sleep(0.7)
            assert server.poll() is None, "Private X11 server failed to start"
        results = []
        for number in range(1, args.count + 1):
            result = benchmark(args, args.output / f"run-{number:02d}", environment)
            results.append(result)
            print(json.dumps(result), flush=True)
        summary = {"binary_sha256": binary_hash,
                   "runs": results}
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print("LOADING_BENCHMARK_PASSED")
    finally:
        if server:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
