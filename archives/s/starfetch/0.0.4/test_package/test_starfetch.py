#!/usr/bin/env python3
"""Consumer test for the installed starfetch 0.0.4 executable.

Runs the packaged binary through the Conan run environment (PATH provides
bin/, STARFETCH_RES_DIR provides the packaged resource directory) and asserts
deterministic behavior of the CLI. 19 assertions total.
"""

import os
import shutil
import subprocess
import sys

ASSERTION_COUNT = 19
_results = []


def check(name, condition):
    _results.append((name, bool(condition)))


def main():
    exe = shutil.which("starfetch")
    check("binary found on PATH", exe is not None)
    if exe is None:
        report()
        return 1

    res_dir = os.environ.get("STARFETCH_RES_DIR", "")
    check("STARFETCH_RES_DIR is exported", bool(res_dir))
    check(
        "constellation data is packaged",
        os.path.isfile(
            os.path.join(res_dir, "constellations", "orion.json")
        ),
    )
    check(
        "template is packaged",
        os.path.isfile(os.path.join(res_dir, "template")),
    )
    check(
        "help message is packaged",
        os.path.isfile(os.path.join(res_dir, "help_message.txt")),
    )

    def run(args):
        proc = subprocess.run(
            [exe] + args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        check(f"exit code 0 for {args or ['<random>']}", proc.returncode == 0)
        return proc.stdout or ""

    out_h = run(["-h"])
    check("help text rendered", "Usage: starfetch" in out_h)

    out_l = run(["-l"])
    check("list contains orion", "orion" in out_l)
    check("list header rendered", "available constellations" in out_l)

    out_n = run(["-n", "orion"])
    check("orion name rendered", "Orion" in out_n)
    check("orion quadrant rendered", "NQ1" in out_n)

    out_bad = run(["-n", "definitely-not-a-constellation"])
    check("unknown name reports error", "isn't recognized" in out_bad)

    out_c = run(["-c", "red", "-n", "orion"])
    check("red color applied", "\x1b[1;31m" in out_c)

    out_r = run([])
    check("random mode produces output", len(out_r.strip()) > 0)

    return report()


def report():
    passed = sum(1 for _, ok in _results if ok)
    for name, ok in _results:
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    print(f"{passed}/{len(_results)} assertions passed")
    if passed != len(_results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
