#!/usr/bin/env python3
"""Consumer driver for GNU gcal 4 (artifact gcal/v4, R34): run the packaged
binary and assert real calendar behaviour — version banner, the February 1992
leap-year layout (29 days, 1st on Sa), a no-argument month grid and
unknown-option rejection."""
import subprocess
import sys


def run(*args):
    return subprocess.run(args, capture_output=True, text=True)


def main():
    bindir = sys.argv[1]
    exe = bindir.rstrip("/\\") + "/gcal"
    failures = 0

    ver = run(exe, "--version")
    if ver.returncode == 0 and "gcal (GNU cal) 4" in ver.stdout:
        print("PASS: --version reports gcal (GNU cal) 4")
    else:
        print(f"FAIL: --version rc={ver.returncode} out={ver.stdout!r}")
        failures += 1

    feb = run(exe, "2/1992")
    rows = [r.split() for r in feb.stdout.splitlines() if r.strip()]
    ok = feb.returncode == 0 and "February 1992" in feb.stdout
    ok = ok and len(rows) > 2 and rows[1] == ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
    ok = ok and rows[2][-1] == "1" and rows[-1][-1] == "29"
    if ok:
        print("PASS: gcal 2/1992 renders the leap-year February (1st on Sa, 29 days)")
    else:
        print(f"FAIL: gcal 2/1992 rc={feb.returncode} out={feb.stdout!r}")
        failures += 1

    today = run(exe)
    grid = [r.split() for r in today.stdout.splitlines() if r.strip()]
    ok = today.returncode == 0 and any(r[:7] == ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
                                       for r in grid[1:])
    ok = ok and any(any(c.isdigit() for c in r) for r in grid[1:])
    if ok:
        print("PASS: bare `gcal` prints a month grid with the Su-Sa header")
    else:
        print(f"FAIL: bare gcal rc={today.returncode} out={today.stdout!r}")
        failures += 1

    bad = run(exe, "--no-such-flag")
    if bad.returncode != 0 and "unrecognized option" in (bad.stdout + bad.stderr):
        print("PASS: unknown option is rejected with non-zero exit")
    else:
        print(f"FAIL: unknown option rc={bad.returncode} out={bad.stdout!r} err={bad.stderr!r}")
        failures += 1

    if failures:
        print(f"{failures} check(s) FAILED")
        return 1
    print("gcal consumer test: all 4 checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
