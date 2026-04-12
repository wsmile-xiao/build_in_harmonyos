#!/usr/bin/env python3
"""ohc CLI wrapper — delegates to scripts/ohc package.

Usage:
    python3 scripts/ohc.py engine [options] <error_text>
    python3 scripts/ohc.py status [options]
    python3 scripts/ohc.py handoff [options] <json_data>
"""
import sys
import os

# Ensure scripts/ is on the import path so 'ohc' package resolves
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from ohc.cli import main

if __name__ == "__main__":
    sys.exit(main() or 0)
