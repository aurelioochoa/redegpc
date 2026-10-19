#!/usr/bin/env python3
"""Capture native pages and qualify Play using a private copy of an installed game."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import tkinter as tk
from unittest.mock import patch

from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from launcher.backend import Directories, save_settings
from launcher.ui import Launcher
from qualify_launches import Display, menu_mask, similarity
from verify_launcher import pump, settled


def skip_intro(display):
    windows = display.windows()
    if not windows:
        return
    x = display.x
    x.XSetInputFocus.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_ulong]
    x.XKeysymToKeycode.argtypes = [C.c_void_p, C.c_ulong]
    x.XKeysymToKeycode.restype = C.c_uint
    x.XWarpPointer.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong,
                              C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_int, C.c_int]
    x.XFlush.argtypes = [C.c_void_p]
    xtest = C.CDLL('libXtst.so.6')
    xtest.XTestFakeButtonEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
    x.XSetInputFocus(display.display, windows[-1], 1, 0)
    # A corner click skips logos/movie without selecting a title-menu action.
    x.XWarpPointer(display.display, 0, windows[-1], 0, 0, 0, 0, 5, 5)
    for pressed in [True, False]:
        xtest.XTestFakeButtonEvent(display.display, 1, pressed, 0)
    x.XFlush(display.display)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/launcher')
    parser.add_argument('--play', action='store_true', help='Also reach the real game menu through Play')
    parser.add_argument('--template', type=Path, default=ROOT / 'target/qualification/cold-20-mouse/menu-01.png')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = ROOT / 'target/qualification/launcher'
    evidence.mkdir(parents=True, exist_ok=True)
    original = Directories.discover()
    failures, errors = [], []
    with tempfile.TemporaryDirectory(prefix='redegpc-launcher-real-') as temporary:
        base = Path(temporary)
        shutil.copytree(original.data, base / 'data/redegpc')
        env = {'XDG_DATA_HOME': str(base / 'data'), 'XDG_CONFIG_HOME': str(base / 'config'),
               'XDG_STATE_HOME': str(base / 'state'), 'SDL_VIDEODRIVER': 'x11', 'vblank_mode': '0'}
        with patch.dict(os.environ, env):
            dirs = Directories.discover()
            save_settings(dirs, {'Fullscreen': False, 'TouchMode': False, 'Volume': 0.0})
            window = tk.Tk()
            window.report_callback_exception = lambda *error: failures.append(error)
            view = Launcher(window, ROOT / 'target/release/redegpc', dirs)
            display = Display()
            with patch('launcher.ui.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)):
                try:
                    settled(window)
                    pump(window, lambda: view.session.verified or errors, timeout=30)
                    assert view.session.verified, (view.session.last_output, errors)
                    for geometry in ['1440x810', '1000x620', '1000x900', '1920x810']:
                        window.geometry(geometry + '+0+0')
                        settled(window)
                        for page in ['overview', 'achievements', 'settings', 'installation']:
                            view.navigate(page)
                            settled(window)
                            x, y = window.winfo_rootx(), window.winfo_rooty()
                            ImageGrab.grab((x, y, x + window.winfo_width(), y + window.winfo_height())).save(
                                args.output / f'{page}-{geometry}.png', optimize=True)
                    record = {'verified_real_installation': True, 'private_copy_of_saves': True,
                              'binary_sha256': hashlib.sha256(view.session.binary.read_bytes()).hexdigest(),
                              'screenshots': [str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
                                              for p in sorted(args.output.glob('*.png'))
                                              if p.name != 'installation-fullscreen.png']}
                    view.toggle_fullscreen()
                    settled(window)
                    if window.attributes('-fullscreen'):
                        assert window.winfo_width() == window.winfo_screenwidth()
                        assert window.winfo_height() == window.winfo_screenheight()
                        x, y = window.winfo_rootx(), window.winfo_rooty()
                        path = args.output / 'installation-fullscreen.png'
                        ImageGrab.grab((x, y, x + window.winfo_width(), y + window.winfo_height())).save(path, optimize=True)
                        record['launcher_fullscreen'] = [window.winfo_width(), window.winfo_height()]
                        record['screenshots'].append(str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path))
                    view.toggle_fullscreen()
                    settled(window)
                    if args.play:
                        template = menu_mask(Image.open(args.template))
                        negative = menu_mask(Image.new('RGB', (480, 320), 'black'))
                        assert sum(template) > 100 and similarity(template, negative) < .85
                        view.navigate('overview')
                        view.controls['play'].invoke()
                        assert view.session.operation == 'run'
                        start, last_skip, score = time.monotonic(), 0, 0
                        while view.session.child and time.monotonic() - start < 90:
                            pump(window)
                            capture = display.capture()
                            if capture:
                                score = similarity(template, menu_mask(capture))
                                if score >= .85:
                                    capture.save(evidence / 'game-menu.png')
                                    break
                            if capture and time.monotonic() - last_skip > 3:
                                skip_intro(display)
                                last_skip = time.monotonic()
                            time.sleep(.1)
                        assert score >= .85, (score, errors, view.session.last_output[-2000:])
                        elapsed = time.monotonic() - start
                        display.request_game_close()
                        pump(window, lambda: view.session.child is None, timeout=20)
                        assert not errors, errors
                        assert view.session.status == 'Ready to play'
                        record.update(menu_reached=True, menu_similarity=round(score, 4),
                                      launch_seconds=round(elapsed, 3), game_closed_cleanly=True)
                        (evidence / 'operation.log').write_text(view.session.last_output)
                    assert not failures and not errors, (failures, errors)
                    (evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
                    print(json.dumps(record, indent=2))
                finally:
                    if view.session.child:
                        view.session.child.stop(force=True)
                        view.session.child.process.wait(timeout=5)
                    display.close()
                    view.destroy()
    print('LAUNCHER_CAPTURE_PASSED')


if __name__ == '__main__':
    main()
