#!/usr/bin/env python3
"""Launch from any working directory: python3 /path/to/launcher/main.py."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description='Resident Evil Degeneration dossier launcher')
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/release/redegpc')
    args = parser.parse_args()
    try:
        import tkinter as tk
        from launcher.ui import Launcher
        from launcher.backend import Directories
        window = tk.Tk()
        Launcher(window, args.binary.resolve(), Directories.discover())
        window.mainloop()
    except ImportError as error:
        parser.exit(1, f'Launcher dependency unavailable: {error}. Install Python Tk and Pillow; see launcher/README.md.\n')
    except (OSError, ValueError, tk.TclError) as error:
        parser.exit(1, f'Cannot open launcher: {error}\n')


if __name__ == '__main__':
    main()
