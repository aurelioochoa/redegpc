#!/usr/bin/env python3
"""Repeated *real* graphical menu launches; requires X11 and Pillow.

The template and negative controls must be locally reviewed game captures.
No game asset is bundled. The optional drive is hidden only in each child's
mount namespace; the user's real mount remains available to other processes.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from PIL import Image


class XImage(C.Structure):
    _fields_ = [("width", C.c_int), ("height", C.c_int), ("xoffset", C.c_int),
                ("format", C.c_int), ("data", C.c_void_p), ("byte_order", C.c_int),
                ("bitmap_unit", C.c_int), ("bitmap_bit_order", C.c_int),
                ("bitmap_pad", C.c_int), ("depth", C.c_int),
                ("bytes_per_line", C.c_int), ("bits_per_pixel", C.c_int)]


class ClientMessage(C.Structure):
    _fields_ = [("type", C.c_int), ("serial", C.c_ulong), ("send_event", C.c_int),
                ("display", C.c_void_p), ("window", C.c_ulong),
                ("message_type", C.c_ulong), ("format", C.c_int), ("data", C.c_long * 5)]


class XEvent(C.Union):
    _fields_ = [("client", ClientMessage), ("padding", C.c_long * 24)]


class Display:
    def __init__(self):
        self.x = C.CDLL("libX11.so.6")
        x = self.x
        x.XOpenDisplay.argtypes = [C.c_char_p]
        x.XOpenDisplay.restype = C.c_void_p
        self.display = x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("An accessible X11 display is required")
        x.XDefaultRootWindow.argtypes = [C.c_void_p]
        x.XDefaultRootWindow.restype = C.c_ulong
        self.root = x.XDefaultRootWindow(self.display)
        x.XQueryTree.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong),
                                C.POINTER(C.c_ulong), C.POINTER(C.POINTER(C.c_ulong)),
                                C.POINTER(C.c_uint)]
        x.XFetchName.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_char_p)]
        x.XFree.argtypes = [C.c_void_p]
        x.XGetGeometry.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong),
                                  C.POINTER(C.c_int), C.POINTER(C.c_int),
                                  C.POINTER(C.c_uint), C.POINTER(C.c_uint),
                                  C.POINTER(C.c_uint), C.POINTER(C.c_uint)]
        x.XGetImage.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_int,
                               C.c_uint, C.c_uint, C.c_ulong, C.c_int]
        x.XGetImage.restype = C.POINTER(XImage)
        x.XDestroyImage.argtypes = [C.POINTER(XImage)]
        x.XCloseDisplay.argtypes = [C.c_void_p]
        handler_type = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p)
        self.error_handler = handler_type(lambda display, event: 0)
        x.XSetErrorHandler.argtypes = [handler_type]
        x.XSetErrorHandler(self.error_handler)

    def windows(self, window=None):
        window = self.root if window is None else window
        root, parent = C.c_ulong(), C.c_ulong()
        children, count = C.POINTER(C.c_ulong)(), C.c_uint()
        self.x.XQueryTree(self.display, window, C.byref(root), C.byref(parent),
                          C.byref(children), C.byref(count))
        found = []
        for index in range(count.value):
            child = children[index]
            name = C.c_char_p()
            self.x.XFetchName(self.display, child, C.byref(name))
            if name.value and b"resident evil" in name.value.lower():
                found.append(child)
            if name:
                self.x.XFree(name)
            found.extend(self.windows(child))
        if children:
            self.x.XFree(children)
        return found

    def capture(self):
        windows = self.windows()
        if not windows:
            return None
        root, px, py = C.c_ulong(), C.c_int(), C.c_int()
        width, height, border, depth = [C.c_uint() for _ in range(4)]
        if not self.x.XGetGeometry(self.display, windows[-1], C.byref(root),
                                  C.byref(px), C.byref(py), C.byref(width),
                                  C.byref(height), C.byref(border), C.byref(depth)):
            return None
        if (width.value, height.value) != (480, 320):
            return None
        image = self.x.XGetImage(self.display, windows[-1], 0, 0, width, height,
                                 C.c_ulong(-1), 2)
        if not image:
            return None
        try:
            raw = C.string_at(image.contents.data, image.contents.bytes_per_line * height.value)
            if image.contents.bits_per_pixel != 32:
                raise RuntimeError("Expected a 32-bit X11 pixel layout")
            return Image.frombytes("RGB", (width.value, height.value), raw, "raw",
                                   "BGRX", image.contents.bytes_per_line)
        finally:
            self.x.XDestroyImage(image)

    def close(self):
        self.x.XCloseDisplay(self.display)

    def request_game_close(self):
        windows = self.windows()
        if not windows:
            return
        x = self.x
        x.XInternAtom.argtypes = [C.c_void_p, C.c_char_p, C.c_int]
        x.XInternAtom.restype = C.c_ulong
        x.XSendEvent.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_long, C.POINTER(XEvent)]
        x.XFlush.argtypes = [C.c_void_p]
        protocol = x.XInternAtom(self.display, b"WM_PROTOCOLS", False)
        delete = x.XInternAtom(self.display, b"WM_DELETE_WINDOW", False)
        event = XEvent()
        event.client = ClientMessage(33, 0, 1, self.display, windows[-1], protocol,
                                     32, (C.c_long * 5)(delete, 0, 0, 0, 0))
        x.XSendEvent(self.display, windows[-1], False, 0, C.byref(event))
        x.XFlush(self.display)


def menu_mask(image):
    pixels = list(image.convert("RGB").crop((150, 123, 330, 151)).get_flattened_data())
    threshold = max((max(p) for p in pixels if max(p) - min(p) < 25), default=0) * 0.65
    return [min(p) > max(60, threshold) and max(p) - min(p) < 25 for p in pixels]


def similarity(left, right):
    count = sum(left) + sum(right)
    return 2 * sum(a and b for a, b in zip(left, right)) / count if count else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(__file__).resolve().parents[1] / "target/release/redegpc")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--negative", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--hide-drive", type=Path)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("count must be positive")
    template = menu_mask(Image.open(args.template))
    assert sum(template) > 100, "Template lacks the reviewed NEW GAME text"
    assert similarity(template, template) == 1
    for negative in args.negative:
        assert similarity(template, menu_mask(Image.open(negative))) < 0.85, str(negative)
    args.output.mkdir(parents=True, exist_ok=False)
    prefix = []
    if args.hide_drive:
        prefix = ["bwrap", "--die-with-parent", "--dev-bind", "/", "/", "--tmpfs", str(args.hide_drive.resolve()), "--"]
        assert not subprocess.check_output(prefix + ["/usr/bin/ls", "-A", str(args.hide_drive)])
    binary = args.binary.resolve()
    environment = dict(os.environ, SDL_VIDEODRIVER="x11", vblank_mode="0")
    environment.pop("REDEGPC_TRACE", None)
    results = {"binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
               "drive_hidden": str(args.hide_drive) if args.hide_drive else None,
               "template_sha256": hashlib.sha256(args.template.read_bytes()).hexdigest(),
               "negative_controls": [str(p) for p in args.negative], "launches": []}
    display = Display()
    try:
        assert not display.windows(), "Close existing game windows before qualification"
        with tempfile.TemporaryDirectory(prefix="redegpc-cwd-") as cwd:
            for number in range(1, args.count + 1):
                start = time.monotonic()
                log_path = args.output / f"launch-{number:02d}.log"
                record = {"number": number, "menu_reached": False}
                with log_path.open("wb") as log:
                    process = subprocess.Popen(prefix + [str(binary), "run", "--windowed", "--fps"],
                                               cwd=cwd, env=environment, stdout=log, stderr=log)
                    try:
                        while process.poll() is None and time.monotonic() - start < args.timeout:
                            capture = display.capture()
                            if capture and similarity(template, menu_mask(capture)) >= 0.85:
                                capture.save(args.output / f"menu-{number:02d}.png")
                                record.update(menu_reached=True, loading_seconds=round(time.monotonic() - start, 3))
                                break
                            time.sleep(0.25)
                    finally:
                        if process.poll() is None:
                            display.request_game_close()
                        try:
                            record["exit_code"] = process.wait(timeout=20)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            record["exit_code"] = process.wait()
                results["launches"].append(record)
                (args.output / "launches.json").write_text(json.dumps(results, indent=2) + "\n")
                print(json.dumps(record), flush=True)
                assert record["menu_reached"] and record["exit_code"] == 0, str(record)
                assert not display.windows(), "Previous runtime window did not close"
    finally:
        display.close()
    print("COLD_LAUNCH_QUALIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
