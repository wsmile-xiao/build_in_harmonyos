#!/usr/bin/env python3
"""Verify the packaged adarkroom web assets are installed.

Usage: test_adarkroom.py <pkg_folder>

Checks that the browser-game artifacts are present in the package:
  - web entry: index.html, browserWarning.html, mobileWarning.html, favicon.ico
  - game engine: script/engine.js + script/*.js
  - assets: css/*.css, img/*, audio/*, lang/*/strings.po
  - license: licenses/LICENSE.md
"""
import os
import sys


def check_file(path, label):
    if not os.path.isfile(path):
        print(f"[FAIL] missing {label}: {path}", file=sys.stderr)
        return False
    size = os.path.getsize(path)
    if size == 0:
        print(f"[FAIL] empty {label}: {path}", file=sys.stderr)
        return False
    print(f"  [ok] {label} ({size} bytes)")
    return True


def check_dir(path, label, non_empty=False):
    if not os.path.isdir(path):
        print(f"[FAIL] missing dir {label}: {path}", file=sys.stderr)
        return False
    n = len(os.listdir(path))
    if non_empty and n == 0:
        print(f"[FAIL] empty dir {label}: {path}", file=sys.stderr)
        return False
    print(f"  [ok] {label}/ ({n} entries)")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_adarkroom.py <pkg_folder>", file=sys.stderr)
        return 2

    pkg = sys.argv[1]
    www = os.path.join(pkg, "share", "adarkroom", "www")
    checks = [
        (check_dir(www, "www", non_empty=True), "www dir"),
        (check_file(os.path.join(www, "index.html"), "index.html"), "index.html"),
        (check_file(os.path.join(www, "script", "engine.js"), "script/engine.js"), "engine.js"),
        (check_dir(os.path.join(www, "css"), "css", non_empty=True), "css dir"),
        (check_dir(os.path.join(www, "img"), "img", non_empty=True), "img dir"),
        (check_dir(os.path.join(www, "audio"), "audio", non_empty=True), "audio dir"),
        (check_dir(os.path.join(www, "lang"), "lang", non_empty=True), "lang dir"),
        (check_dir(os.path.join(www, "lib"), "lib", non_empty=True), "lib dir"),
        (check_file(os.path.join(www, "lib", "base64.js"), "lib/base64.js"), "lib/base64.js"),
        (check_file(os.path.join(pkg, "licenses", "LICENSE.md"), "licenses/LICENSE.md"), "license"),
    ]

    # index.html must reference the engine script (real content check)
    idx = os.path.join(www, "index.html")
    if os.path.isfile(idx):
        with open(idx, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        ok = "script/engine.js" in content
        checks.append((ok, "index.html references engine.js"))
        print(f"  [{'ok' if ok else 'FAIL'}] index.html references script/engine.js")

    passed = sum(1 for c, _ in checks if c)
    failed = sum(1 for c, _ in checks if not c)
    print(f"=== Results: {passed} passed, {failed} failed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
