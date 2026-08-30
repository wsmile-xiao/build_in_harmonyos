#!/usr/bin/env python3
"""cdargs consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

cdargs -f <list> -a <absdir> is a fully headless operation: it reads
the bookmark list file, appends the given absolute directory and
rewrites the list file. In the source the -a/--add branch exits before
init_curses(), so no terminal/curses is touched — the packaged binary
is really executed on OHOS (R34 full check, not degraded).

Usage: test_cdargs.py <package-folder>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "cdargs")
    if not os.path.isfile(exe):
        raise AssertionError(f"cdargs binary missing: {exe}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"cdargs not executable: {exe}")

    cwd = os.getcwd()
    if not cwd.startswith("/"):
        raise AssertionError(f"test cwd is not absolute: {cwd}")

    list_file = os.path.join(cwd, "cdargs.test.bookmarks")
    if os.path.exists(list_file):
        os.remove(list_file)

    # non-interactive bookmark add: cdargs -f <list> -a <absdir>
    proc = subprocess.run(
        [exe, "-f", list_file, "-a", cwd],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"cdargs -a failed rc={proc.returncode}: {proc.stderr}")
    if not os.path.isfile(list_file):
        raise AssertionError(f"bookmark list not written: {list_file}")
    with open(list_file, encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    if cwd not in content:
        raise AssertionError(
            f"bookmark not found in list file: {cwd!r} not in {content!r}")
    print(f"OK: cdargs bookmark add roundtrip verified ({cwd})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
