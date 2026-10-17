#!/usr/bin/env python3
"""Validate the installed sound resource tree and representative files."""

import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_resources.py <package-folder>")
    root = Path(sys.argv[1]) / "share" / "sounds" / "lomiri"
    if not root.is_dir():
        raise AssertionError(f"sound root missing: {root}")
    ogg_files = sorted(root.rglob("*.ogg"))
    if len(ogg_files) < 40:
        raise AssertionError(f"expected at least 40 Ogg files, found {len(ogg_files)}")
    required = (
        Path("camera") / "click" / "camera_click.ogg",
        Path("camera") / "focus" / "camera_focus.ogg",
        Path("notifications") / "A440.ogg",
        Path("ringtones") / "Ubuntu.ogg",
    )
    for relative in required:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"required non-empty resource missing: {path}")
    print(f"OK: {len(ogg_files)} Lomiri Ogg resources installed")


if __name__ == "__main__":
    main()
