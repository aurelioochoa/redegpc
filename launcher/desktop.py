"""Shared desktop icon preferences and per-user shortcut installation."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

from .backend import Directories

ROOT = Path(__file__).resolve().parents[1]
ICONS = (('leon-portrait', 'Leon'), ('quarantine-dossier', 'Dossier'),
         ('fractured-d', 'Fractured D'))
ICON_IDS = {key for key, label in ICONS}
ICON_ASSETS = Path(__file__).resolve().parent / 'assets/desktop-icons'


def load_icon(dirs):
    path = dirs.config / 'desktop-icon.json'
    if not path.exists():
        return ICONS[0][0]
    value = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or not isinstance(value.get('icon'), str)
            or value['icon'] not in ICON_IDS):
        raise ValueError('Unrecognized desktop icon preference')
    return value['icon']


def write_file(path, contents, mode=0o644):
    """Replace each file atomically, leaving complete files on disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.desktop-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def entry_value(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')


def exec_value(path):
    value = str(path).replace('%', '%%')
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, '\\' + character)
    return entry_value('"' + value + '"')


def desktop_folder():
    if shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True,
                                text=True, check=False)
        if result.returncode:
            raise ValueError('Cannot locate your desktop directory')
        folder = Path(result.stdout.strip())
    else:
        folder = Path.home() / 'Desktop'
    if not folder.is_absolute() or folder == Path.home() or not folder.is_dir():
        raise ValueError('No desktop directory configured; omit --desktop to install only the applications-menu entry')
    return folder


def locations(dirs):
    return (Path.home() / '.local/bin/redegpc',
            dirs.data.parent / 'applications/redegpc.desktop')


def install_icon(choice, *, dirs=None, binary=None, desktop=False):
    if choice not in ICON_IDS:
        raise ValueError('Choose one of the three desktop icons')
    dirs = dirs or Directories.discover()
    binary = Path(binary or ROOT / 'target/release/redegpc').resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError('Build the release host first with make build')
    # Retain the installing interpreter, including a configured venv.
    import tkinter  # noqa: F401
    from PIL import Image, ImageTk  # noqa: F401
    artwork = ICON_ASSETS / f'{choice}.png'
    with Image.open(artwork) as image:
        image.verify()
    wrapper, entry = locations(dirs)
    # Distinct filenames invalidate desktop-shell icon caches on change.
    icon = dirs.data / 'icons' / f'redegpc-{choice}.png'
    shortcut = desktop_folder() / entry.name if desktop else None
    launcher = '\n'.join([
        '#!/bin/sh',
        'if [ "$#" -eq 0 ] || [ "$1" = launcher ]; then',
        '    if [ "$#" -gt 0 ]; then shift; fi',
        '    exec ' + shlex.quote(sys.executable) + ' '
        + shlex.quote(str(Path(__file__).resolve().parent / 'main.py')) + ' --binary '
        + shlex.quote(str(binary)) + ' "$@"',
        'fi',
        'exec ' + shlex.quote(str(binary)) + ' "$@"', '',
    ])
    contents = '\n'.join([
        '[Desktop Entry]', 'Version=1.0', 'Type=Application',
        'Name=Resident Evil Degeneration',
        'Comment=Open the Resident Evil Degeneration dossier launcher',
        'Exec=' + exec_value(wrapper), 'TryExec=' + entry_value(wrapper),
        'Icon=' + entry_value(icon), 'Terminal=false', 'Categories=Game;',
        'Keywords=Resident Evil;Degeneration;redegpc;',
        'StartupNotify=false', '',
    ]).encode('utf-8')
    write_file(icon, artwork.read_bytes())
    write_file(wrapper, launcher.encode('utf-8'), 0o755)
    write_file(entry, contents)
    paths = [wrapper, entry, icon]
    if shortcut:
        write_file(shortcut, contents, 0o755)
        paths.append(shortcut)
    write_file(dirs.config / 'desktop-icon.json',
               (json.dumps({'icon': choice}) + '\n').encode('utf-8'))
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(entry.parent)], check=False)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop', action='store_true', help='Also create a desktop shortcut')
    parser.add_argument('--uninstall', action='store_true', help='Remove shortcuts and icons; preserve game and saves')
    parser.add_argument('--icon', choices=sorted(ICON_IDS), help='Use a concept icon (default: saved choice or Leon)')
    args = parser.parse_args()
    try:
        dirs = Directories.discover()
        if args.uninstall:
            paths = list(locations(dirs)) + [dirs.data / 'icons/redegpc.png']
            paths += [dirs.data / 'icons' / f'redegpc-{key}.png' for key, label in ICONS]
            if args.desktop:
                paths.append(desktop_folder() / 'redegpc.desktop')
            for path in paths:
                path.unlink(missing_ok=True)
                print('Removed:', path)
            return 0
        paths = install_icon(args.icon or load_icon(dirs), dirs=dirs, desktop=args.desktop)
        for path in paths:
            print('Installed:', path)
        if args.desktop:
            print('If your desktop asks, choose Allow Launching / Trust this launcher.')
        print('Keep this checkout in place; rerun make desktop after moving it.')
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as error:
        print('Desktop setup:', error, file=sys.stderr)
        return 1
    return 0
