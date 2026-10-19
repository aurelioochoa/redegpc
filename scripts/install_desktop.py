#!/usr/bin/env python3
"""Install per-user Linux desktop shortcuts from this checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from launcher.desktop import main


if __name__ == '__main__':
    sys.exit(main())
