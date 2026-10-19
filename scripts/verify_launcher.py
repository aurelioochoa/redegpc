#!/usr/bin/env python3
"""Isolated native UI, real CLI import, and process lifecycle regression checks."""
import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from unittest.mock import patch
import zipfile

from PIL import Image, ImageDraw, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from launcher.backend import (Child, Directories, Session, load_settings, save_settings,
                              validate_settings, tail_log)
from launcher.ui import Artwork, Launcher
from launcher.desktop import ICONS, ICON_ASSETS, load_icon
from qualify_launches import Display


def pump(window, predicate=lambda: True, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        window.update()
        if predicate():
            return
        assert time.monotonic() < deadline, 'Timed out waiting for launcher'
        time.sleep(.01)


def settled(window):
    deadline = time.monotonic() + 10
    previous, stable_since = None, time.monotonic()
    while time.monotonic() < deadline:
        window.update()
        geometry = (window.winfo_width(), window.winfo_height())
        if geometry != previous:
            previous, stable_since = geometry, time.monotonic()
        elif time.monotonic() - stable_since >= .15:
            return
        time.sleep(.015)
    raise AssertionError('Window geometry did not settle')


def wheel(view, sequence, *, delta=None, count=1, inside=True):
    """Queue real Tk events over a row (including Linux button wheel events)."""
    target = view.button_pool['achievement-row-0'] if inside else view.controls['nav-achievements']
    for _ in range(count):
        options = {'x': 10, 'y': 10, 'when': 'tail'}
        if delta is not None:
            options['delta'] = delta
        target.event_generate(sequence, **options)
    settled(view.window)


def check_layout(view):
    w, h = view.canvas.winfo_width(), view.canvas.winfo_height()
    assert view.background.size == (w, h)
    # Chrome spans the window; the dossier keeps the same proportions inside it.
    assert view.point(0, 0) == (0, 0)
    assert view.point(1440, 810) == (w, h)
    _, _, body_w, body_h = view.box((740, 117, 676, 454))
    assert abs(body_w - body_h * 676 / 454) <= 2, 'Evidence must scale proportionally'
    left, top = view.point(0, 48)
    right, bottom = view.point(1440, 762)
    assert left >= 0 and right <= w and top >= 0 and bottom <= h
    assert abs(left - (w - right)) <= 1, 'Dossier must stay centered horizontally'
    assert abs(top - (h - bottom)) <= 1, 'Dossier must stay centered vertically'
    nav = view.controls['nav-overview']
    assert nav.winfo_y() == 0, 'Navigation must reach the top edge'
    assert view.controls['logs'].winfo_y() > h - 60 * view.scale
    if view.page == 'overview':
        left, top, width, height = view.box((792, 690, 430, 62))
        x1, y1, x2, y2 = view.canvas.bbox('installation-badge')
        assert left <= x1 < x2 <= left + width, 'Installation badge must fit its paper'
        assert top <= y1 < y2 <= top + height, 'Installation badge must fit its paper'
    for key, control in view.controls.items():
        assert control.winfo_x() >= 0 and control.winfo_y() >= 0, key
        assert control.winfo_x() + control.winfo_width() <= w, key
        assert control.winfo_y() + control.winfo_height() <= h, key
        for item in control.find_all():
            if control.type(item) == 'text':
                x1, y1, x2, y2 = control.bbox(item)
                assert x1 >= 0 and y1 >= 0 and x2 <= control.w and y2 <= control.h, (key, control.itemcget(item, 'text'))


def check_photo_borders():
    # Four different edge colors expose either crop direction, including after
    # rotation. The complete silhouette must remain inside its assigned bounds.
    art = Artwork()
    photo = Image.new('RGBA', (300, 200), '#333333')
    draw = ImageDraw.Draw(photo)
    edges = ['#ff0000', '#00ff00', '#0000ff', '#ffff00']
    for bounds, color in zip([(0, 0, 299, 9), (290, 0, 299, 199),
                              (0, 190, 299, 199), (0, 0, 9, 199)], edges):
        draw.rectangle(bounds, fill=color)
    art.images['border-check'] = photo
    for width, height in [(120, 300), (400, 120), (300, 200)]:
        for angle in [-7, 0, 3]:
            canvas = Image.new('RGBA', (width + 40, height + 40))
            art.paste(canvas, 'border-check', (20, 20, width, height),
                      contain=True, angle=angle)
            left, top, right, bottom = canvas.getbbox()
            assert left >= 20 and top >= 20 and right <= width + 20 and bottom <= height + 20
            colors = {color for _, color in canvas.getcolors(canvas.width * canvas.height)}
            for edge in edges:
                assert Image.new('RGBA', (1, 1), edge).getpixel((0, 0)) in colors, (width, height, angle, edge)


def fixture(path):
    info = {'CFBundleIdentifier': 'jp.co.capcom.residentevil.en',
            'CFBundleVersion': '1.03.00', 'CFBundleExecutable': 'game'}
    executable = struct.pack('<12I', 0xfeedface, 12, 6, 2, 1, 20, 0, 0x21, 20, 0, 0, 0)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in {'Info.plist': plistlib.dumps(info), 'game': executable,
                           'main.dz': b'resource fixture', 'intro.mp4': b'fixture'}.items():
            archive.writestr('Payload/game.app/' + name, data)


def main():
    check_photo_borders()
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', type=Path)
    parser.add_argument('--display', help='Use a specific X11 display for graphical checks')
    parser.add_argument('--icons-only', action='store_true', help='Run focused desktop icon and settings-layout checks')
    parser.add_argument('--require-fullscreen', action='store_true',
                        help='Fail unless a window manager enters actual fullscreen')
    args = parser.parse_args()
    if args.display:
        os.environ['DISPLAY'] = args.display
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    failures, errors = [], []
    with tempfile.TemporaryDirectory(prefix='redegpc-launcher-') as temporary:
        base = Path(temporary)
        env = {'XDG_DATA_HOME': str(base / 'data'), 'XDG_CONFIG_HOME': str(base / 'config'),
               'XDG_STATE_HOME': str(base / 'state')}
        with patch.dict(os.environ, env):
            dirs = Directories.discover()
            assert dirs.data == base / 'data/redegpc'
            with patch.dict(os.environ, {'XDG_DATA_HOME': 'relative'}):
                assert Directories.discover().data == Path.home() / '.local/share/redegpc'
            assert load_settings(dirs)['Volume'] == 1
            values = {'Fullscreen': True, 'TouchMode': True, 'Volume': .37}
            save_settings(dirs, values)
            assert load_settings(dirs) == values
            for bad in [{'Volume': float('nan')}, {'Volume': 1.5}, {'Fullscreen': 1}, {'unexpected': True}, []]:
                try:
                    validate_settings(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f'Accepted invalid preferences: {bad}')

            window = tk.Tk()
            window.report_callback_exception = lambda *exception: failures.append(exception)
            with patch('launcher.ui.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)), \
                 patch('launcher.ui.messagebox.showinfo'), \
                 patch('launcher.ui.messagebox.askyesno', return_value=True):
                view = Launcher(window, ROOT / 'target/release/redegpc', dirs)
                try:
                    settled(window)
                    assert not view.controls['play'].enabled
                    assert view.session.installation_state == 'missing'
                    view.controls['settings'].invoke()
                    assert view.page == 'settings'
                    view.controls['windowed'].invoke()
                    view.controls['desktop'].invoke()
                    view.volume.set(63)
                    view.controls['save-settings'].invoke()
                    assert load_settings(dirs) == {'Fullscreen': False, 'TouchMode': False, 'Volume': .63}
                    # Exercise the real filesystem installer through each UI option,
                    # with both home and XDG destinations isolated from the user.
                    desktop = base / 'Bureau'
                    desktop.mkdir()
                    with patch.dict(os.environ, {'HOME': str(base)}), \
                         patch('launcher.desktop.desktop_folder', return_value=desktop):
                        for key, label in ICONS:
                            view.controls['icon-' + key].invoke()
                            assert view.controls['icon-' + key].selected
                            view.controls['apply-desktop-icon'].invoke()
                            assert load_icon(dirs) == key
                            icon = dirs.data / 'icons' / f'redegpc-{key}.png'
                            assert icon.read_bytes() == (ICON_ASSETS / f'{key}.png').read_bytes()
                            entry = base / 'data/applications/redegpc.desktop'
                            shortcut = desktop / 'redegpc.desktop'
                            assert entry.read_bytes() == shortcut.read_bytes()
                            assert 'Icon=' + str(icon) in entry.read_text()
                            assert os.access(shortcut, os.X_OK)
                            if shutil.which('desktop-file-validate'):
                                subprocess.run(['desktop-file-validate', str(entry), str(shortcut)], check=True)
                        saved_entry = entry.read_bytes()
                        subprocess.run([sys.executable, ROOT / 'scripts/install_desktop.py'], check=True,
                                       stdout=subprocess.DEVNULL)
                        assert load_icon(dirs) == 'fractured-d'
                        assert entry.read_bytes() == saved_entry, 'Reinstall must preserve the icon'
                        result = subprocess.run([base / '.local/bin/redegpc', '--help'], cwd=base,
                                                capture_output=True, text=True, check=True)
                        assert 'redegpc launcher' in result.stdout
                        view.controls['icon-leon-portrait'].invoke()
                        with patch('launcher.desktop.write_file', side_effect=PermissionError('read only')):
                            view.controls['apply-desktop-icon'].invoke()
                        assert errors[-1][0] == 'Cannot set desktop icon'
                        assert load_icon(dirs) == 'fractured-d'
                        assert entry.read_bytes() == saved_entry
                        assert load_settings(dirs)['Volume'] == .63, 'Icon choices must preserve game settings'
                        errors.clear()
                    if args.icons_only:
                        for geometry in ['1440x810', '1000x620', '1280x720', '1000x900', '1920x810', '1024x768']:
                            window.geometry(geometry + '+0+0')
                            settled(window)
                            view.navigate('settings')
                            settled(window)
                            check_layout(view)
                        view.destroy()
                        window = tk.Tk()
                        window.report_callback_exception = lambda *exception: failures.append(exception)
                        view = Launcher(window, ROOT / 'target/release/redegpc', dirs)
                        settled(window)
                        assert view.desktop_icon == 'fractured-d'
                        view.navigate('settings')
                        assert view.controls['icon-fractured-d'].selected
                        assert not failures and not errors, (failures, errors)
                        print('DESKTOP_ICON_CHECKS_PASSED: three options, shortcuts, reinstall, write errors, restart and six layouts')
                        return
                    view.navigate('overview')
                    view.controls['achievements'].focus_force()
                    pump(window)
                    view.controls['achievements'].event_generate('<KeyPress-Return>')
                    pump(window)
                    assert view.page == 'achievements', 'Enter must activate the focused native control'
                    reached = set()
                    for category in ['all', 'story', 'weapons', 'challenge', 'difficulty', 'completion']:
                        view.controls['filter-' + category].invoke()
                        while True:
                            for entry in view.filtered()[view.offset:view.offset + 4]:
                                view.controls['achievement-' + entry['id']].invoke()
                                reached.add(entry['id'])
                            if not view.controls['next'].enabled:
                                break
                            view.controls['next'].invoke()
                    assert reached == {entry['id'] for entry in view.catalog}
                    view.filter_category('all')
                    rows = [view.button_pool[f'achievement-row-{i}'] for i in range(4)]
                    wheel(view, '<Button-5>')
                    assert view.offset == view.selected == 4
                    assert rows == [view.button_pool[f'achievement-row-{i}'] for i in range(4)]
                    wheel(view, '<Button-4>')
                    assert view.offset == 0
                    wheel(view, '<MouseWheel>', delta=0)
                    assert view.offset == 0, 'Zero delta must not navigate'
                    wheel(view, '<MouseWheel>', delta=-30, count=4)
                    assert view.offset == 4, 'Fractional wheel deltas must accumulate'
                    wheel(view, '<MouseWheel>', delta=-120, count=100)
                    assert view.offset == view.selected == 20
                    wheel(view, '<MouseWheel>', delta=-120, count=20)
                    assert view.offset == 20, 'End boundary must remain stable'
                    wheel(view, '<MouseWheel>', delta=120, count=100)
                    assert view.offset == view.selected == 0
                    wheel(view, '<Button-5>', count=12, inside=False)
                    assert view.offset == 0, 'Wheel outside the list must leave it alone'
                    for category in ['story', 'weapons', 'challenge', 'difficulty', 'completion']:
                        view.filter_category(category)
                        wheel(view, '<Button-5>', count=25)
                        assert view.offset == (len(view.filtered()) - 1) // 4 * 4
                        wheel(view, '<Button-4>', count=25)
                        assert view.offset == 0
                    # A pending wheel render must not restore the old filter/page.
                    view.filter_category('all')
                    row = view.button_pool['achievement-row-0']
                    row.event_generate('<Button-5>', x=10, y=10)
                    view.filter_category('completion')
                    settled(window)
                    assert view.category == 'completion' and view.offset == 0
                    view.filter_category('all')
                    row = view.button_pool['achievement-row-0']
                    row.event_generate('<Button-5>', x=10, y=10)
                    view.navigate('settings')
                    settled(window)
                    assert view.page == 'settings'
                    view.navigate('achievements')
                    view.select(0)
                    view.controls['nav-achievements'].focus_force()
                    window.event_generate('<KeyPress-Down>')
                    pump(window)
                    assert view.selected == 1
                    window.event_generate('<KeyPress-Next>')
                    pump(window)
                    assert view.offset == 4
                    window.event_generate('<Escape>')
                    pump(window)
                    assert view.page == 'overview'

                    view.navigate('installation')
                    with patch('launcher.ui.filedialog.askopenfilename', return_value=''):
                        view.controls['choose-ipa'].invoke()
                    assert view.session.child is None, 'Cancel must leave the installation untouched'
                    invalid = base / 'bad archive.ipa'
                    invalid.write_bytes(b'not a zip archive')
                    view.import_ipa(invalid)
                    pump(window, lambda: view.session.child is None)
                    assert errors and not view.session.verified
                    assert view.session.installation_state == 'import_failed'
                    ipa = base / 'game with spaces.ipa'
                    fixture(ipa)
                    digest = hashlib.sha256(ipa.read_bytes()).hexdigest()
                    view.import_ipa(ipa)
                    assert view.session.installation_state == 'importing'
                    assert not view.import_ipa(ipa), 'Overlapping operations must be rejected'
                    pump(window, lambda: view.session.child is None)
                    assert view.session.verified, view.session.last_output
                    assert view.session.installation_state == 'ready'
                    assert Session(view.session.binary, dirs).installation_state == 'pending'
                    ipa.unlink()
                    view.verify()
                    assert view.session.installation_state == 'checking'
                    pump(window, lambda: view.session.child is None)
                    assert view.session.verified, 'Imported game must work without the source archive'
                    pointer = (dirs.data / 'current.plist').read_bytes()
                    view.import_ipa(invalid)
                    pump(window, lambda: view.session.child is None)
                    assert (dirs.data / 'current.plist').read_bytes() == pointer
                    assert not view.session.verified
                    view.verify()
                    pump(window, lambda: view.session.child is None)
                    assert view.session.verified

                    for geometry in ['1440x810', '1000x620', '1280x720', '1000x900', '1920x810', '1024x768']:
                        window.geometry(geometry + '+0+0')
                        settled(window)
                        for page in ['overview', 'achievements', 'settings', 'installation']:
                            view.navigate(page)
                            settled(window)
                            check_layout(view)
                            if args.screenshots:
                                x, y = window.winfo_rootx(), window.winfo_rooty()
                                ImageGrab.grab((x, y, x + window.winfo_width(), y + window.winfo_height())).save(
                                    args.screenshots / f'{page}-{geometry}.png')
                    # F11 is launcher fullscreen; the saved game preference is independent.
                    window.focus_force()
                    settled(window)
                    before_geometry = window.geometry()
                    game_fullscreen = view.fullscreen.get()
                    window.event_generate('<KeyPress-F11>')
                    settled(window)
                    assert view.launcher_fullscreen
                    if window.attributes('-fullscreen'):
                        assert window.winfo_width() == window.winfo_screenwidth()
                        assert window.winfo_height() == window.winfo_screenheight()
                        check_layout(view)
                        if args.screenshots:
                            x, y = window.winfo_rootx(), window.winfo_rooty()
                            ImageGrab.grab((x, y, x + window.winfo_width(), y + window.winfo_height())).save(
                                args.screenshots / 'installation-fullscreen.png')
                    else:
                        assert not args.require_fullscreen, 'A fullscreen-capable window manager is required'
                        print('No fullscreen-capable window manager: checked toggle state only.')
                    window.event_generate('<Escape>')
                    settled(window)
                    assert not view.launcher_fullscreen and view.page == 'installation'
                    assert window.geometry() == before_geometry
                    assert view.fullscreen.get() == game_fullscreen
                    view.controls['launcher-fullscreen'].invoke()
                    settled(window)
                    assert view.launcher_fullscreen
                    view.controls['launcher-fullscreen'].invoke()
                    settled(window)
                    assert not view.launcher_fullscreen
                    log = dirs.logs / 'redegpc.log'
                    log.parent.mkdir(parents=True)
                    log.write_text('runtime log proof\n')
                    view.show_logs()
                    assert 'runtime log proof' in view.log_text.get('1.0', 'end')
                    log.write_text('updated log proof\n')
                    view.refresh_logs()
                    assert 'updated log proof' in view.log_text.get('1.0', 'end')
                    view.log_text.tag_add('sel', '1.0', '1.7')
                    view.refresh_logs()
                    assert view.log_text.tag_ranges('sel'), 'Unchanged refresh must preserve text selection'
                    assert len(tail_log(log, 5)) <= 5
                    view.log_window.destroy()

                    # Corruption must turn the same successful check into a failure.
                    resource = dirs.data / 'installations' / digest / 'Payload/game.app/main.dz'
                    resource.write_bytes(b'tampered')
                    view.verify()
                    pump(window, lambda: view.session.child is None)
                    assert not view.session.verified and 'hash mismatch' in view.session.last_output
                    assert view.session.installation_state == 'attention'

                    # A separate process fixture exercises long-lived game state safely.
                    fake = base / 'fake-host'
                    fake.write_text(f'#!{sys.executable}\nimport os,sys,time\n'
                                    'print("child started", flush=True)\n'
                                    'os.write(1, b"x" * 1048576)\n'
                                    'time.sleep(30)\n')
                    fake.chmod(0o755)
                    view.session.binary = fake
                    view.session.verified = True
                    view.navigate('overview')
                    view.controls['play'].invoke()
                    assert view.session.operation == 'run'
                    assert view.session.installation_state == 'running'
                    assert not view.controls['play'].enabled
                    view.navigate('settings')
                    assert not view.controls['save-settings'].enabled
                    child = view.session.child
                    view.close()
                    pump(window, lambda: child.process.poll() is not None)
                    assert child.process.returncode is not None
                finally:
                    if view.session.child:
                        view.session.child.stop(force=True)
                    try:
                        if window.winfo_exists():
                            view.destroy()
                    except tk.TclError:
                        pass
            assert not failures, failures

            # Malformed XML is reported and repair is an explicit settings action.
            settings_file = dirs.config / 'settings.plist'
            settings_file.write_bytes(b'<?xml version="1.0"?><plist><dict>')
            window = tk.Tk()
            window.report_callback_exception = lambda *exception: failures.append(exception)
            # Empty data avoids an unrelated check while testing settings repair.
            repair_dirs = Directories(base / 'empty-data', dirs.config, dirs.logs)
            view = Launcher(window, ROOT / 'target/release/redegpc', repair_dirs)
            try:
                settled(window)
                assert view.desktop_icon == 'fractured-d', 'Desktop icon must survive launcher restart'
                assert view.settings_error and settings_file.read_bytes().endswith(b'<dict>')
                view.navigate('settings')
                assert not view.controls['save-settings'].enabled
                view.controls['reset-settings'].invoke()
                assert not view.settings_error
                assert load_settings(dirs) == {'Fullscreen': False, 'TouchMode': False, 'Volume': 1.0}
                view.session.binary = base / 'missing-binary'
                with patch('launcher.ui.messagebox.showerror') as error:
                    assert not view.verify()
                    assert error.called and view.session.child is None
            finally:
                view.destroy()

            # Reader must drain a large, newline-free pipe without blocking.
            child = Child([sys.executable, '-c', 'import os; os.write(1, b"x" * 2097152); print("END")'])
            deadline = time.monotonic() + 5
            output = ''
            while True:
                chunk, code = child.poll()
                output = (output + chunk)[-65536:]
                if code is not None:
                    break
                assert time.monotonic() < deadline
                time.sleep(.01)
            assert code == 0 and output.endswith('END\n')

            # Exercise the public Rust command from outside the source checkout.
            env = dict(os.environ, XDG_DATA_HOME=str(base / 'empty-data'),
                       XDG_CONFIG_HOME=str(base / 'empty-config'),
                       XDG_STATE_HOME=str(base / 'empty-state'))
            display = Display()
            process = subprocess.Popen([ROOT / 'target/release/redegpc', 'launcher'],
                                       cwd=base, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while not display.windows():
                    assert process.poll() is None, process.stdout.read().decode()
                    assert time.monotonic() < deadline
                    time.sleep(.05)
                # Wait until the launcher has installed its close handler.
                time.sleep(.5)
                display.request_game_close()
                assert process.wait(timeout=10) == 0
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()
                display.close()
            print(f'Checked navigation, all {len(reached)} goals, input, real import/check, settings, logs and process lifecycle.')
    print('LAUNCHER_CHECKS_PASSED')


if __name__ == '__main__':
    main()
